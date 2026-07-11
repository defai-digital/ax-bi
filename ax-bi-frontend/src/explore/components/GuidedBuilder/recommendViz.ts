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
import { getVizDescriptor } from './vizDescriptors';

export interface VizRecommendation {
  vizType: string;
  label: string;
  reason: string;
  score: number;
}

/**
 * Score guided-builder viz types from measure/dimension counts (Show Me lite).
 * Pure and deterministic — no I/O.
 */
export function recommendVizTypes(
  measureCount: number,
  dimensionCount: number,
  limit = 3,
): VizRecommendation[] {
  const m = Math.max(0, measureCount);
  const d = Math.max(0, dimensionCount);

  const scored: VizRecommendation[] = [
    {
      vizType: VizType.BigNumberTotal,
      label: getVizDescriptor(VizType.BigNumberTotal)?.label ?? t('Big Number'),
      reason: t('Single KPI total'),
      score: m >= 1 && d === 0 ? 100 : m === 1 && d === 0 ? 90 : 10,
    },
    {
      vizType: VizType.Table,
      label: getVizDescriptor(VizType.Table)?.label ?? t('Table'),
      reason: t('Flexible detail view'),
      score: m >= 1 || d >= 1 ? 55 + Math.min(m + d, 10) : 20,
    },
    {
      vizType: VizType.Bar,
      label: getVizDescriptor(VizType.Bar)?.label ?? t('Bar Chart'),
      reason: t('Compare categories'),
      score: m >= 1 && d >= 1 ? 85 + Math.min(d, 5) : m >= 1 ? 40 : 5,
    },
    {
      vizType: VizType.Line,
      label: getVizDescriptor(VizType.Line)?.label ?? t('Line Chart'),
      reason: t('Trends over a series'),
      score: m >= 1 && d >= 1 ? 80 : m >= 1 ? 35 : 5,
    },
    {
      vizType: VizType.Area,
      label: getVizDescriptor(VizType.Area)?.label ?? t('Area Chart'),
      reason: t('Volume over a series'),
      score: m >= 1 && d >= 1 ? 70 : 5,
    },
    {
      vizType: VizType.Pie,
      label: getVizDescriptor(VizType.Pie)?.label ?? t('Pie Chart'),
      reason: t('Part-to-whole share'),
      score: m === 1 && d >= 1 && d <= 2 ? 88 : m === 1 && d >= 1 ? 50 : 5,
    },
  ];

  return scored
    .filter(r => r.score > 15)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}
