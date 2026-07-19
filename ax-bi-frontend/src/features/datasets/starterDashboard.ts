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
import { DatasourceType, AxBIClient, VizType } from '@ax-bi/ui-core';
import { t } from '@ax-bi/core/translation';

export interface DatasetColumnLike {
  column_name: string;
  verbose_name?: string | null;
  type_generic?: number | null;
  is_dttm?: boolean;
  expression?: string | null;
}

export interface DatasetMetricLike {
  metric_name: string;
  verbose_name?: string | null;
  expression?: string;
}

export interface DatasetLike {
  id: number;
  table_name: string;
  columns?: DatasetColumnLike[];
  metrics?: DatasetMetricLike[];
  datasource_name?: string;
}

export interface StarterChartPlan {
  slice_name: string;
  viz_type: string;
  params: Record<string, unknown>;
}

const GENERIC_NUMERIC = 0; // GenericDataType.Numeric in @ax-bi/ui-core

/**
 * Build a small set of chart plans from dataset metadata (X-ray lite).
 * Pure — no network.
 */
export function planStarterCharts(dataset: DatasetLike): StarterChartPlan[] {
  const datasource = `${dataset.id}__${DatasourceType.Table}`;
  const metrics = dataset.metrics ?? [];
  const columns = dataset.columns ?? [];
  const firstMetric =
    metrics.find(m => m.metric_name === 'count')?.metric_name ||
    metrics[0]?.metric_name ||
    'count';
  const dimCandidates = columns.filter(
    c => !c.is_dttm && c.type_generic !== GENERIC_NUMERIC,
  );
  const firstDim = dimCandidates[0]?.column_name;
  const timeCol = columns.find(c => c.is_dttm)?.column_name;
  const tableName = dataset.table_name || t('Dataset');

  const plans: StarterChartPlan[] = [
    {
      slice_name: t('%s — total', tableName),
      viz_type: VizType.BigNumberTotal,
      params: {
        datasource,
        viz_type: VizType.BigNumberTotal,
        metric: firstMetric,
        header_font_size: 0.4,
        subheader_font_size: 0.15,
      },
    },
    {
      slice_name: t('%s — table', tableName),
      viz_type: VizType.Table,
      params: {
        datasource,
        viz_type: VizType.Table,
        query_mode: 'aggregate',
        metrics: [firstMetric],
        groupby: firstDim ? [firstDim] : [],
        row_limit: 50,
        all_columns: [],
      },
    },
  ];

  if (firstDim) {
    plans.push({
      slice_name: t('%s — by %s', tableName, firstDim),
      viz_type: VizType.Bar,
      params: {
        datasource,
        viz_type: VizType.Bar,
        metrics: [firstMetric],
        x_axis: firstDim,
        groupby: [],
        row_limit: 25,
      },
    });
  } else if (timeCol) {
    plans.push({
      slice_name: t('%s — over time', tableName),
      viz_type: VizType.Line,
      params: {
        datasource,
        viz_type: VizType.Line,
        metrics: [firstMetric],
        x_axis: timeCol,
        groupby: [],
        row_limit: 100,
      },
    });
  }

  return plans;
}

/**
 * Create charts and a dashboard from a dataset id.
 * Returns dashboard id on success.
 */
export async function createStarterDashboard(
  datasetId: number,
): Promise<{ dashboardId: number; dashboardTitle: string }> {
  const dsRes = await AxBIClient.get({
    endpoint: `/api/v1/dataset/${datasetId}`,
  });
  const dataset = dsRes.json?.result as DatasetLike;
  if (!dataset?.id) {
    throw new Error(t('Dataset not found'));
  }

  const plans = planStarterCharts(dataset);
  const chartIds: number[] = [];

  for (const plan of plans) {
    const chartRes = await AxBIClient.post({
      endpoint: `/api/v1/chart/`,
      jsonPayload: {
        slice_name: plan.slice_name,
        viz_type: plan.viz_type,
        datasource_id: dataset.id,
        datasource_type: DatasourceType.Table,
        params: JSON.stringify(plan.params),
        dashboards: [],
        owners: [],
      },
    });
    const id = chartRes.json?.id ?? chartRes.json?.result?.id;
    if (id) {
      chartIds.push(Number(id));
    }
  }

  if (chartIds.length === 0) {
    throw new Error(t('Could not create starter charts'));
  }

  const dashboardTitle = t('%s — starter dashboard', dataset.table_name);
  const dashRes = await AxBIClient.post({
    endpoint: `/api/v1/dashboard/`,
    jsonPayload: { dashboard_title: dashboardTitle },
  });
  const dashboardId = Number(dashRes.json?.id ?? dashRes.json?.result?.id);
  if (!dashboardId) {
    throw new Error(t('Could not create dashboard'));
  }

  // Attach charts via position JSON (simple vertical stack)
  const position: Record<string, unknown> = {
    DASHBOARD_VERSION_KEY: 'v2',
    ROOT_ID: {
      type: 'ROOT',
      id: 'ROOT_ID',
      children: ['GRID_ID'],
    },
    GRID_ID: {
      type: 'GRID',
      id: 'GRID_ID',
      children: chartIds.map((_, i) => `ROW-${i}`),
      parents: ['ROOT_ID'],
    },
    HEADER_ID: {
      id: 'HEADER_ID',
      type: 'HEADER',
      meta: { text: dashboardTitle },
    },
  };

  chartIds.forEach((chartId, i) => {
    const rowId = `ROW-${i}`;
    const chartKey = `CHART-${chartId}`;
    (position.GRID_ID as { children: string[] }).children = chartIds.map(
      (_, idx) => `ROW-${idx}`,
    );
    position[rowId] = {
      type: 'ROW',
      id: rowId,
      children: [chartKey],
      parents: ['ROOT_ID', 'GRID_ID'],
      meta: { background: 'BACKGROUND_TRANSPARENT' },
    };
    position[chartKey] = {
      type: 'CHART',
      id: chartKey,
      children: [],
      parents: ['ROOT_ID', 'GRID_ID', rowId],
      meta: {
        chartId,
        width: 12,
        height: 50,
        sliceName: plans[i]?.slice_name,
      },
    };
  });

  await AxBIClient.put({
    endpoint: `/api/v1/dashboard/${dashboardId}`,
    jsonPayload: {
      json_metadata: JSON.stringify({}),
      position_json: JSON.stringify(position),
    },
  });

  // Link charts to dashboard
  await Promise.all(
    chartIds.map(chartId =>
      AxBIClient.put({
        endpoint: `/api/v1/chart/${chartId}`,
        jsonPayload: { dashboards: [dashboardId] },
      }),
    ),
  );

  return { dashboardId, dashboardTitle };
}
