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
import { FC, useEffect } from 'react';
import {
  fireEvent,
  render,
  screen,
  userEvent,
} from 'spec/helpers/testing-library';
import {
  Command,
  CommandPalette,
  CommandPaletteProvider,
  useCommandPalette,
} from '.';

const dashboardAction = jest.fn();
const datasetAction = jest.fn();

const commands: Command[] = [
  {
    id: 'nav-dashboard',
    name: 'Dashboards',
    description: 'Browse dashboards',
    type: 'navigation',
    action: dashboardAction,
    keywords: ['charts'],
  },
  {
    id: 'action-dataset',
    name: 'New dataset',
    description: 'Connect a new dataset',
    type: 'action',
    action: datasetAction,
    shortcut: 'D',
  },
];

const PaletteHarness: FC = () => {
  const { open, registerCommand } = useCommandPalette();

  useEffect(() => {
    const cleanups = commands.map(command => registerCommand(command));
    return () => {
      cleanups.forEach(cleanup => cleanup());
    };
  }, [registerCommand]);

  return (
    <>
      <button type="button" onClick={open}>
        Open palette
      </button>
      <CommandPalette />
    </>
  );
};

const renderPalette = () =>
  render(
    <CommandPaletteProvider>
      <PaletteHarness />
    </CommandPaletteProvider>,
    { useTheme: true },
  );

beforeAll(() => {
  window.HTMLElement.prototype.scrollIntoView = jest.fn();
});

beforeEach(() => {
  dashboardAction.mockClear();
  datasetAction.mockClear();
});

test('filters commands and executes the selected command', async () => {
  renderPalette();

  await userEvent.click(screen.getByRole('button', { name: 'Open palette' }));
  const search = await screen.findByRole('combobox', {
    name: 'Search commands',
  });

  expect(screen.getByText('Dashboards')).toBeInTheDocument();
  await userEvent.type(search, 'dataset');

  expect(screen.queryByText('Dashboards')).not.toBeInTheDocument();
  expect(screen.getByText('New dataset')).toBeInTheDocument();

  fireEvent.keyDown(search, { key: 'Enter' });

  expect(datasetAction).toHaveBeenCalledTimes(1);
  expect(dashboardAction).not.toHaveBeenCalled();
});

test('supports keyboard navigation between command rows', async () => {
  renderPalette();

  await userEvent.click(screen.getByRole('button', { name: 'Open palette' }));
  const search = await screen.findByRole('combobox', {
    name: 'Search commands',
  });

  fireEvent.keyDown(search, { key: 'ArrowDown' });
  fireEvent.keyDown(search, { key: 'Enter' });

  expect(datasetAction).toHaveBeenCalledTimes(1);
  expect(dashboardAction).not.toHaveBeenCalled();
});
