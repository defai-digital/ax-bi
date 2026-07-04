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
import { VizType } from '@superset-ui/core';
import { t } from '@apache-superset/core/translation';
import { VizDescriptor } from './types';

/**
 * Curated set of viz types supported by the guided builder. Each entry's
 * measure/dimension keys were verified against the corresponding plugin
 * controlPanel: table & timeseries use `metrics` (array); pie & big number use
 * `metric` (single); timeseries charts route the first dimension to `x_axis`.
 *
 * This is intentionally a small, high-confidence set. Every other viz type
 * remains fully available through the advanced control panel.
 */
export const VIZ_DESCRIPTORS: VizDescriptor[] = [
  {
    key: VizType.Table,
    label: t('Table'),
    measures: 'multi',
    dimensions: 'multi',
    extraFormData: { query_mode: 'aggregate' },
  },
  {
    key: VizType.BigNumberTotal,
    label: t('Big Number'),
    measures: 'single',
    dimensions: 'none',
  },
  {
    key: VizType.Pie,
    label: t('Pie Chart'),
    measures: 'single',
    dimensions: 'multi',
  },
  {
    key: VizType.Bar,
    label: t('Bar Chart'),
    measures: 'multi',
    dimensions: 'multi',
    hasXAxis: true,
  },
  {
    key: VizType.Line,
    label: t('Line Chart'),
    measures: 'multi',
    dimensions: 'multi',
    hasXAxis: true,
  },
  {
    key: VizType.Area,
    label: t('Area Chart'),
    measures: 'multi',
    dimensions: 'multi',
    hasXAxis: true,
  },
];

const BY_KEY: Record<string, VizDescriptor> = VIZ_DESCRIPTORS.reduce(
  (acc, d) => ({ ...acc, [d.key]: d }),
  {},
);

/** The descriptor for a viz type, or undefined if not guided-supported. */
export const getVizDescriptor = (
  vizType?: string,
): VizDescriptor | undefined => (vizType ? BY_KEY[vizType] : undefined);

/** Whether the guided builder can represent this viz type. */
export const isGuidedVizType = (vizType?: string): boolean =>
  !!vizType && vizType in BY_KEY;

/** Default viz type when entering the guided builder fresh. */
export const DEFAULT_GUIDED_VIZ_TYPE = VizType.Table;
