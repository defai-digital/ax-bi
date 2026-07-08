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
import { render, screen, userEvent } from 'spec/helpers/testing-library';
import { usePWAInstall, UsePWAInstallReturn } from 'src/hooks/usePWAInstall';
import { PWAInstallPrompt } from '.';

jest.mock('src/hooks/usePWAInstall', () => ({
  usePWAInstall: jest.fn(),
}));

const mockUsePWAInstall = usePWAInstall as jest.MockedFunction<
  typeof usePWAInstall
>;

const promptInstall = jest.fn<Promise<boolean>, []>();
const dismissInstall = jest.fn();

const installState = (
  overrides: Partial<UsePWAInstallReturn> = {},
): UsePWAInstallReturn => ({
  canInstall: true,
  isInstalled: false,
  isDismissed: false,
  promptInstall,
  dismissInstall,
  platform: 'mac',
  ...overrides,
});

beforeEach(() => {
  promptInstall.mockResolvedValue(true);
  dismissInstall.mockClear();
  mockUsePWAInstall.mockReturnValue(installState());
});

test('renders a platform-aware install prompt', () => {
  render(<PWAInstallPrompt />, { useTheme: true });

  expect(screen.getByRole('status')).toHaveTextContent('Install AX BI on Mac');
  expect(
    screen.getByText(
      'Get quick access from your desktop with the installable app',
    ),
  ).toBeInTheDocument();
});

test('invokes install and dismiss actions', async () => {
  render(<PWAInstallPrompt />, { useTheme: true });

  await userEvent.click(screen.getByRole('button', { name: 'Install' }));
  await userEvent.click(screen.getByRole('button', { name: 'Dismiss' }));

  expect(promptInstall).toHaveBeenCalledTimes(1);
  expect(dismissInstall).toHaveBeenCalledTimes(1);
});

test('does not render when installation is unavailable', () => {
  mockUsePWAInstall.mockReturnValue(installState({ canInstall: false }));

  render(<PWAInstallPrompt />, { useTheme: true });

  expect(screen.queryByRole('status')).not.toBeInTheDocument();
});
