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
  DatasourceType,
  JsonResponse,
  SupersetClient,
} from '@superset-ui/core';
import {
  ADD_SLICES,
  FETCH_ALL_SLICES_STARTED,
  fetchSlices,
} from './sliceEntities';

test('fetchSlices keeps charts with malformed params using datasource fallback', async () => {
  const getStub = jest.spyOn(SupersetClient, 'get').mockResolvedValue({
    json: {
      result: [
        {
          id: 10,
          url: '/explore/?slice_id=10',
          slice_name: 'Malformed params chart',
          params: '{malformed',
          datasource_id: 7,
          datasource_type: DatasourceType.Table,
          datasource_name_text: 'birth_names',
          datasource_url: '/tablemodelview/list/?id=7',
          changed_on_utc: '2024-01-01T00:00:00',
          description: '',
          description_markeddown: '',
          viz_type: 'table',
          changed_on_delta_humanized: 'a day ago',
          thumbnail_url: '/thumbnail/10',
          owners: [],
          created_by: { id: 1 },
        },
      ],
    },
  } as unknown as JsonResponse);
  const dispatch = jest.fn();

  await fetchSlices()(dispatch);

  expect(dispatch).toHaveBeenNthCalledWith(1, {
    type: FETCH_ALL_SLICES_STARTED,
  });
  expect(dispatch).toHaveBeenNthCalledWith(
    2,
    expect.objectContaining({
      type: ADD_SLICES,
      payload: {
        slices: {
          10: expect.objectContaining({
            form_data: { datasource: '7__table' },
          }),
        },
      },
    }),
  );
  getStub.mockRestore();
});
