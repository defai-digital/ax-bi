# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""Semantic enrichment assistance via the Admin-configured LLM factory.

Produces **draft** suggestions (descriptions, synonyms, relationship hints).
Writes to certified semantic fields still require existing permissions and
human/admin approval — model output is never authoritative.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from axbi.genai.audit import timed_complete_json
from axbi.genai.llm_provider import LLMProvider, StubLLMProvider
from axbi.genai.provider_factory import get_llm_provider

logger = logging.getLogger(__name__)

SuggestionType = Literal["description", "synonym", "relationship"]
ObjectType = Literal["dataset", "column", "metric"]


class SemanticSuggestion(BaseModel):
    """A single draft enrichment suggestion."""

    object_type: ObjectType
    object_name: str
    suggestion_type: SuggestionType
    value: str = Field(description="Suggested text, alias, or related object name")
    related_object: str | None = Field(
        default=None,
        description="For relationship hints: the other column/object name",
    )
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    rationale: str = ""


class SemanticAssistResult(BaseModel):
    """Transport-neutral semantic assist outcome."""

    suggestions: list[SemanticSuggestion] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    used_llm: bool = False
    provider_type: str | None = None
    model: str | None = None


_SYSTEM_PROMPT = """\
You are a BI semantic modeling assistant. Given a dataset's columns and metrics,
suggest draft enrichments that help analysts and AI map business language to
technical fields and understand relationships.

RULES:
- Only reference object_name values that appear in the metadata.
- suggestion_type must be one of: description, synonym, relationship.
- object_type must be one of: dataset, column, metric.
- For synonym: value is an alternate business name (not the technical name).
- For relationship: value describes the relationship; related_object is the
  other column name (e.g. customer_id → customers.id style join key).
- Prefer high-confidence suggestions; omit low-value noise.
- Do not invent SQL credentials or connection details.
- Output is draft only — never claim fields are certified.
"""


class _LlmSemanticAssistResponse(BaseModel):
    """Schema for structured LLM output."""

    suggestions: list[SemanticSuggestion] = Field(default_factory=list)


def _humanize_identifier(name: str) -> str:
    text = re.sub(r"[_\-.]+", " ", name or "").strip()
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    return " ".join(part.capitalize() for part in text.split() if part)


def _is_fk_like(name: str) -> bool:
    """True for foreign-key-style names like ``customer_id``, not bare ``id`` (PK)."""
    lower = (name or "").lower()
    return lower.endswith("_id") and len(lower) > 3


def _fk_related_object(cname: str, col_names: set[str]) -> str | None:
    """Entity stem or peer column for an FK-like name; never self-referential."""
    stem = re.sub(r"_id$", "", cname or "", flags=re.IGNORECASE).strip()
    if not stem or stem.lower() == (cname or "").lower():
        return None
    # Prefer another column that matches the entity stem (e.g. ``customer``).
    if stem in col_names and stem != cname:
        return stem
    # Do not set related_object to this column's own name (``{stem}_id``).
    return stem


def _dataset_table_name(dataset: Any) -> str:
    return (
        getattr(dataset, "table_name", "") or getattr(dataset, "name", "") or ""
    )


def _known_object_names(dataset: Any) -> dict[str, set[str]]:
    """Allowed object_name values per object_type for suggestion validation."""
    table_name = _dataset_table_name(dataset)
    columns = {
        getattr(c, "column_name", "") or ""
        for c in list(getattr(dataset, "columns", None) or [])
        if getattr(c, "column_name", None)
    }
    metrics = {
        getattr(m, "metric_name", "") or ""
        for m in list(getattr(dataset, "metrics", None) or [])
        if getattr(m, "metric_name", None)
    }
    datasets = {table_name} if table_name else set()
    return {"dataset": datasets, "column": columns, "metric": metrics}


def _filter_suggestions_to_known(
    suggestions: list[SemanticSuggestion],
    known: dict[str, set[str]],
) -> list[SemanticSuggestion]:
    """Drop suggestions that invent object names not present in the dataset."""
    kept: list[SemanticSuggestion] = []
    for suggestion in suggestions:
        allowed = known.get(suggestion.object_type) or set()
        if suggestion.object_name not in allowed:
            continue
        related = suggestion.related_object
        if related and suggestion.object_type == "column":
            # related_object may be an entity stem (not a column) or another column.
            # Reject only when it is exactly the same as object_name (self-loop).
            if related == suggestion.object_name:
                related = _fk_related_object(suggestion.object_name, allowed)
        kept.append(
            suggestion.model_copy(update={"related_object": related})
            if related != suggestion.related_object
            else suggestion
        )
    return kept


def _dataset_context_lines(dataset: Any) -> list[str]:
    table_name = _dataset_table_name(dataset)
    lines: list[str] = [
        f"Dataset: {table_name}",
        f"Description: {getattr(dataset, 'description', None) or '(none)'}",
    ]
    col_bits: list[str] = []
    for col in list(getattr(dataset, "columns", None) or [])[:40]:
        cname = getattr(col, "column_name", "") or ""
        ctype = str(getattr(col, "type", "") or "UNKNOWN")
        cdesc = getattr(col, "description", None) or ""
        bit = f"{cname}:{ctype}"
        if cdesc:
            bit += f" ({cdesc[:60]})"
        col_bits.append(bit)
    if col_bits:
        lines.append("Columns: " + "; ".join(col_bits))
    metric_bits: list[str] = []
    for metric in list(getattr(dataset, "metrics", None) or [])[:20]:
        mname = getattr(metric, "metric_name", "") or ""
        mexpr = getattr(metric, "expression", "") or ""
        metric_bits.append(f"{mname}={mexpr}" if mexpr else mname)
    if metric_bits:
        lines.append("Metrics: " + "; ".join(metric_bits))
    return lines


def _heuristic_column_suggestions(
    columns: list[Any],
    *,
    table_name: str,
    col_names: set[str],
) -> list[SemanticSuggestion]:
    suggestions: list[SemanticSuggestion] = []
    for col in columns:
        cname = getattr(col, "column_name", "") or ""
        if not cname:
            continue
        cdesc = (getattr(col, "description", None) or "").strip()
        human = _humanize_identifier(cname)
        if human and human.lower() != cname.lower():
            suggestions.append(
                SemanticSuggestion(
                    object_type="column",
                    object_name=cname,
                    suggestion_type="synonym",
                    value=human,
                    confidence=0.5,
                    rationale="Humanized column name",
                )
            )
        if not cdesc:
            suggestions.append(
                SemanticSuggestion(
                    object_type="column",
                    object_name=cname,
                    suggestion_type="description",
                    value=f"{human} field on {table_name or 'dataset'}",
                    confidence=0.35,
                    rationale="Placeholder description for missing metadata",
                )
            )
        if _is_fk_like(cname):
            related = _fk_related_object(cname, col_names)
            stem = related or re.sub(r"_id$", "", cname, flags=re.IGNORECASE)
            suggestions.append(
                SemanticSuggestion(
                    object_type="column",
                    object_name=cname,
                    suggestion_type="relationship",
                    value=(
                        f"Likely foreign key referencing "
                        f"{stem or 'related entity'}"
                    ),
                    related_object=related,
                    confidence=0.45,
                    rationale="Column name matches common foreign-key pattern",
                )
            )
    return suggestions


def heuristic_semantic_suggestions(dataset: Any) -> SemanticAssistResult:
    """Rule-based drafts when no LLM is configured."""
    suggestions: list[SemanticSuggestion] = []
    table_name = _dataset_table_name(dataset)
    if table_name:
        human = _humanize_identifier(table_name)
        if human.lower() != table_name.lower():
            suggestions.append(
                SemanticSuggestion(
                    object_type="dataset",
                    object_name=table_name,
                    suggestion_type="synonym",
                    value=human,
                    confidence=0.55,
                    rationale="Humanized identifier from table name",
                )
            )

    columns = list(getattr(dataset, "columns", None) or [])
    col_names = {
        getattr(c, "column_name", "") or ""
        for c in columns
        if getattr(c, "column_name", None)
    }
    suggestions.extend(
        _heuristic_column_suggestions(
            columns, table_name=table_name, col_names=col_names
        )
    )

    for metric in list(getattr(dataset, "metrics", None) or [])[:15]:
        mname = getattr(metric, "metric_name", "") or ""
        if not mname:
            continue
        human = _humanize_identifier(mname)
        if human.lower() != mname.lower():
            suggestions.append(
                SemanticSuggestion(
                    object_type="metric",
                    object_name=mname,
                    suggestion_type="synonym",
                    value=human,
                    confidence=0.5,
                    rationale="Humanized metric name",
                )
            )

    return SemanticAssistResult(
        suggestions=suggestions[:40],
        warnings=[
            "No LLM provider configured. Suggestions use heuristics only. "
            "Configure GENAI_LLM_PROVIDER_CONFIG (Admin) for higher-quality drafts."
        ],
        used_llm=False,
        provider_type=None,
        model=None,
    )


def llm_semantic_suggestions(
    dataset: Any,
    provider: LLMProvider,
    *,
    focus: str | None = None,
) -> SemanticAssistResult:
    """Call the shared LLM factory for structured enrichment drafts."""
    context = "\n".join(_dataset_context_lines(dataset))
    focus_line = f"\nFocus: {focus}" if focus else ""
    user_prompt = (
        f"Suggest semantic enrichments for this dataset.\n\n"
        f"{context}{focus_line}\n\n"
        "Return draft suggestions only."
    )
    result = timed_complete_json(
        provider,
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_schema=_LlmSemanticAssistResponse,
        metadata={
            "operation": "semantic_assist",
            "tool": "suggest_semantic_enrichment",
        },
    )
    if not isinstance(result, _LlmSemanticAssistResponse):
        result = _LlmSemanticAssistResponse.model_validate(result)

    known = _known_object_names(dataset)
    filtered = _filter_suggestions_to_known(list(result.suggestions or []), known)
    warnings: list[str] = []
    dropped = len(result.suggestions or []) - len(filtered)
    if dropped > 0:
        warnings.append(
            f"Dropped {dropped} suggestion(s) referencing unknown object names."
        )

    return SemanticAssistResult(
        suggestions=filtered[:50],
        warnings=warnings,
        used_llm=True,
        provider_type=provider.provider_name(),
        model=provider.model_name(),
    )


def suggest_semantic_enrichment(
    dataset: Any,
    *,
    provider: LLMProvider | None = None,
    focus: str | None = None,
) -> SemanticAssistResult:
    """Produce draft semantic suggestions using LLM when configured.

    Falls back to heuristics when the provider is missing, stub, or fails.
    """
    if dataset is None:
        return SemanticAssistResult(
            suggestions=[],
            warnings=["Dataset is required."],
            used_llm=False,
        )

    active = provider
    if active is None:
        try:
            active = get_llm_provider()
        except Exception:  # pylint: disable=broad-except
            active = StubLLMProvider()

    if isinstance(active, StubLLMProvider) or active.provider_name() == "stub":
        return heuristic_semantic_suggestions(dataset)

    try:
        return llm_semantic_suggestions(dataset, active, focus=focus)
    except NotImplementedError:
        return heuristic_semantic_suggestions(dataset)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Semantic assist LLM failed: %s", exc, exc_info=True)
        fallback = heuristic_semantic_suggestions(dataset)
        fallback.warnings = [
            f"LLM semantic assist failed ({type(exc).__name__}); using heuristics.",
            *fallback.warnings,
        ]
        return fallback
