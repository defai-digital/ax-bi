/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

// ---- Common AxBI REST API response shapes ----

/** Standard envelope returned by AxBI list endpoints. */
export interface AxBIListEnvelope<T> {
  count: number;
  ids: number[];
  result: T[];
  label_columns?: Record<string, string>;
  description_columns?: Record<string, string>;
  list_columns?: Record<string, string>;
  list_title?: string;
  add_columns?: unknown[];
  edit_columns?: unknown[];
}

/** Standard envelope returned by AxBI single-item endpoints. */
export interface AxBIItemEnvelope<T> {
  id: number;
  result: T;
  show_title?: string;
  show_columns?: string[];
  description_columns?: Record<string, string>;
  label_columns?: Record<string, string>;
}

/** Standard delete response. */
export interface AxBIDeleteEnvelope {
  message: string;
}

// ---- Resource item types ----

export interface DashboardItem {
  id?: number;
  uuid?: string;
  dashboard_title?: string;
  slug?: string;
  url?: string;
  published?: boolean;
  certified_by?: string;
  certification_details?: string;
  description?: string;
  changed_on?: string;
  changed_on_humanized?: string;
  created_on?: string;
  created_by?: { first_name?: string; last_name?: string; username?: string };
  owners?: Array<{ first_name?: string; last_name?: string; username?: string }>;
  thumbnail_url?: string;
  css?: string;
  json_metadata?: string;
  position_json?: string;
}

export interface ChartItem {
  id?: number;
  uuid?: string;
  slice_name?: string;
  viz_type?: string;
  datasource_id?: number;
  datasource_type?: string;
  description?: string;
  url?: string;
  certified_by?: string;
  certification_details?: string;
  changed_on?: string;
  changed_on_humanized?: string;
  created_on?: string;
  created_by?: { first_name?: string; last_name?: string; username?: string };
  owners?: Array<{ first_name?: string; last_name?: string; username?: string }>;
  thumbnail_url?: string;
  params?: string;
  query_context?: string;
  cache_timeout?: number | null;
}

export interface DatasetItem {
  id?: number;
  uuid?: string;
  table_name?: string;
  schema?: string;
  database?: { database_name?: string; id?: number };
  description?: string;
  url?: string;
  certified_by?: string;
  certification_details?: string;
  changed_on?: string;
  changed_on_humanized?: string;
  created_on?: string;
  owners?: Array<{ first_name?: string; last_name?: string; username?: string }>;
  columns?: Array<{
    column_name?: string;
    type?: string;
    is_dttm?: boolean;
    description?: string;
  }>;
  metrics?: Array<{
    metric_name?: string;
    expression?: string;
    description?: string;
  }>;
}

export interface DatabaseItem {
  id?: number;
  uuid?: string;
  database_name?: string;
  backend?: string;
  sqlalchemy_uri?: string;
  expose_in_sqllab?: boolean;
  allow_run_async?: boolean;
  allow_ctas?: boolean;
  allow_cvas?: boolean;
  allow_dml?: boolean;
  extra?: string;
}

export interface QueryItem {
  id?: number;
  uuid?: string;
  tab_name?: string;
  sql?: string;
  sql_editor_id?: string;
  database?: { database_name?: string; id?: number };
  schema?: string;
  status?: string;
  start_time?: string;
  end_time?: string;
  rows?: number;
  error_message?: string;
  results_key?: string;
  tracking_url?: string;
  changed_on?: string;
  user?: { first_name?: string; last_name?: string; username?: string };
}

// ---- Create/Update input types ----

export interface CreateDashboardInput {
  dashboard_title: string;
  slug?: string;
  description?: string;
  certified_by?: string;
  certification_details?: string;
  published?: boolean;
  owners?: number[];
  css?: string;
  json_metadata?: string;
  position_json?: string;
}

export interface UpdateDashboardInput {
  dashboard_title?: string;
  slug?: string;
  description?: string;
  certified_by?: string;
  certification_details?: string;
  published?: boolean;
  owners?: number[];
  css?: string;
  json_metadata?: string;
  position_json?: string;
}

export interface CreateChartInput {
  slice_name: string;
  viz_type: string;
  datasource_id: number;
  datasource_type?: string;
  description?: string;
  certified_by?: string;
  certification_details?: string;
  owners?: number[];
  params?: string;
  query_context?: string;
  cache_timeout?: number | null;
}

export interface UpdateChartInput {
  slice_name?: string;
  viz_type?: string;
  datasource_id?: number;
  datasource_type?: string;
  description?: string;
  certified_by?: string;
  certification_details?: string;
  owners?: number[];
  params?: string;
  query_context?: string;
  cache_timeout?: number | null;
}

export interface CreateDatasetInput {
  table_name: string;
  database: number;
  schema?: string;
  description?: string;
  owners?: number[];
  columns?: Array<{
    column_name: string;
    type?: string;
    is_dttm?: boolean;
    description?: string;
  }>;
  metrics?: Array<{
    metric_name: string;
    expression: string;
    description?: string;
  }>;
}

export interface UpdateDatasetInput {
  table_name?: string;
  schema?: string;
  description?: string;
  owners?: number[];
  columns?: Array<{
    column_name: string;
    type?: string;
    is_dttm?: boolean;
    description?: string;
  }>;
  metrics?: Array<{
    metric_name: string;
    expression: string;
    description?: string;
  }>;
}
