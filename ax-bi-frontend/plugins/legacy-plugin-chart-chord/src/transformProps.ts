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
import { ChartProps } from '@ax-bi/ui-core';

export default function transformProps(chartProps: ChartProps) {
  const { width, height, formData, queriesData } = chartProps;
  const { yAxisFormat, colorScheme, sliceId } = formData;

  // Prefer a well-typed empty chord payload over [] so the render path does not
  // destructure matrix/nodes from an array (which yields undefined and throws).
  const raw = queriesData[0]?.data;
  const data =
    raw &&
    typeof raw === 'object' &&
    !Array.isArray(raw) &&
    Array.isArray((raw as { nodes?: unknown }).nodes) &&
    Array.isArray((raw as { matrix?: unknown }).matrix)
      ? raw
      : { nodes: [] as string[], matrix: [] as number[][] };

  return {
    colorScheme,
    data,
    height,
    numberFormat: yAxisFormat,
    width,
    sliceId,
  };
}
