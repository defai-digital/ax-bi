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
import { Operators } from 'src/explore/constants';

/**
 * Guided chart builder model. A {@link GuidedIntent} is the simplified,
 * business-level description of a chart that the guided builder collects. It is
 * compiled to (and read back from) the existing Explore `form_data` so the
 * advanced control panel and the chart preview stay in sync. See
 * ax-docs/ux-simplification-tech-spec.md.
 */

/** How a viz type consumes measures and dimensions. */
export type Arity = 'multi' | 'single' | 'none';

/**
 * Declarative description of a curated viz type: which `form_data` keys receive
 * the guided measures/dimensions and any constant extras (e.g. table needs
 * `query_mode: 'aggregate'`). This keeps viz-specific knowledge in data, not
 * branching logic, so adding a viz type is a one-line table entry.
 */
export interface VizDescriptor {
  /** The registered `viz_type` string (e.g. 'table', 'pie'). */
  key: string;
  /** Human label shown in the visualization picker. */
  label: string;
  /** 'multi' -> form_data.metrics[]; 'single' -> form_data.metric. */
  measures: Arity;
  /** 'multi' -> form_data.groupby[]; 'none' -> no dimensions. */
  dimensions: Arity;
  /**
   * Timeseries charts split dimensions: the first becomes `x_axis`, the rest
   * become `groupby` (series breakdown).
   */
  hasXAxis?: boolean;
  /** Constant form_data merged on compile (e.g. { query_mode: 'aggregate' }). */
  extraFormData?: Record<string, unknown>;
}

/** A single simple filter (column / operator / value). */
export interface GuidedFilter {
  column: string;
  operatorId: Operators;
  /** Omitted for unary operators (IS NULL / IS NOT NULL). */
  value?: string;
}

/** The complete guided description of a chart. */
export interface GuidedIntent {
  vizType: string;
  /** Saved metric names. */
  measures: string[];
  /** Column names. */
  dimensions: string[];
  filters: GuidedFilter[];
  rowLimit?: number;
}

/** An empty intent for a given viz type. */
export const emptyIntent = (vizType: string): GuidedIntent => ({
  vizType,
  measures: [],
  dimensions: [],
  filters: [],
});
