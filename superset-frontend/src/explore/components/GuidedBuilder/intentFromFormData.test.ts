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
import { Operators } from 'src/explore/constants';
import { intentFromFormData } from './intentFromFormData';
import { compileIntent } from './compileIntent';

test('reads table form_data back into an intent', () => {
  const intent = intentFromFormData({
    viz_type: VizType.Table,
    metrics: ['count', 'sum__x'],
    groupby: ['country'],
    row_limit: 500,
    adhoc_filters: [
      {
        expressionType: 'SIMPLE',
        subject: 'country',
        operator: 'IN',
        operatorId: Operators.In,
        comparator: ['US', 'CA'],
        clause: 'WHERE',
      },
    ],
  });
  expect(intent.measures).toEqual(['count', 'sum__x']);
  expect(intent.dimensions).toEqual(['country']);
  expect(intent.rowLimit).toBe(500);
  expect(intent.filters).toEqual([
    { column: 'country', operatorId: Operators.In, value: 'US, CA' },
  ]);
});

test('reads singular metric for pie', () => {
  const intent = intentFromFormData({
    viz_type: VizType.Pie,
    metric: 'sum__sales',
    groupby: ['region'],
  });
  expect(intent.measures).toEqual(['sum__sales']);
  expect(intent.dimensions).toEqual(['region']);
});

test('reconstructs x_axis + groupby into dimensions for timeseries', () => {
  const intent = intentFromFormData({
    viz_type: VizType.Bar,
    metrics: ['count'],
    x_axis: 'ds',
    groupby: ['country'],
  });
  expect(intent.dimensions).toEqual(['ds', 'country']);
});

test('ignores adhoc (object) metrics and SQL filters', () => {
  const intent = intentFromFormData({
    viz_type: VizType.Table,
    metrics: ['count', { expressionType: 'SQL', sqlExpression: 'SUM(x)' }],
    adhoc_filters: [{ expressionType: 'SQL', sqlExpression: 'x > 1' }],
  });
  expect(intent.measures).toEqual(['count']);
  expect(intent.filters).toEqual([]);
});

test('round-trips: compile(read(fd)) preserves the guided-representable parts', () => {
  const formData = {
    viz_type: VizType.Table,
    metrics: ['count'],
    groupby: ['country'],
    row_limit: 100,
    adhoc_filters: [
      {
        expressionType: 'SIMPLE',
        subject: 'country',
        operator: '==',
        operatorId: Operators.Equals,
        comparator: 'US',
        clause: 'WHERE',
      },
    ],
  };
  const recompiled = compileIntent(intentFromFormData(formData));
  expect(recompiled.metrics).toEqual(['count']);
  expect(recompiled.groupby).toEqual(['country']);
  expect(recompiled.row_limit).toBe(100);
  expect(recompiled.adhoc_filters).toEqual([
    {
      expressionType: 'SIMPLE',
      subject: 'country',
      operator: '==',
      operatorId: Operators.Equals,
      comparator: 'US',
      clause: 'WHERE',
    },
  ]);
});

test('empty / undefined form_data yields an empty intent', () => {
  const intent = intentFromFormData(undefined);
  expect(intent).toEqual({
    vizType: '',
    measures: [],
    dimensions: [],
    filters: [],
    rowLimit: undefined,
  });
});
