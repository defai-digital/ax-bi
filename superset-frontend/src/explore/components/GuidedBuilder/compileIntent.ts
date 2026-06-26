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
import {
  DISABLE_INPUT_OPERATORS,
  MULTI_OPERATORS,
  OPERATOR_ENUM_TO_OPERATOR_TYPE,
} from 'src/explore/constants';
import { GuidedFilter, GuidedIntent } from './types';
import { getVizDescriptor } from './vizDescriptors';

/**
 * Build a SIMPLE adhoc filter object equivalent to the one the advanced filter
 * popover produces. Both `operator` (the SQL-ish operation, e.g. '==') and
 * `operatorId` (the enum, e.g. 'EQUALS') are set because different parts of the
 * frontend read each. Comparators follow the operator's arity: multi operators
 * (IN / NOT IN) take a string[] split on commas; value-less operators
 * (IS NULL / IS NOT NULL / IS TRUE / IS FALSE) carry no comparator.
 */
export function buildAdhocFilter(
  filter: GuidedFilter,
): Record<string, unknown> {
  const { column, operatorId, value } = filter;
  const operation = OPERATOR_ENUM_TO_OPERATOR_TYPE[operatorId]?.operation;
  const base: Record<string, unknown> = {
    expressionType: 'SIMPLE',
    subject: column,
    operator: operation,
    operatorId,
    clause: 'WHERE',
  };

  if (DISABLE_INPUT_OPERATORS.includes(operatorId)) {
    return base;
  }
  if (MULTI_OPERATORS.has(operatorId)) {
    const list = (value ?? '')
      .split(',')
      .map(part => part.trim())
      .filter(Boolean);
    return { ...base, comparator: list };
  }
  return { ...base, comparator: value ?? '' };
}

/**
 * Compile a {@link GuidedIntent} into a partial `form_data` map of
 * control-name -> value. Each key is dispatched via `setControlValue`, so the
 * result drives the exact same query_context the advanced panel would. Only the
 * keys relevant to the selected viz type are emitted; viz types not in the
 * curated set return just `{ viz_type }` (the guided builder does not offer
 * them).
 */
export function compileIntent(intent: GuidedIntent): Record<string, unknown> {
  const descriptor = getVizDescriptor(intent.vizType);
  const formData: Record<string, unknown> = { viz_type: intent.vizType };
  if (!descriptor) {
    return formData;
  }

  // Measures.
  if (descriptor.measures === 'multi') {
    formData.metrics = intent.measures;
  } else if (descriptor.measures === 'single') {
    formData.metric = intent.measures[0] ?? null;
  }

  // Dimensions. Timeseries charts route the first dimension to the x-axis and
  // the remainder to the series breakdown (groupby).
  if (descriptor.hasXAxis) {
    const [first, ...rest] = intent.dimensions;
    formData.x_axis = first ?? null;
    formData.groupby = rest;
  } else if (descriptor.dimensions === 'multi') {
    formData.groupby = intent.dimensions;
  } else if (descriptor.dimensions === 'single') {
    formData.groupby = intent.dimensions.slice(0, 1);
  }

  // Filters.
  formData.adhoc_filters = intent.filters.map(buildAdhocFilter);

  // Row limit (only when the user set one).
  if (intent.rowLimit != null) {
    formData.row_limit = intent.rowLimit;
  }

  // Constant viz-specific extras (e.g. table query_mode).
  return { ...formData, ...descriptor.extraFormData };
}
