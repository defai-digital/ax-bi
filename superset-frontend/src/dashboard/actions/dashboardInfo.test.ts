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
import { makeApi } from '@superset-ui/core';
import {
  ChartConfiguration,
  DashboardInfo,
  FilterBarOrientation,
  RootState,
} from 'src/dashboard/types';
import { ON_SAVE } from './dashboardState';
import {
  DASHBOARD_INFO_UPDATED,
  SAVE_CHART_CONFIG_COMPLETE,
  SET_CROSS_FILTERS_ENABLED,
  SET_FILTER_BAR_ORIENTATION,
  saveChartConfiguration,
  saveCrossFiltersSetting,
  saveFilterBarOrientation,
} from './dashboardInfo';

jest.mock('@superset-ui/core', () => ({
  ...jest.requireActual('@superset-ui/core'),
  makeApi: jest.fn(),
}));

const updateDashboard = jest.fn();
const mockMakeApi = makeApi as jest.Mock;

const baseMetadata = {
  native_filter_configuration: [],
  chart_configuration: {},
  global_chart_configuration: {
    scope: { rootPath: ['ROOT_ID'], excluded: [] },
    chartsInScope: [],
  },
  color_scheme: 'supersetColors',
  color_namespace: '',
  color_scheme_domain: [],
  label_colors: {},
  shared_label_colors: [],
  map_label_colors: {},
  cross_filters_enabled: false,
} as DashboardInfo['metadata'];

const getState = () =>
  ({
    dashboardInfo: {
      id: 1,
      metadata: baseMetadata,
      crossFiltersEnabled: false,
    },
  }) as RootState;

beforeEach(() => {
  updateDashboard.mockReset();
  mockMakeApi.mockReturnValue(updateDashboard);
});

test('saveChartConfiguration falls back to saved metadata when response metadata is malformed', async () => {
  const dispatch = jest.fn();
  const chartConfiguration: ChartConfiguration = {
    42: {
      id: 42,
      crossFilters: {
        scope: 'global',
        chartsInScope: [101],
      },
    },
  };
  const expectedMetadata = {
    ...baseMetadata,
    chart_configuration: chartConfiguration,
  };
  updateDashboard.mockResolvedValue({
    result: { json_metadata: '{malformed' },
    last_modified_time: 123,
  });

  await saveChartConfiguration({ chartConfiguration })(dispatch, getState);

  expect(dispatch).toHaveBeenCalledWith({
    type: DASHBOARD_INFO_UPDATED,
    newInfo: { metadata: expectedMetadata },
  });
  expect(dispatch).toHaveBeenCalledWith({
    type: SAVE_CHART_CONFIG_COMPLETE,
    chartConfiguration,
    globalChartConfiguration: undefined,
  });
});

test('saveFilterBarOrientation applies successful save when response metadata is malformed', async () => {
  const dispatch = jest.fn();
  updateDashboard.mockResolvedValue({
    result: { json_metadata: '{malformed' },
    last_modified_time: 123,
  });

  await saveFilterBarOrientation(FilterBarOrientation.Horizontal)(
    dispatch,
    getState,
  );

  expect(dispatch).toHaveBeenCalledWith({
    type: SET_FILTER_BAR_ORIENTATION,
    filterBarOrientation: FilterBarOrientation.Horizontal,
  });
  expect(dispatch).toHaveBeenCalledWith({
    type: ON_SAVE,
    lastModifiedTime: 123,
  });
});

test('saveCrossFiltersSetting keeps successful save when response metadata is malformed', async () => {
  const dispatch = jest.fn();
  updateDashboard.mockResolvedValue({
    result: { json_metadata: '{malformed' },
    last_modified_time: 123,
  });

  await saveCrossFiltersSetting(true)(dispatch, getState);

  expect(dispatch).toHaveBeenCalledWith({
    type: SET_CROSS_FILTERS_ENABLED,
    crossFiltersEnabled: true,
  });
  expect(dispatch).toHaveBeenCalledWith({
    type: DASHBOARD_INFO_UPDATED,
    newInfo: {
      metadata: {
        ...baseMetadata,
        cross_filters_enabled: true,
      },
    },
  });
});
