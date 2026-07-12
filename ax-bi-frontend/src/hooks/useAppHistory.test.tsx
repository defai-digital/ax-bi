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
import { renderHook, act } from '@testing-library/react';
import { unstable_HistoryRouter as HistoryRouter } from 'react-router-dom';
import { createMemoryHistory } from 'history';
import { useAppHistory } from './useAppHistory';

/**
 * useAppHistory is the shipped entry point for object-form navigation used by
 * View Query → SQL Lab (requestedQuery state). These tests drive that API
 * through HistoryRouter + a real history v5 instance.
 */
test('object-form push preserves embedded state (View Query → SQL Lab payload)', () => {
  const history = createMemoryHistory({ initialEntries: ['/explore'] });
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <HistoryRouter history={history}>{children}</HistoryRouter>
  );

  const { result } = renderHook(() => useAppHistory(), { wrapper });

  const requestedQuery = {
    datasourceKey: '1__table',
    sql: 'SELECT 1 AS n',
  };

  act(() => {
    // Same shape as ViewQuery / ViewQueryModalFooter
    result.current.push({
      pathname: '/sqllab',
      state: { requestedQuery },
    });
  });

  expect(history.location.pathname).toBe('/sqllab');
  expect(history.location.state).toEqual({ requestedQuery });
});

test('object-form push with explicit second-arg state prefers the second arg', () => {
  const history = createMemoryHistory({ initialEntries: ['/'] });
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <HistoryRouter history={history}>{children}</HistoryRouter>
  );

  const { result } = renderHook(() => useAppHistory(), { wrapper });

  act(() => {
    result.current.push(
      { pathname: '/sqllab', state: { fromObject: true } },
      { fromSecond: true },
    );
  });

  expect(history.location.pathname).toBe('/sqllab');
  expect(history.location.state).toEqual({ fromSecond: true });
});

test('object-form replace preserves embedded state', () => {
  const history = createMemoryHistory({ initialEntries: ['/dashboard/1'] });
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <HistoryRouter history={history}>{children}</HistoryRouter>
  );

  const { result } = renderHook(() => useAppHistory(), { wrapper });

  act(() => {
    result.current.replace({
      pathname: '/dashboard/1',
      search: '?native_filters_key=abc',
      state: { filterState: { region: 'west' } },
    });
  });

  expect(history.location.search).toBe('?native_filters_key=abc');
  expect(history.location.state).toEqual({ filterState: { region: 'west' } });
});

test('string-form push still accepts state as the second argument', () => {
  const history = createMemoryHistory({ initialEntries: ['/'] });
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <HistoryRouter history={history}>{children}</HistoryRouter>
  );

  const { result } = renderHook(() => useAppHistory(), { wrapper });

  act(() => {
    result.current.push('/sqllab', { requestedQuery: { sql: 'SELECT 2' } });
  });

  expect(history.location.pathname).toBe('/sqllab');
  expect(history.location.state).toEqual({
    requestedQuery: { sql: 'SELECT 2' },
  });
});
