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
import { render, screen, waitFor } from 'spec/helpers/testing-library';
import fetchMock from 'fetch-mock';
import { isUserAdmin } from 'src/dashboard/util/permissionUtils';
import GenaiLlmSettings from '.';

jest.mock('src/dashboard/util/permissionUtils', () => ({
  isUserAdmin: jest.fn(() => true),
}));

jest.mock('src/utils/getBootstrapData', () => ({
  __esModule: true,
  default: () => ({
    common: {
      theme: {},
      conf: {},
      feature_flags: {},
    },
    user: {
      userId: 1,
      firstName: 'Admin',
      lastName: 'User',
      roles: { Admin: [] },
    },
  }),
}));

const mockSettings = {
  enabled: true,
  provider: 'openai_compatible',
  base_url: 'http://10.0.0.5:11434/v1',
  model: 'llama3.1',
  api_key_set: false,
  timeout_seconds: 60,
  verify_tls: true,
  allow_http: true,
  allow_private_network: true,
  configured: true,
};

beforeEach(() => {
  fetchMock.clearHistory().removeRoutes();
  (isUserAdmin as jest.Mock).mockReturnValue(true);
  fetchMock.get('glob:*/api/v1/admin/genai/llm/provider/', {
    result: mockSettings,
  });
});

afterEach(() => {
  fetchMock.clearHistory().removeRoutes();
});

test('loads and shows admin LLM provider form', async () => {
  render(<GenaiLlmSettings />, { useRedux: true, useRouter: true });

  await waitFor(() => {
    expect(screen.getByText(/Optional server-side LLM/i)).toBeInTheDocument();
  });
  expect(screen.getByRole('button', { name: /Save/i })).toBeInTheDocument();
  expect(
    screen.getByRole('button', { name: /Test connection/i }),
  ).toBeInTheDocument();
});

test('non-admin sees warning only', async () => {
  (isUserAdmin as jest.Mock).mockReturnValue(false);

  render(<GenaiLlmSettings />, { useRedux: true, useRouter: true });

  expect(await screen.findByText(/Administrators only/i)).toBeInTheDocument();
  expect(
    screen.queryByRole('button', { name: /Save/i }),
  ).not.toBeInTheDocument();
});
