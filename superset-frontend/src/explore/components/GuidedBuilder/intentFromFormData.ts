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
import { JsonObject } from '@superset-ui/core';
import { Operators } from 'src/explore/constants';
import { GuidedFilter, GuidedIntent } from './types';
import { getVizDescriptor } from './vizDescriptors';

/** Keep only plain saved-metric / column names (strings). Adhoc objects are
 * left untouched in form_data and surfaced via the advanced panel instead. */
const stringsOnly = (value: unknown): string[] => {
  if (Array.isArray(value)) {
    return value.filter((item): item is string => typeof item === 'string');
  }
  return typeof value === 'string' ? [value] : [];
};

const toGuidedFilter = (raw: JsonObject): GuidedFilter | undefined => {
  if (raw?.expressionType !== 'SIMPLE' || !raw?.subject || !raw?.operatorId) {
    return undefined;
  }
  const { comparator } = raw;
  const value = Array.isArray(comparator)
    ? comparator.join(', ')
    : comparator == null
      ? undefined
      : String(comparator);
  return {
    column: raw.subject as string,
    operatorId: raw.operatorId as Operators,
    value,
  };
};

/**
 * Read an existing `form_data` into a {@link GuidedIntent}. Only the pieces the
 * guided builder can represent (saved metrics, plain columns, simple filters)
 * are extracted; adhoc metrics/columns/SQL filters are intentionally ignored
 * here and remain editable in the advanced panel. Pure and side-effect free.
 */
export function intentFromFormData(formData?: JsonObject): GuidedIntent {
  const vizType = (formData?.viz_type as string) ?? '';
  const descriptor = getVizDescriptor(vizType);

  const measures =
    descriptor?.measures === 'single'
      ? stringsOnly(formData?.metric)
      : stringsOnly(formData?.metrics);

  const dimensions = descriptor?.hasXAxis
    ? [...stringsOnly(formData?.x_axis), ...stringsOnly(formData?.groupby)]
    : stringsOnly(formData?.groupby);

  const filters = Array.isArray(formData?.adhoc_filters)
    ? (formData?.adhoc_filters as JsonObject[])
        .map(toGuidedFilter)
        .filter((f): f is GuidedFilter => f !== undefined)
    : [];

  const rowLimit =
    typeof formData?.row_limit === 'number'
      ? (formData?.row_limit as number)
      : undefined;

  return { vizType, measures, dimensions, filters, rowLimit };
}
