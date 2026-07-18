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
import { useEffect } from 'react';
import { AxBIClient, FeatureFlag } from '@ax-bi/ui-core';
import {
  render,
  screen,
  sleep,
  userEvent,
  waitFor,
} from 'spec/helpers/testing-library';
import {
  Command,
  CommandPaletteProvider,
  useCommandPalette,
} from 'src/components/CommandPalette';
import { ensureAppRoot } from 'src/utils/pathUtils';
import { useAssetSearchCommands } from './useAssetSearchCommands';

const mockPush = jest.fn();

jest.mock('src/hooks/useAppHistory', () => ({
  useHistory: () => ({ push: mockPush }),
  useAppHistory: () => ({ push: mockPush }),
}));

const ENDPOINT_ROWS: Record<string, unknown[]> = {
  '/api/v1/dashboard/': [
    { id: 1, dashboard_title: 'Sales dashboard', url: '/ax-bi/dashboard/1/' },
  ],
  '/api/v1/chart/': [{ id: 2, slice_name: 'Sales chart' }],
  '/api/v1/dataset/': [{ id: 3, table_name: 'sales_table' }],
  '/api/v1/database/': [{ id: 4, database_name: 'sales_db' }],
  '/api/v1/saved_query/': [{ id: 5, label: 'sales query' }],
};

const getSpy = jest.spyOn(AxBIClient, 'get');

interface ProbeProps {
  onCommands: (commands: Command[]) => void;
}

const Probe = ({ onCommands }: ProbeProps) => {
  useAssetSearchCommands();
  const { getCommands, open, setQuery } = useCommandPalette();

  useEffect(() => {
    open();
  }, [open]);

  useEffect(() => {
    onCommands(getCommands());
  }, [getCommands, onCommands]);

  return (
    <>
      <button type="button" onClick={() => setQuery('sales')}>
        Search sales
      </button>
      <button type="button" onClick={() => setQuery('s')}>
        Search s
      </button>
    </>
  );
};

const renderProbe = () => {
  const onCommands = jest.fn();
  render(
    <CommandPaletteProvider>
      <Probe onCommands={onCommands} />
    </CommandPaletteProvider>,
  );
  return onCommands;
};

const latestAssetCommands = (onCommands: jest.Mock): Command[] => {
  const calls = onCommands.mock.calls as [Command[]][];
  const latest = calls.at(-1)?.[0] ?? [];
  return latest.filter(cmd => cmd.id.startsWith('asset-search-'));
};

const calledEndpoints = () =>
  getSpy.mock.calls.map(([config]) => String(config.endpoint));

beforeEach(() => {
  window.featureFlags = { [FeatureFlag.GlobalSearchV2]: true };
  mockPush.mockClear();
  getSpy.mockReset();
  getSpy.mockImplementation(async ({ endpoint }) => {
    const path = Object.keys(ENDPOINT_ROWS).find(prefix =>
      String(endpoint).startsWith(prefix),
    );
    return {
      json: { result: path ? ENDPOINT_ROWS[path] : [] },
      response: new Response(),
    };
  });
});

afterAll(() => {
  getSpy.mockRestore();
});

test('registers asset commands for all five types when GLOBAL_SEARCH_V2 is on', async () => {
  const onCommands = renderProbe();

  await userEvent.click(screen.getByRole('button', { name: 'Search sales' }));

  await waitFor(() => {
    expect(latestAssetCommands(onCommands)).toHaveLength(5);
  });

  const ids = latestAssetCommands(onCommands).map(cmd => cmd.id);
  expect(ids).toEqual(
    expect.arrayContaining([
      'asset-search-dashboard-1',
      'asset-search-chart-2',
      'asset-search-dataset-3',
      'asset-search-database-4',
      'asset-search-saved-query-5',
    ]),
  );
  [
    '/api/v1/dashboard/',
    '/api/v1/chart/',
    '/api/v1/dataset/',
    '/api/v1/database/',
    '/api/v1/saved_query/',
  ].forEach(prefix => {
    expect(
      calledEndpoints().some(endpoint => endpoint.startsWith(prefix)),
    ).toBe(true);
  });
});

test('asset commands navigate to per-type targets', async () => {
  const onCommands = renderProbe();

  await userEvent.click(screen.getByRole('button', { name: 'Search sales' }));

  await waitFor(() => {
    expect(latestAssetCommands(onCommands)).toHaveLength(5);
  });

  const byId = (id: string) =>
    latestAssetCommands(onCommands).find(cmd => cmd.id === id)!;
  const appRoot = ensureAppRoot('');

  byId('asset-search-dashboard-1').action();
  expect(mockPush).toHaveBeenLastCalledWith('/ax-bi/dashboard/1/');

  byId('asset-search-chart-2').action();
  expect(mockPush).toHaveBeenLastCalledWith(`${appRoot}/explore/?slice_id=2`);

  byId('asset-search-dataset-3').action();
  expect(mockPush).toHaveBeenLastCalledWith(`${appRoot}/dataset/3`);

  byId('asset-search-database-4').action();
  expect(mockPush).toHaveBeenLastCalledWith(`${appRoot}/databases`);

  byId('asset-search-saved-query-5').action();
  expect(mockPush).toHaveBeenLastCalledWith(`${appRoot}/sqllab?savedQueryId=5`);
});

test('searches only dashboards and charts when GLOBAL_SEARCH_V2 is off', async () => {
  window.featureFlags = { [FeatureFlag.GlobalSearchV2]: false };
  const onCommands = renderProbe();

  await userEvent.click(screen.getByRole('button', { name: 'Search sales' }));

  await waitFor(() => {
    expect(latestAssetCommands(onCommands)).toHaveLength(2);
  });

  const ids = latestAssetCommands(onCommands).map(cmd => cmd.id);
  expect(ids).toEqual(
    expect.arrayContaining([
      'asset-search-dashboard-1',
      'asset-search-chart-2',
    ]),
  );

  const endpoints = calledEndpoints();
  expect(endpoints).toHaveLength(2);
  expect(endpoints.some(url => url.startsWith('/api/v1/dashboard/'))).toBe(
    true,
  );
  expect(endpoints.some(url => url.startsWith('/api/v1/chart/'))).toBe(true);
});

test('does not search for queries shorter than two characters', async () => {
  const onCommands = renderProbe();

  await userEvent.click(screen.getByRole('button', { name: 'Search s' }));

  // Wait beyond the debounce window before asserting nothing fired.
  await sleep(400);
  expect(getSpy).not.toHaveBeenCalled();
  expect(latestAssetCommands(onCommands)).toHaveLength(0);
});

test('keeps search results from failing endpoints out of the palette', async () => {
  getSpy.mockImplementation(async ({ endpoint }) => {
    if (String(endpoint).startsWith('/api/v1/chart/')) {
      throw new Error('Chart API down');
    }
    const path = Object.keys(ENDPOINT_ROWS).find(prefix =>
      String(endpoint).startsWith(prefix),
    );
    return {
      json: { result: path ? ENDPOINT_ROWS[path] : [] },
      response: new Response(),
    };
  });

  const onCommands = renderProbe();
  await userEvent.click(screen.getByRole('button', { name: 'Search sales' }));

  await waitFor(() => {
    expect(latestAssetCommands(onCommands)).toHaveLength(4);
  });

  const ids = latestAssetCommands(onCommands).map(cmd => cmd.id);
  expect(ids).not.toContain('asset-search-chart-2');
  expect(ids).toContain('asset-search-dashboard-1');
});
