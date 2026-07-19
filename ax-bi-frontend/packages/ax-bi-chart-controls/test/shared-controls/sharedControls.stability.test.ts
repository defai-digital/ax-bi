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
import sharedControls from '../../src/shared-controls/sharedControls';
import {
  dndGroupByControl,
  dndColumnsControl,
} from '../../src/shared-controls/dndControls';
import { xAxisSortControl } from '../../src/shared-controls/customControls';

test('sharedControls registers ColumnMeta-specialized groupby without dropping type', () => {
  expect(sharedControls.groupby).toBe(dndGroupByControl);
  expect(sharedControls.columns).toBe(dndColumnsControl);
  expect(sharedControls.groupby.type).toBe('DndColumnSelect');
  expect(typeof sharedControls.groupby.optionRenderer).toBe('function');
});

test('xAxisSortControl mapStateToProps dedupes metric labels via Set without throw', () => {
  const mapStateToProps = xAxisSortControl.config.mapStateToProps;
  expect(mapStateToProps).toBeDefined();
  const state = mapStateToProps!(
    {
      controls: {
        groupby: { value: [] },
        metrics: {
          value: ['count(*)', 'count(*)', 'sum(sales)'],
        },
        timeseries_limit_metric: { value: 'count(*)' },
        x_axis: { value: 'country' },
      },
      datasource: {
        type: 'table',
        columns: [{ column_name: 'country' }],
        verbose_map: {},
      },
    } as any,
    { value: null, type: 'XAxisSortControl' } as any,
  );
  const values = (state.options as { value: string }[] | undefined)?.map(
    c => c.value,
  );
  // Single-sort path exposes unique metric labels from metrics + limit metric
  expect(values).toEqual(
    expect.arrayContaining(['count(*)', 'sum(sales)', 'country']),
  );
  expect(values?.filter(v => v === 'count(*)')).toHaveLength(1);
});
