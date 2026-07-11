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

/**
 * Default chart types shown first when CURATED_VIZ_GALLERY is enabled.
 * Stable viz_type plugin keys — long-tail types remain available under
 * "More charts". See .internal/docs/ui-ux-improvement-tech-spec.md.
 */
export const CURATED_VIZ_TYPES: readonly string[] = [
  VizType.Table,
  VizType.BigNumberTotal,
  VizType.Bar,
  VizType.Line,
  VizType.Area,
  VizType.Pie,
  VizType.Scatter,
  VizType.PivotTable,
  VizType.WorldMap,
  VizType.Heatmap,
  VizType.Histogram,
  VizType.Treemap,
  VizType.Funnel,
  VizType.Sankey,
];

const curatedSet = new Set(CURATED_VIZ_TYPES);

export function isCuratedVizType(vizType: string | null | undefined): boolean {
  return !!vizType && curatedSet.has(vizType);
}

/**
 * Order entries for the curated gallery: curated keys first (stable list order),
 * then ensure selectedViz is present even if outside the curated set.
 */
export function orderCuratedVizEntries<T extends { key: string }>(
  entries: T[],
  selectedViz: string | null,
): T[] {
  const byKey = new Map(entries.map(entry => [entry.key, entry]));
  const ordered: T[] = [];

  CURATED_VIZ_TYPES.forEach(key => {
    const entry = byKey.get(key);
    if (entry) {
      ordered.push(entry);
    }
  });

  if (selectedViz && !isCuratedVizType(selectedViz)) {
    const selected = byKey.get(selectedViz);
    if (selected && !ordered.some(e => e.key === selectedViz)) {
      ordered.unshift(selected);
    }
  }

  return ordered;
}
