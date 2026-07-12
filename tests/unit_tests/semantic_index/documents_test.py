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
"""Tests for semantic document builders."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from axbi.semantic_index.documents import build_dataset_semantic_documents


def test_build_dataset_semantic_documents() -> None:
    dataset_uuid = uuid4()
    dataset = SimpleNamespace(
        id=12,
        uuid=dataset_uuid,
        table_name="sales_orders",
        schema="mart",
        description="Sales order facts",
        main_dttm_col="order_date",
        database=SimpleNamespace(database_name="analytics"),
        columns=[
            SimpleNamespace(
                column_name="order_date",
                type="TIMESTAMP",
                description="Order date",
                is_dttm=True,
                groupby=True,
                filterable=True,
            ),
            SimpleNamespace(
                column_name="region",
                type="VARCHAR",
                description="Sales region",
                is_dttm=False,
                groupby=True,
                filterable=True,
            ),
        ],
        metrics=[
            SimpleNamespace(
                metric_name="total_revenue",
                expression="sum(revenue)",
                description="Total booked revenue",
                d3format="$,.2f",
            )
        ],
    )

    documents = build_dataset_semantic_documents(dataset)

    assert [document.document_kind for document in documents] == [
        "summary",
        "column_profile",
        "column_profile",
        "metric_candidate",
    ]
    assert documents[0].object_type == "dataset"
    assert documents[0].object_id == str(dataset_uuid)
    assert "Columns: order_date, region" in documents[0].content
    assert "Metric: total_revenue" in documents[-1].content
    assert all(document.dataset_id == 12 for document in documents)


def test_semantic_document_source_hash_is_stable() -> None:
    dataset = SimpleNamespace(
        id=1,
        uuid=None,
        table_name="inventory",
        schema=None,
        description=None,
        main_dttm_col=None,
        database=None,
        columns=[],
        metrics=[],
    )

    first = build_dataset_semantic_documents(dataset)[0]
    second = build_dataset_semantic_documents(dataset)[0]

    assert first.source_hash == second.source_hash


def _small_dataset() -> SimpleNamespace:
    return SimpleNamespace(
        id=7,
        uuid=None,
        table_name="revenue",
        schema=None,
        description=None,
        main_dttm_col=None,
        database=None,
        columns=[
            SimpleNamespace(
                column_name="client",
                type="VARCHAR",
                description=None,
                is_dttm=False,
                groupby=True,
                filterable=True,
            )
        ],
        metrics=[
            SimpleNamespace(
                metric_name="total_revenue",
                expression="SUM(amount)",
                description=None,
                d3format=None,
            )
        ],
    )


def test_aliases_enrich_documents() -> None:
    aliases = {
        ("column", "client"): ["customer", "account"],
        ("metric", "total_revenue"): ["turnover"],
    }
    documents = build_dataset_semantic_documents(_small_dataset(), aliases=aliases)

    summary = documents[0]
    assert "Glossary:" in summary.content
    assert "client (aka customer, account)" in summary.content

    column_doc = next(d for d in documents if d.object_type == "column")
    assert "Also known as: customer, account" in column_doc.content
    metric_doc = next(d for d in documents if d.object_type == "metric")
    assert "Also known as: turnover" in metric_doc.content


def test_instructions_emit_governed_note_documents() -> None:
    instructions = ["Amounts are LCY; do not sum across regions.", "  "]
    documents = build_dataset_semantic_documents(
        _small_dataset(), instructions=instructions
    )

    notes = [d for d in documents if d.document_kind == "note"]
    # Blank instruction is skipped; one real note emitted.
    assert len(notes) == 1
    assert "do not sum across regions" in notes[0].content
    assert notes[0].source == "dataset_profile"


def test_no_governance_is_backward_compatible() -> None:
    # Without aliases/instructions the document set is unchanged.
    documents = build_dataset_semantic_documents(_small_dataset())
    assert [d.document_kind for d in documents] == [
        "summary",
        "column_profile",
        "metric_candidate",
    ]
    assert "Also known as" not in documents[1].content
