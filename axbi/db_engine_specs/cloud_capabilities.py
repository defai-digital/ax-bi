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

from dataclasses import dataclass
from enum import Enum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from axbi.db_engine_specs.base import BaseEngineSpec


_CLOUD_AWS_CATEGORIES = {"CLOUD_AWS", "Cloud - AWS"}
_CLOUD_GCP_CATEGORIES = {"CLOUD_GCP", "Cloud - Google"}
_CLOUD_AZURE_CATEGORIES = {"CLOUD_AZURE", "Cloud - Azure"}
_CLOUD_WAREHOUSE_CATEGORIES = {
    "CLOUD_DATA_WAREHOUSES",
    "Cloud Data Warehouses",
}
_ANALYTICAL_CATEGORIES = {"ANALYTICAL_DATABASES", "Analytical Databases"}
_QUERY_ENGINE_CATEGORIES = {"QUERY_ENGINES", "Query Engines"}
_SEARCH_NOSQL_CATEGORIES = {"SEARCH_NOSQL", "Search & NoSQL"}
_PROVIDER_CATEGORIES = (
    _CLOUD_AWS_CATEGORIES
    | _CLOUD_GCP_CATEGORIES
    | _CLOUD_AZURE_CATEGORIES
    | _CLOUD_WAREHOUSE_CATEGORIES
)


class CloudDataProductType(str, Enum):
    """Product-level grouping for cloud data connectors."""

    CLOUD_WAREHOUSE = "cloud_warehouse"
    LAKEHOUSE = "lakehouse"
    DATA_LAKE_QUERY_ENGINE = "data_lake_query_engine"
    QUERY_ENGINE = "query_engine"
    NOSQL_OR_SEARCH = "nosql_or_search"
    EMBEDDED_OR_EDGE_SQL = "embedded_or_edge_sql"
    OBSERVABILITY_ANALYTICS = "observability_analytics"


class CloudConnectorSupportLevel(str, Enum):
    """Product-facing support status for a connector."""

    CERTIFIED = "certified"
    PACKAGED = "packaged"
    COMPATIBLE = "compatible"
    INTEGRATION_CANDIDATE = "integration_candidate"


@dataclass(frozen=True)
class CloudConnectorCapability:
    """Machine-readable cloud connector capability for an engine spec."""

    engine: str
    engine_name: str
    product_type: CloudDataProductType
    support_level: CloudConnectorSupportLevel
    cloud_providers: tuple[str, ...]
    data_products: tuple[str, ...]
    recommended: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of this capability."""

        return {
            "engine": self.engine,
            "engine_name": self.engine_name,
            "product_type": self.product_type.value,
            "support_level": self.support_level.value,
            "cloud_providers": list(self.cloud_providers),
            "data_products": list(self.data_products),
            "recommended": self.recommended,
            "notes": self.notes,
        }


_HIGH_VALUE_CONNECTORS: dict[str, CloudConnectorCapability] = {
    "amazon athena": CloudConnectorCapability(
        engine="awsathena",
        engine_name="Amazon Athena",
        product_type=CloudDataProductType.DATA_LAKE_QUERY_ENGINE,
        support_level=CloudConnectorSupportLevel.PACKAGED,
        cloud_providers=("AWS",),
        data_products=("S3", "AWS Glue Data Catalog", "Apache Iceberg"),
        recommended=True,
        notes="Primary AWS data lake SQL path for S3-backed analytics.",
    ),
    "amazon dynamodb": CloudConnectorCapability(
        engine="dynamodb",
        engine_name="Amazon DynamoDB",
        product_type=CloudDataProductType.NOSQL_OR_SEARCH,
        support_level=CloudConnectorSupportLevel.COMPATIBLE,
        cloud_providers=("AWS",),
        data_products=("DynamoDB",),
        notes="Useful for operational NoSQL analytics when SQL-like access is enough.",
    ),
    "amazon redshift": CloudConnectorCapability(
        engine="redshift",
        engine_name="Amazon Redshift",
        product_type=CloudDataProductType.CLOUD_WAREHOUSE,
        support_level=CloudConnectorSupportLevel.PACKAGED,
        cloud_providers=("AWS",),
        data_products=("Redshift", "Redshift Serverless"),
        recommended=True,
        notes="Primary AWS cloud warehouse connector.",
    ),
    "azure data explorer": CloudConnectorCapability(
        engine="kustosql",
        engine_name="Azure Data Explorer",
        product_type=CloudDataProductType.OBSERVABILITY_ANALYTICS,
        support_level=CloudConnectorSupportLevel.PACKAGED,
        cloud_providers=("Azure",),
        data_products=("Azure Data Explorer", "Kusto"),
        recommended=True,
        notes="Best fit for telemetry, logs, time series, and operational analytics.",
    ),
    "azure data explorer (kql)": CloudConnectorCapability(
        engine="kustokql",
        engine_name="Azure Data Explorer (KQL)",
        product_type=CloudDataProductType.OBSERVABILITY_ANALYTICS,
        support_level=CloudConnectorSupportLevel.PACKAGED,
        cloud_providers=("Azure",),
        data_products=("Azure Data Explorer", "Kusto"),
        notes="Native KQL path for advanced Azure Data Explorer workloads.",
    ),
    "azure synapse": CloudConnectorCapability(
        engine="mssql",
        engine_name="Azure Synapse",
        product_type=CloudDataProductType.CLOUD_WAREHOUSE,
        support_level=CloudConnectorSupportLevel.COMPATIBLE,
        cloud_providers=("Azure",),
        data_products=("Azure Synapse", "Microsoft Fabric SQL Endpoint"),
        recommended=True,
        notes="SQL Server-compatible path for Microsoft cloud warehouse workloads.",
    ),
    "clickhouse": CloudConnectorCapability(
        engine="clickhouse",
        engine_name="ClickHouse",
        product_type=CloudDataProductType.CLOUD_WAREHOUSE,
        support_level=CloudConnectorSupportLevel.COMPATIBLE,
        cloud_providers=("Cloud", "Self-hosted"),
        data_products=("ClickHouse Cloud", "ClickHouse"),
        recommended=True,
        notes="High-performance analytical database for event and product analytics.",
    ),
    "cloudflare d1": CloudConnectorCapability(
        engine="d1",
        engine_name="Cloudflare D1",
        product_type=CloudDataProductType.EMBEDDED_OR_EDGE_SQL,
        support_level=CloudConnectorSupportLevel.COMPATIBLE,
        cloud_providers=("Cloudflare",),
        data_products=("D1", "SQLite"),
        recommended=True,
        notes="Serverless SQLite-compatible database for edge applications.",
    ),
    "databricks": CloudConnectorCapability(
        engine="databricks",
        engine_name="Databricks",
        product_type=CloudDataProductType.LAKEHOUSE,
        support_level=CloudConnectorSupportLevel.PACKAGED,
        cloud_providers=("AWS", "Azure", "Google Cloud"),
        data_products=("Databricks SQL Warehouse", "Unity Catalog", "Delta Lake"),
        recommended=True,
        notes="Primary lakehouse connector for SQL warehouses and governed data.",
    ),
    "databricks interactive cluster": CloudConnectorCapability(
        engine="databricks",
        engine_name="Databricks Interactive Cluster",
        product_type=CloudDataProductType.LAKEHOUSE,
        support_level=CloudConnectorSupportLevel.COMPATIBLE,
        cloud_providers=("AWS", "Azure", "Google Cloud"),
        data_products=("Databricks All-purpose Compute", "Delta Lake"),
        notes="Legacy cluster path; prefer Databricks SQL warehouses.",
    ),
    "dremio": CloudConnectorCapability(
        engine="dremio",
        engine_name="Dremio",
        product_type=CloudDataProductType.LAKEHOUSE,
        support_level=CloudConnectorSupportLevel.COMPATIBLE,
        cloud_providers=("Cloud", "Self-hosted"),
        data_products=("Dremio", "Apache Iceberg", "Object Storage"),
        recommended=True,
        notes="Lakehouse query engine for governed object-store analytics.",
    ),
    "duckdb": CloudConnectorCapability(
        engine="duckdb",
        engine_name="DuckDB",
        product_type=CloudDataProductType.QUERY_ENGINE,
        support_level=CloudConnectorSupportLevel.PACKAGED,
        cloud_providers=("Local", "Object Storage"),
        data_products=("DuckDB", "Parquet", "CSV", "Iceberg"),
        notes="Embedded analytical engine for local and object-store data.",
    ),
    "google bigquery": CloudConnectorCapability(
        engine="bigquery",
        engine_name="Google BigQuery",
        product_type=CloudDataProductType.CLOUD_WAREHOUSE,
        support_level=CloudConnectorSupportLevel.PACKAGED,
        cloud_providers=("Google Cloud",),
        data_products=("BigQuery", "BigLake", "External Tables"),
        recommended=True,
        notes="Primary Google Cloud warehouse and lake analytics connector.",
    ),
    "google datastore": CloudConnectorCapability(
        engine="datastore",
        engine_name="Google Datastore",
        product_type=CloudDataProductType.NOSQL_OR_SEARCH,
        support_level=CloudConnectorSupportLevel.COMPATIBLE,
        cloud_providers=("Google Cloud",),
        data_products=("Datastore", "Firestore in Datastore mode"),
        notes="Operational NoSQL analytics connector.",
    ),
    "motherduck": CloudConnectorCapability(
        engine="motherduck",
        engine_name="MotherDuck",
        product_type=CloudDataProductType.CLOUD_WAREHOUSE,
        support_level=CloudConnectorSupportLevel.PACKAGED,
        cloud_providers=("MotherDuck",),
        data_products=("MotherDuck", "DuckDB"),
        recommended=True,
        notes="DuckDB-compatible serverless cloud analytics connector.",
    ),
    "snowflake": CloudConnectorCapability(
        engine="snowflake",
        engine_name="Snowflake",
        product_type=CloudDataProductType.CLOUD_WAREHOUSE,
        support_level=CloudConnectorSupportLevel.PACKAGED,
        cloud_providers=("AWS", "Azure", "Google Cloud"),
        data_products=("Snowflake", "External Tables", "Apache Iceberg"),
        recommended=True,
        notes="Primary multi-cloud warehouse connector.",
    ),
    "trino": CloudConnectorCapability(
        engine="trino",
        engine_name="Trino",
        product_type=CloudDataProductType.DATA_LAKE_QUERY_ENGINE,
        support_level=CloudConnectorSupportLevel.PACKAGED,
        cloud_providers=("Cloud", "Self-hosted"),
        data_products=("Apache Iceberg", "Hive", "Delta Lake", "Object Storage"),
        recommended=True,
        notes="Open query engine for lakehouse and federated SQL workloads.",
    ),
}


def _metadata_categories(spec: type["BaseEngineSpec"]) -> tuple[str, ...]:
    metadata: dict[str, Any] = getattr(spec, "metadata", {}) or {}
    categories = metadata.get("categories", ())
    return tuple(str(category) for category in categories)


def _infer_cloud_providers(categories: tuple[str, ...]) -> tuple[str, ...]:
    providers = []
    category_set = set(categories)
    if category_set & _CLOUD_AWS_CATEGORIES:
        providers.append("AWS")
    if category_set & _CLOUD_AZURE_CATEGORIES:
        providers.append("Azure")
    if category_set & _CLOUD_GCP_CATEGORIES:
        providers.append("Google Cloud")
    if category_set & _CLOUD_WAREHOUSE_CATEGORIES:
        providers.append("Cloud")
    return tuple(dict.fromkeys(providers))


def _infer_product_type(
    categories: tuple[str, ...],
) -> CloudDataProductType | None:
    category_set = set(categories)
    if category_set & _CLOUD_WAREHOUSE_CATEGORIES:
        return CloudDataProductType.CLOUD_WAREHOUSE
    if category_set & _QUERY_ENGINE_CATEGORIES:
        return CloudDataProductType.QUERY_ENGINE
    if category_set & _SEARCH_NOSQL_CATEGORIES:
        return CloudDataProductType.NOSQL_OR_SEARCH
    if category_set & _ANALYTICAL_CATEGORIES and category_set & _PROVIDER_CATEGORIES:
        return CloudDataProductType.CLOUD_WAREHOUSE
    return None


def get_cloud_connector_capability(
    spec: type["BaseEngineSpec"],
) -> CloudConnectorCapability | None:
    """Return cloud connector capability metadata for an engine spec."""

    return get_cloud_connector_capability_for_values(
        engine=spec.engine,
        engine_name=spec.engine_name or spec.engine,
        categories=_metadata_categories(spec),
    )


def get_cloud_connector_capability_for_values(
    engine: str,
    engine_name: str,
    categories: tuple[str, ...] | list[str] = (),
) -> CloudConnectorCapability | None:
    """Return cloud connector capability metadata for raw engine values."""

    if capability := _HIGH_VALUE_CONNECTORS.get(engine_name.lower()):
        return capability

    categories = tuple(str(category) for category in categories)
    providers = _infer_cloud_providers(categories)
    product_type = _infer_product_type(categories)

    if not providers or product_type is None:
        return None

    return CloudConnectorCapability(
        engine=engine,
        engine_name=engine_name,
        product_type=product_type,
        support_level=CloudConnectorSupportLevel.COMPATIBLE,
        cloud_providers=providers,
        data_products=(engine_name,),
        notes="Inferred from engine spec cloud categories.",
    )


def list_high_value_cloud_connectors() -> tuple[CloudConnectorCapability, ...]:
    """Return the curated high-value cloud connector list in display order."""

    return tuple(
        sorted(
            _HIGH_VALUE_CONNECTORS.values(),
            key=lambda capability: capability.engine_name.lower(),
        )
    )
