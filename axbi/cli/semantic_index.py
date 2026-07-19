#!/usr/bin/env python
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
"""CLI commands for the GenAI BI semantic index."""

from __future__ import annotations

from typing import Any, cast

import click
from flask.cli import with_appcontext

from axbi.extensions import db
from axbi.utils import json
from axbi.utils.session_lifecycle import commit_session


@click.group()
def semantic_index() -> None:
    """GenAI BI semantic index commands."""


def _echo_json(payload: dict[str, Any] | list[dict[str, Any]]) -> None:
    """Print JSON output for CLI automation."""

    click.echo(json.dumps(payload, indent=2, sort_keys=True))


@semantic_index.command("backfill-datasets")
@with_appcontext
@click.option(
    "--dataset-id",
    "dataset_ids",
    multiple=True,
    type=int,
    help="Dataset id to index. May be repeated.",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Limit datasets when no id is given.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Build documents without embedding writes.",
)
@click.option("--json-output", is_flag=True, help="Print machine-readable JSON.")
def backfill_datasets(
    dataset_ids: tuple[int, ...],
    limit: int | None,
    dry_run: bool,
    json_output: bool,
) -> None:
    """Backfill semantic documents for SQL datasets."""

    from axbi.connectors.sqla.models import SqlaTable
    from axbi.semantic_index.documents import build_dataset_semantic_documents
    from axbi.semantic_index.service import SemanticIndexService

    if dataset_ids:
        ids = list(dataset_ids)
    else:
        query = db.session.query(SqlaTable.id).order_by(cast(Any, SqlaTable.id).asc())
        if limit:
            query = query.limit(limit)
        ids = [row[0] for row in query.all()]

    results: list[dict[str, Any]] = []
    service = None if dry_run else SemanticIndexService()

    for dataset_id in ids:
        result: dict[str, Any]
        if dry_run:
            dataset = (
                db.session.query(SqlaTable).filter(SqlaTable.id == dataset_id).one()
            )
            documents = build_dataset_semantic_documents(dataset)
            result = {
                "dataset_id": dataset_id,
                "documents_seen": len(documents),
                "documents_written": 0,
                "dry_run": True,
            }
        else:
            if service is None:
                raise RuntimeError("SemanticIndexService not initialized")
            summary = service.index_dataset(dataset_id)
            commit_session(db.session, context="semantic_index.backfill")
            result = {
                "dataset_id": dataset_id,
                "documents_seen": summary.documents_seen,
                "documents_written": summary.documents_written,
                "embedding_model": summary.embedding_model,
                "embedding_dimension": summary.embedding_dimension,
                "dry_run": False,
            }
        results.append(result)

    if json_output:
        _echo_json(results)
        return

    for result in results:
        click.echo(
            "dataset {dataset_id}: {documents_written}/{documents_seen} "
            "documents written".format(**result)
        )


@semantic_index.command("search")
@with_appcontext
@click.argument("query")
@click.option("--limit", type=int, default=10)
@click.option(
    "--object-type",
    "object_types",
    multiple=True,
    help="Object type filter. May be repeated.",
)
@click.option("--json-output", is_flag=True, help="Print machine-readable JSON.")
def search(
    query: str,
    limit: int,
    object_types: tuple[str, ...],
    json_output: bool,
) -> None:
    """Search the semantic index."""

    from axbi.semantic_index.service import SemanticIndexService

    service = SemanticIndexService()
    results = service.search(
        query,
        limit=limit,
        object_types=list(object_types) if object_types else None,
    )
    payload = [
        {
            "uuid": result.uuid,
            "object_type": result.object_type,
            "object_id": result.object_id,
            "object_name": result.object_name,
            "document_kind": result.document_kind,
            "distance": result.distance,
            "dataset_id": result.dataset_id,
            "content": result.content,
        }
        for result in results
    ]

    if json_output:
        _echo_json(payload)
        return

    for result in payload:
        distance = result["distance"]
        distance_text = "n/a" if distance is None else f"{distance:.4f}"
        click.echo(
            f"{distance_text} {result['object_type']} "
            f"{result['object_name']} ({result['document_kind']})"
        )


@semantic_index.command("reindex-stale")
@with_appcontext
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Maximum number of stale datasets to reindex.",
)
@click.option("--json-output", is_flag=True, help="Print machine-readable JSON.")
def reindex_stale(limit: int | None, json_output: bool) -> None:
    """Reindex datasets whose documents were marked stale by change hooks.

    This is the manual safety net for deployments without a Celery worker: the
    change hooks mark documents stale synchronously, and this command refreshes
    them by re-embedding each affected dataset.
    """

    from axbi.models.ai import AISemanticDocument
    from axbi.semantic_index.service import SemanticIndexService

    query = (
        db.session.query(AISemanticDocument.dataset_id)
        .filter(
            AISemanticDocument.review_status == "stale",
            AISemanticDocument.dataset_id.isnot(None),
        )
        .distinct()
        .order_by(AISemanticDocument.dataset_id.asc())
    )
    if limit:
        query = query.limit(limit)
    dataset_ids = [row[0] for row in query.all()]

    service = SemanticIndexService()
    results: list[dict[str, Any]] = []
    for dataset_id in dataset_ids:
        try:
            summary = service.index_dataset(dataset_id)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        results.append(
            {
                "dataset_id": dataset_id,
                "documents_seen": summary.documents_seen,
                "documents_written": summary.documents_written,
                "embedding_model": summary.embedding_model,
                "embedding_dimension": summary.embedding_dimension,
            }
        )

    if json_output:
        _echo_json(results)
        return

    if not results:
        click.echo("No stale semantic documents to reindex.")
        return

    for result in results:
        click.echo(
            "dataset {dataset_id}: {documents_written}/{documents_seen} "
            "documents reindexed".format(**result)
        )


@semantic_index.command("eval")
@with_appcontext
@click.option("--dataset-id", type=int, required=True, help="Dataset id to evaluate.")
@click.option("--persist/--no-persist", default=True, help="Record an AIEvaluationRun.")
@click.option("--json-output", is_flag=True, help="Print machine-readable JSON.")
def evaluate(dataset_id: int, persist: bool, json_output: bool) -> None:
    """Score a dataset's governed semantic layer (guardrail + grounding).

    Deterministic and LLM-free: verifies every governance policy is enforced and
    reports how complete the governed data model is.
    """

    from axbi.connectors.sqla.models import SqlaTable
    from axbi.semantic_index.evaluation import (
        evaluate_contract,
        persist_evaluation,
    )
    from axbi.semantic_index.governance import (
        load_dataset_aliases,
        load_dataset_instructions,
        load_dataset_policies,
    )
    from axbi.semantic_index.grounding import build_grounding_contract

    dataset = db.session.query(SqlaTable).filter(SqlaTable.id == dataset_id).one()
    contract = build_grounding_contract(
        dataset,
        aliases=load_dataset_aliases(dataset_id),
        instructions=load_dataset_instructions(dataset),
        policies=load_dataset_policies(dataset),
    )
    report = evaluate_contract(contract)
    if persist:
        persist_evaluation(report)

    if json_output:
        _echo_json(report.to_dict())
        return

    guardrail = report.guardrail
    grounding = report.grounding
    click.echo(f"dataset {report.dataset_id} ({report.dataset_name})")
    click.echo(
        "  guardrail: {passed}/{total} cases correct "
        "(accuracy={accuracy}, precision={precision}, recall={recall})".format(
            **guardrail
        )
        if guardrail.get("total")
        else "  guardrail: no policies declared"
    )
    click.echo(
        "  grounding maturity: {maturity_score} "
        "({measures_defined}/{measure_count} measures defined, "
        "{glossary_terms} glossary terms, {policy_count} policies)".format(**grounding)
    )


def _generation_cases(
    dataset: Any,
    cases_file: str | None,
    contract: Any,
) -> list[Any]:
    """Resolve the golden generation cases: file > dataset extra > auto-derived."""

    from axbi.semantic_index.evaluation import (
        build_generation_cases,
        GenerationCase,
    )
    from axbi.semantic_index.governance import load_dataset_eval_cases

    if cases_file:
        with open(cases_file, encoding="utf-8") as handle:
            raw = json.loads(handle.read())
        return [GenerationCase.from_dict(item) for item in raw]

    if authored := load_dataset_eval_cases(dataset):
        return [GenerationCase.from_dict(item) for item in authored]

    return build_generation_cases(contract)


def _generation_fn(dataset: Any) -> Any:
    """Return a prompt->config generator using the configured pipeline.

    Runs the real generation path: the LLM intent mapper when a provider is
    configured, otherwise the heuristic fallback. This measures whatever
    generation the deployment actually uses.
    """

    from axbi.mcp_service.ai.llm_provider import StubLLMProvider
    from axbi.mcp_service.ai.provider_factory import get_llm_provider

    provider = get_llm_provider()

    def generate(prompt: str) -> dict[str, Any] | None:
        if not isinstance(provider, StubLLMProvider):
            from axbi.mcp_service.ai.intent_mapper import map_intent_to_chart

            return map_intent_to_chart(prompt, dataset, provider).config

        from axbi.mcp_service.ai.intent_heuristic import heuristic_chart_config

        config, *_ = heuristic_chart_config(prompt, dataset, [])
        return config

    return generate


@semantic_index.command("eval-generation")
@with_appcontext
@click.option("--dataset-id", type=int, required=True, help="Dataset id to evaluate.")
@click.option(
    "--cases-file",
    type=click.Path(exists=True),
    default=None,
    help="JSON file of golden cases; overrides the dataset's authored cases.",
)
@click.option("--persist/--no-persist", default=True, help="Record an AIEvaluationRun.")
@click.option(
    "--fail-under",
    type=float,
    default=None,
    help="Exit non-zero if the governance-compliance rate is below this (CI gate).",
)
@click.option(
    "--fail-under-intent",
    type=float,
    default=None,
    help="Exit non-zero if the intent-match rate is below this (CI quality gate).",
)
@click.option("--json-output", is_flag=True, help="Print machine-readable JSON.")
def eval_generation(
    dataset_id: int,
    cases_file: str | None,
    persist: bool,
    fail_under: float | None,
    fail_under_intent: float | None,
    json_output: bool,
) -> None:
    """Score end-to-end prompt-to-dashboard generation for a dataset.

    Runs golden prompts through the configured generation pipeline and reports
    validity, governance-compliance, and intent-match rates so accuracy can be
    tracked over time and gated in CI.
    """

    from sqlalchemy.orm import subqueryload

    from axbi.connectors.sqla.models import SqlaTable
    from axbi.semantic_index.evaluation import (
        EvalReport,
        evaluate_generation,
        persist_evaluation,
    )
    from axbi.semantic_index.governance import (
        load_dataset_aliases,
        load_dataset_instructions,
        load_dataset_policies,
    )
    from axbi.semantic_index.grounding import build_grounding_contract

    dataset = (
        db.session.query(SqlaTable)
        .options(subqueryload(SqlaTable.columns), subqueryload(SqlaTable.metrics))
        .filter(SqlaTable.id == dataset_id)
        .one()
    )
    contract = build_grounding_contract(
        dataset,
        aliases=load_dataset_aliases(dataset_id),
        instructions=load_dataset_instructions(dataset),
        policies=load_dataset_policies(dataset),
    )
    cases = _generation_cases(dataset, cases_file, contract)
    if not cases:
        click.echo("No generation cases to evaluate.")
        return

    score = evaluate_generation(cases, _generation_fn(dataset), contract)

    if persist:
        persist_evaluation(
            EvalReport(
                dataset_id=dataset_id,
                dataset_name=getattr(dataset, "table_name", "") or str(dataset_id),
                guardrail={},
                grounding={},
            ),
            model="generation-eval",
        )

    if json_output:
        _echo_json(score)
    else:
        click.echo(
            "dataset {dataset_id}: {valid}/{total} valid, "
            "compliance={compliance_rate}, intent_match={intent_match_rate}".format(
                dataset_id=dataset_id, **score
            )
        )
        for detail in score["details"]:
            if not detail["governance_compliant"] and detail["blocked_by"]:
                click.echo(f'  ✗ blocked: "{detail["prompt"]}"')

    failures: list[str] = []
    if fail_under is not None and score["compliance_rate"] < fail_under:
        failures.append(
            f"compliance_rate {score['compliance_rate']} < --fail-under {fail_under}"
        )
    intent_rate = score["intent_match_rate"]
    if (
        fail_under_intent is not None
        and intent_rate is not None
        and intent_rate < fail_under_intent
    ):
        failures.append(
            f"intent_match_rate {intent_rate} < --fail-under-intent {fail_under_intent}"
        )
    if failures:
        raise click.ClickException("; ".join(failures))
