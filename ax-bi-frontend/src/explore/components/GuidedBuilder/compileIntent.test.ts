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
import { VizType } from '@ax-bi/ui-core';
import { Operators } from 'src/explore/constants';
import { compileIntent, buildAdhocFilter } from './compileIntent';
import { GuidedIntent } from './types';

const base: GuidedIntent = {
  vizType: VizType.Table,
  measures: ['count'],
  dimensions: ['country'],
  filters: [],
};

test('table compiles measures->metrics, dimensions->groupby, adds query_mode', () => {
  const fd = compileIntent(base);
  expect(fd.viz_type).toBe(VizType.Table);
  expect(fd.metrics).toEqual(['count']);
  expect(fd.groupby).toEqual(['country']);
  expect(fd.query_mode).toBe('aggregate');
  expect(fd.adhoc_filters).toEqual([]);
});

test('pie uses singular metric and keeps groupby', () => {
  const fd = compileIntent({
    ...base,
    vizType: VizType.Pie,
    measures: ['sum__sales', 'ignored_second'],
  });
  expect(fd.metric).toBe('sum__sales');
  expect(fd.metrics).toBeUndefined();
  expect(fd.groupby).toEqual(['country']);
});

test('big number uses singular metric and no dimensions', () => {
  const fd = compileIntent({
    ...base,
    vizType: VizType.BigNumberTotal,
    measures: ['count'],
    dimensions: ['country'],
  });
  expect(fd.metric).toBe('count');
  expect(fd.groupby).toBeUndefined();
});

test('timeseries routes first dimension to x_axis and rest to groupby', () => {
  const fd = compileIntent({
    ...base,
    vizType: VizType.Line,
    measures: ['count'],
    dimensions: ['ds', 'country', 'product'],
  });
  expect(fd.x_axis).toBe('ds');
  expect(fd.groupby).toEqual(['country', 'product']);
  expect(fd.metrics).toEqual(['count']);
});

test('single-measure viz with no measure selected yields null metric', () => {
  const fd = compileIntent({ ...base, vizType: VizType.Pie, measures: [] });
  expect(fd.metric).toBeNull();
});

test('row limit is only emitted when set', () => {
  expect(compileIntent(base).row_limit).toBeUndefined();
  expect(compileIntent({ ...base, rowLimit: 100 }).row_limit).toBe(100);
});

test('unknown viz type compiles to just viz_type', () => {
  expect(compileIntent({ ...base, vizType: 'deck_scatter' })).toEqual({
    viz_type: 'deck_scatter',
  });
});

test('buildAdhocFilter sets operator, operatorId and clause for equals', () => {
  const f = buildAdhocFilter({
    column: 'country',
    operatorId: Operators.Equals,
    value: 'US',
  });
  expect(f).toEqual({
    expressionType: 'SIMPLE',
    subject: 'country',
    operator: '==',
    operatorId: Operators.Equals,
    clause: 'WHERE',
    comparator: 'US',
  });
});

test('buildAdhocFilter splits IN values into a comparator array', () => {
  const f = buildAdhocFilter({
    column: 'country',
    operatorId: Operators.In,
    value: 'US, CA ,MX',
  });
  expect(f.operator).toBe('IN');
  expect(f.comparator).toEqual(['US', 'CA', 'MX']);
});

test('buildAdhocFilter omits comparator for value-less operators', () => {
  const f = buildAdhocFilter({
    column: 'country',
    operatorId: Operators.IsNull,
  });
  expect(f.operator).toBe('IS NULL');
  expect('comparator' in f).toBe(false);
});
