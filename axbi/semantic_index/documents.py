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
"""Semantic document builders for AxBI metadata objects."""

from __future__ import annotations

from typing import Any

from axbi.semantic_index.governance import aliases_for, AliasMap
from axbi.semantic_index.types import SemanticDocument


def _clean(value: Any) -> str:
    """Return a compact string for semantic document text."""

    if value is None:
        return ""
    return str(value).strip()


def _alias_suffix(aliases: AliasMap | None, object_type: str, name: str) -> str:
    """Return an ``Also known as`` line for an object, or an empty string."""

    aka = aliases_for(aliases, object_type, name)
    return f"\nAlso known as: {', '.join(aka)}" if aka else ""


def _dataset_object_id(dataset: Any) -> str:
    """Return a stable dataset object identifier."""

    if dataset_uuid := getattr(dataset, "uuid", None):
        return str(dataset_uuid)
    return str(dataset.id)


def _column_content(dataset_name: str, column: Any) -> str:
    """Build semantic text for a dataset column."""

    parts = [
        f"Dataset: {dataset_name}",
        f"Column: {_clean(getattr(column, 'column_name', ''))}",
    ]
    if column_type := _clean(getattr(column, "type", "")):
        parts.append(f"Type: {column_type}")

    if description := _clean(getattr(column, "description", "")):
        parts.append(f"Description: {description}")

    flags = []
    if getattr(column, "is_dttm", False):
        flags.append("time column")
    if getattr(column, "groupby", False):
        flags.append("groupable dimension")
    if getattr(column, "filterable", False):
        flags.append("filterable dimension")
    if flags:
        parts.append(f"Usage: {', '.join(flags)}")

    return "\n".join(parts)


def _metric_content(dataset_name: str, metric: Any) -> str:
    """Build semantic text for a dataset metric."""

    parts = [
        f"Dataset: {dataset_name}",
        f"Metric: {_clean(getattr(metric, 'metric_name', ''))}",
    ]
    if expression := _clean(getattr(metric, "expression", "")):
        parts.append(f"Expression: {expression}")

    if description := _clean(getattr(metric, "description", "")):
        parts.append(f"Description: {description}")

    if d3format := _clean(getattr(metric, "d3format", "")):
        parts.append(f"Format: {d3format}")

    return "\n".join(parts)


def build_dataset_semantic_documents(  # noqa: C901
    dataset: Any,
    *,
    aliases: AliasMap | None = None,
    instructions: list[str] | None = None,
) -> list[SemanticDocument]:
    """Build semantic index documents for a AxBI SQL dataset.

    ``aliases`` enriches documents with business synonyms (so a query for
    "turnover" matches a ``revenue`` metric) and ``instructions`` emits governed
    ``note`` documents capturing disambiguation rules (for example, "amounts are
    in local currency; do not sum across regions"). Both are optional so the
    builder stays backward compatible and pure (no database access here).
    """

    dataset_id = getattr(dataset, "id", None)
    object_id = _dataset_object_id(dataset)
    dataset_name = _clean(getattr(dataset, "table_name", "")) or object_id
    schema = _clean(getattr(dataset, "schema", ""))
    database = _clean(getattr(getattr(dataset, "database", None), "database_name", ""))
    description = _clean(getattr(dataset, "description", ""))
    main_dttm_col = _clean(getattr(dataset, "main_dttm_col", ""))

    columns = list(getattr(dataset, "columns", []) or [])
    metrics = list(getattr(dataset, "metrics", []) or [])
    column_names = [
        _clean(getattr(column, "column_name", ""))
        for column in columns
        if _clean(getattr(column, "column_name", ""))
    ]
    metric_names = [
        _clean(getattr(metric, "metric_name", ""))
        for metric in metrics
        if _clean(getattr(metric, "metric_name", ""))
    ]

    summary_parts = [
        f"Dataset: {dataset_name}",
        f"Object id: {object_id}",
    ]
    if database:
        summary_parts.append(f"Database: {database}")
    if schema:
        summary_parts.append(f"Schema: {schema}")
    if description:
        summary_parts.append(f"Description: {description}")
    if main_dttm_col:
        summary_parts.append(f"Time column: {main_dttm_col}")
    if column_names:
        summary_parts.append(f"Columns: {', '.join(column_names)}")
    if metric_names:
        summary_parts.append(f"Metrics: {', '.join(metric_names)}")

    if dataset_aka := aliases_for(aliases, "dataset", dataset_name):
        summary_parts.append(f"Also known as: {', '.join(dataset_aka)}")

    glossary_entries = []
    for column_name in column_names:
        aka = aliases_for(aliases, "column", column_name)
        if aka:
            glossary_entries.append(f"{column_name} (aka {', '.join(aka)})")
    for metric_name in metric_names:
        aka = aliases_for(aliases, "metric", metric_name)
        if aka:
            glossary_entries.append(f"{metric_name} (aka {', '.join(aka)})")
    if glossary_entries:
        summary_parts.append("Glossary: " + "; ".join(glossary_entries))

    documents = [
        SemanticDocument(
            object_type="dataset",
            object_id=object_id,
            object_name=dataset_name,
            document_kind="summary",
            source="dataset_profile",
            content="\n".join(summary_parts),
            dataset_id=dataset_id,
            extra={
                "schema": schema,
                "database": database,
                "column_count": len(column_names),
                "metric_count": len(metric_names),
            },
        )
    ]

    for column in columns:
        column_name = _clean(getattr(column, "column_name", ""))
        if not column_name:
            continue
        documents.append(
            SemanticDocument(
                object_type="column",
                object_id=f"{object_id}:{column_name}",
                object_name=column_name,
                document_kind="column_profile",
                source="dataset_profile",
                content=_column_content(dataset_name, column)
                + _alias_suffix(aliases, "column", column_name),
                dataset_id=dataset_id,
                extra={"dataset_object_id": object_id},
            )
        )

    for metric in metrics:
        metric_name = _clean(getattr(metric, "metric_name", ""))
        if not metric_name:
            continue
        documents.append(
            SemanticDocument(
                object_type="metric",
                object_id=f"{object_id}:{metric_name}",
                object_name=metric_name,
                document_kind="metric_candidate",
                source="dataset_profile",
                content=_metric_content(dataset_name, metric)
                + _alias_suffix(aliases, "metric", metric_name),
                dataset_id=dataset_id,
                extra={"dataset_object_id": object_id},
            )
        )

    for index, instruction in enumerate(instructions or []):
        instruction_text = _clean(instruction)
        if not instruction_text:
            continue
        documents.append(
            SemanticDocument(
                object_type="dataset",
                object_id=f"{object_id}:instruction:{index}",
                object_name=dataset_name,
                document_kind="note",
                source="dataset_profile",
                content=f"Dataset: {dataset_name}\nInstruction: {instruction_text}",
                dataset_id=dataset_id,
                extra={"dataset_object_id": object_id, "instruction_index": index},
            )
        )

    return documents
