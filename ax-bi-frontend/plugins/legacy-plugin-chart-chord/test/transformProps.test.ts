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
import transformProps from '../src/transformProps';

test('returns a typed empty chord payload when queries have no rows', () => {
  const props = {
    width: 400,
    height: 300,
    formData: { yAxisFormat: '.2f', colorScheme: 'bnbColors', sliceId: 9 },
    queriesData: [],
  } as unknown as ChartProps;

  const result = transformProps(props);
  expect(result.data).toEqual({ nodes: [], matrix: [] });
  expect(result.width).toBe(400);
  expect(result.sliceId).toBe(9);
});

test('passes through a valid chord matrix payload', () => {
  const payload = {
    nodes: ['A', 'B'],
    matrix: [
      [0, 1],
      [2, 0],
    ],
  };
  const props = {
    width: 100,
    height: 100,
    formData: { yAxisFormat: '.1f', colorScheme: 'bnbColors', sliceId: 1 },
    queriesData: [{ data: payload }],
  } as unknown as ChartProps;

  expect(transformProps(props).data).toEqual(payload);
});
