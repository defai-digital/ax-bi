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
from __future__ import annotations

from superset.db_engine_specs.athena import AthenaEngineSpec
from superset.db_engine_specs.base import BaseEngineSpec, DatabaseCategory
from superset.db_engine_specs.bigquery import BigQueryEngineSpec
from superset.db_engine_specs.cloud_capabilities import (
    CloudConnectorSupportLevel,
    CloudDataProductType,
    get_cloud_connector_capability,
    get_cloud_connector_capability_for_values,
    list_high_value_cloud_connectors,
)
from superset.db_engine_specs.databricks import DatabricksPythonConnectorEngineSpec
from superset.db_engine_specs.sqlite import SqliteEngineSpec


def test_high_value_lakehouse_connector_capability() -> None:
    capability = get_cloud_connector_capability(DatabricksPythonConnectorEngineSpec)

    assert capability is not None
    assert capability.engine_name == "Databricks"
    assert capability.product_type == CloudDataProductType.LAKEHOUSE
    assert capability.support_level == CloudConnectorSupportLevel.PACKAGED
    assert capability.cloud_providers == ("AWS", "Azure", "Google Cloud")
    assert "Unity Catalog" in capability.data_products
    assert capability.recommended is True


def test_high_value_data_lake_query_engine_capability() -> None:
    capability = get_cloud_connector_capability(AthenaEngineSpec)

    assert capability is not None
    assert capability.engine_name == "Amazon Athena"
    assert capability.product_type == CloudDataProductType.DATA_LAKE_QUERY_ENGINE
    assert capability.support_level == CloudConnectorSupportLevel.PACKAGED
    assert capability.cloud_providers == ("AWS",)
    assert "S3" in capability.data_products


def test_high_value_cloud_warehouse_capability() -> None:
    capability = get_cloud_connector_capability(BigQueryEngineSpec)

    assert capability is not None
    assert capability.engine_name == "Google BigQuery"
    assert capability.product_type == CloudDataProductType.CLOUD_WAREHOUSE
    assert capability.support_level == CloudConnectorSupportLevel.PACKAGED
    assert capability.cloud_providers == ("Google Cloud",)


def test_infers_generic_cloud_connector_from_metadata() -> None:
    class ExampleCloudWarehouseEngineSpec(BaseEngineSpec):
        engine = "examplecloud"
        engine_name = "Example Cloud Warehouse"
        metadata = {
            "categories": [
                DatabaseCategory.CLOUD_AWS,
                DatabaseCategory.ANALYTICAL_DATABASES,
            ],
        }

    capability = get_cloud_connector_capability(ExampleCloudWarehouseEngineSpec)

    assert capability is not None
    assert capability.engine == "examplecloud"
    assert capability.product_type == CloudDataProductType.CLOUD_WAREHOUSE
    assert capability.support_level == CloudConnectorSupportLevel.COMPATIBLE
    assert capability.cloud_providers == ("AWS",)
    assert capability.recommended is False


def test_raw_value_lookup_returns_serializable_capability() -> None:
    capability = get_cloud_connector_capability_for_values(
        engine="bigquery",
        engine_name="Google BigQuery",
        categories=[DatabaseCategory.CLOUD_GCP, DatabaseCategory.ANALYTICAL_DATABASES],
    )

    assert capability is not None
    assert capability.to_dict() == {
        "engine": "bigquery",
        "engine_name": "Google BigQuery",
        "product_type": "cloud_warehouse",
        "support_level": "packaged",
        "cloud_providers": ["Google Cloud"],
        "data_products": ["BigQuery", "BigLake", "External Tables"],
        "recommended": True,
        "notes": "Primary Google Cloud warehouse and lake analytics connector.",
    }


def test_raw_value_lookup_accepts_ast_category_names() -> None:
    capability = get_cloud_connector_capability_for_values(
        engine="examplecloud",
        engine_name="Example Cloud Warehouse",
        categories=["CLOUD_AWS", "ANALYTICAL_DATABASES"],
    )

    assert capability is not None
    assert capability.product_type == CloudDataProductType.CLOUD_WAREHOUSE
    assert capability.support_level == CloudConnectorSupportLevel.COMPATIBLE
    assert capability.cloud_providers == ("AWS",)


def test_returns_none_for_non_cloud_local_connector() -> None:
    assert get_cloud_connector_capability(SqliteEngineSpec) is None


def test_high_value_connector_list_is_sorted_and_stable() -> None:
    connectors = list_high_value_cloud_connectors()
    names = [connector.engine_name for connector in connectors]

    assert names == sorted(names, key=str.lower)
    assert "Databricks" in names
    assert "Snowflake" in names
    assert "Google BigQuery" in names
    assert len(connectors) >= 10


def test_generate_yaml_docs_includes_cloud_capability(mocker) -> None:
    from superset.db_engine_specs import lib

    mocker.patch(
        "superset.db_engine_specs.lib.load_engine_specs",
        return_value=[BigQueryEngineSpec, SqliteEngineSpec],
    )

    docs = lib.generate_yaml_docs()

    assert docs["Google BigQuery"]["cloud_capability"]["product_type"] == (
        "cloud_warehouse"
    )
    assert "cloud_capability" not in docs["SQLite"]
