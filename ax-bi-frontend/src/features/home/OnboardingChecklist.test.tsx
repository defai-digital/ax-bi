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

import { waitFor } from '@testing-library/react';
import { AxBIClient } from '@ax-bi/ui-core';
import { render, screen, userEvent } from 'spec/helpers/testing-library';
import { resetUxPreferencesCache } from 'src/hooks/useUxPreference';
import OnboardingChecklist from './OnboardingChecklist';

jest.mock('@ax-bi/ui-core', () => ({
  ...jest.requireActual('@ax-bi/ui-core'),
  AxBIClient: {
    get: jest.fn(),
    put: jest.fn(),
  },
}));

const mockGet = AxBIClient.get as jest.Mock;
const mockPut = AxBIClient.put as jest.Mock;

const defaultProps = {
  canUploadData: true,
  hasChart: false,
  hasDashboard: false,
};

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  resetUxPreferencesCache();
  mockGet.mockResolvedValue({ json: { result: {} } });
  mockPut.mockResolvedValue({ json: { result: {} } });
});

test('renders the checklist when not dismissed', () => {
  render(<OnboardingChecklist {...defaultProps} />);

  expect(screen.getByText('Get started')).toBeInTheDocument();
});

test('is hidden when the server preference says dismissed', async () => {
  mockGet.mockResolvedValue({
    json: { result: { 'ux.home.onboarding_dismissed': true } },
  });

  render(<OnboardingChecklist {...defaultProps} />);

  await waitFor(() =>
    expect(screen.queryByText('Get started')).not.toBeInTheDocument(),
  );
});

test('is hidden when legacy localStorage dismissal exists', () => {
  localStorage.setItem('home__onboarding_checklist_dismissed', '1');

  render(<OnboardingChecklist {...defaultProps} />);

  expect(screen.queryByText('Get started')).not.toBeInTheDocument();
});

test('dismiss hides the checklist and persists the preference', async () => {
  render(<OnboardingChecklist {...defaultProps} />);

  userEvent.click(screen.getByTestId('onboarding-dismiss'));

  expect(screen.queryByText('Get started')).not.toBeInTheDocument();
  expect(localStorage.getItem('home__onboarding_checklist_dismissed')).toBe(
    'true',
  );
  await waitFor(() =>
    expect(mockPut).toHaveBeenCalledWith({
      endpoint: '/api/v1/me/preferences/',
      body: JSON.stringify({ 'ux.home.onboarding_dismissed': true }),
      headers: { 'Content-Type': 'application/json' },
    }),
  );
});

test('is hidden when all core steps are done', () => {
  render(<OnboardingChecklist {...defaultProps} hasChart hasDashboard />);

  expect(screen.queryByText('Get started')).not.toBeInTheDocument();
});
