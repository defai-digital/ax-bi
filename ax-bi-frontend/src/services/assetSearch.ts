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
import rison from 'rison';
import { AxBIClient } from '@ax-bi/ui-core';

/** Maximum number of results returned per asset type. */
export const ASSET_SEARCH_PAGE_SIZE = 8;

/** Asset types covered by global asset search. */
export const ASSET_SEARCH_TYPES = [
  'dashboards',
  'charts',
  'datasets',
  'databases',
  'savedQueries',
] as const;

export type AssetSearchType = (typeof ASSET_SEARCH_TYPES)[number];

export interface DashboardAsset {
  id: number;
  title: string;
  url?: string;
}

export interface ChartAsset {
  id: number;
  title: string;
  url?: string;
}

export interface DatasetAsset {
  id: number;
  title: string;
}

export interface DatabaseAsset {
  id: number;
  title: string;
}

export interface SavedQueryAsset {
  id: number;
  title: string;
}

/** Search results grouped by asset type. */
export interface AssetSearchResults {
  dashboards: DashboardAsset[];
  charts: ChartAsset[];
  datasets: DatasetAsset[];
  databases: DatabaseAsset[];
  savedQueries: SavedQueryAsset[];
}

export interface SearchAssetsOptions {
  /** Restrict the asset types to search. Defaults to all types. */
  types?: readonly AssetSearchType[];
  /** Signal to cancel in-flight requests. */
  signal?: AbortSignal;
  /** Maximum results per type. Defaults to {@link ASSET_SEARCH_PAGE_SIZE}. */
  pageSize?: number;
}

// Raw list-API row shapes (only the fields consumed here).
interface DashboardListRow {
  id: number;
  dashboard_title?: string;
  url?: string;
}

interface ChartListRow {
  id: number;
  slice_name?: string;
  url?: string;
}

interface DatasetListRow {
  id: number;
  table_name?: string;
}

interface DatabaseListRow {
  id: number;
  database_name?: string;
}

interface SavedQueryListRow {
  id: number;
  label?: string;
}

interface AssetTypeConfig<TRow, TAsset> {
  endpoint: string;
  filterColumn: string;
  mapRow: (row: TRow) => TAsset;
}

const ASSET_TYPE_CONFIG: {
  dashboards: AssetTypeConfig<DashboardListRow, DashboardAsset>;
  charts: AssetTypeConfig<ChartListRow, ChartAsset>;
  datasets: AssetTypeConfig<DatasetListRow, DatasetAsset>;
  databases: AssetTypeConfig<DatabaseListRow, DatabaseAsset>;
  savedQueries: AssetTypeConfig<SavedQueryListRow, SavedQueryAsset>;
} = {
  dashboards: {
    endpoint: '/api/v1/dashboard/',
    filterColumn: 'dashboard_title',
    mapRow: row => ({
      id: row.id,
      title: row.dashboard_title ?? '',
      url: row.url,
    }),
  },
  charts: {
    endpoint: '/api/v1/chart/',
    filterColumn: 'slice_name',
    mapRow: row => ({ id: row.id, title: row.slice_name ?? '', url: row.url }),
  },
  datasets: {
    endpoint: '/api/v1/dataset/',
    filterColumn: 'table_name',
    mapRow: row => ({ id: row.id, title: row.table_name ?? '' }),
  },
  databases: {
    endpoint: '/api/v1/database/',
    filterColumn: 'database_name',
    mapRow: row => ({ id: row.id, title: row.database_name ?? '' }),
  },
  savedQueries: {
    endpoint: '/api/v1/saved_query/',
    filterColumn: 'label',
    mapRow: row => ({ id: row.id, title: row.label ?? '' }),
  },
};

const EMPTY_RESULTS: AssetSearchResults = {
  dashboards: [],
  charts: [],
  datasets: [],
  databases: [],
  savedQueries: [],
};

async function searchType<TRow, TAsset>(
  config: AssetTypeConfig<TRow, TAsset>,
  query: string,
  pageSize: number,
  signal?: AbortSignal,
): Promise<TAsset[]> {
  const params = rison.encode({
    filters: [{ col: config.filterColumn, opr: 'ct', value: query }],
    page_size: pageSize,
    order_column: 'changed_on_delta_humanized',
    order_direction: 'desc',
  });
  const { json } = await AxBIClient.get({
    endpoint: `${config.endpoint}?q=${params}`,
    signal,
  });
  const rows = (json?.result ?? []) as TRow[];
  return rows.map(config.mapRow);
}

/**
 * Searches the asset list APIs (dashboards, charts, datasets, databases,
 * saved queries) by name using rison `ct` (contains) filters.
 *
 * Failures are contained per type: one failing endpoint yields an empty
 * group for that type without rejecting the others. An aborted search
 * rejects the whole promise so callers can ignore stale results.
 */
export async function searchAssets(
  query: string,
  {
    types,
    signal,
    pageSize = ASSET_SEARCH_PAGE_SIZE,
  }: SearchAssetsOptions = {},
): Promise<AssetSearchResults> {
  const trimmed = query.trim();
  if (!trimmed || signal?.aborted) {
    return { ...EMPTY_RESULTS };
  }

  const requested = new Set<AssetSearchType>(types ?? ASSET_SEARCH_TYPES);

  const searchOne = <TRow, TAsset>(
    type: AssetSearchType,
    config: AssetTypeConfig<TRow, TAsset>,
  ): Promise<TAsset[]> => {
    if (!requested.has(type)) {
      return Promise.resolve([]);
    }
    return searchType(config, trimmed, pageSize, signal).catch(error => {
      if (signal?.aborted) {
        throw error;
      }
      return [];
    });
  };

  const [dashboards, charts, datasets, databases, savedQueries] =
    await Promise.all([
      searchOne('dashboards', ASSET_TYPE_CONFIG.dashboards),
      searchOne('charts', ASSET_TYPE_CONFIG.charts),
      searchOne('datasets', ASSET_TYPE_CONFIG.datasets),
      searchOne('databases', ASSET_TYPE_CONFIG.databases),
      searchOne('savedQueries', ASSET_TYPE_CONFIG.savedQueries),
    ]);

  return { dashboards, charts, datasets, databases, savedQueries };
}

export default searchAssets;
