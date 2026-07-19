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
import { AxBIClient } from '@ax-bi/ui-core';
import {
  render,
  screen,
  userEvent,
  waitFor,
} from 'spec/helpers/testing-library';
import { formatMcpApiKeyHint, McpApiKey } from './McpApiKey';

const oldKey = {
  uuid: 'old-key',
  name: 'AX BI MCP',
  key_prefix: 'sst_1oldZ',
  active: true,
  created_on: '2026-07-18T10:00:00Z',
  expires_on: null,
  revoked_on: null,
};

const newKey = {
  uuid: 'new-key',
  name: 'AX BI MCP',
  key: 'sst_M8hayd7-secret-value-iay8hfdsG',
  key_prefix: 'M8hayhfdsG',
  active: true,
  created_on: '2026-07-18T11:00:00Z',
  expires_on: null,
  revoked_on: null,
};

beforeEach(() => {
  jest.restoreAllMocks();
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText: jest.fn().mockResolvedValue(undefined) },
  });
});

test('formats the MCP key as a partial masked hint', () => {
  expect(formatMcpApiKeyHint('M8hayhfdsG')).toBe('M8hay********hfdsG');
  // Hyphens are only kept when they appear in the source characters.
  expect(formatMcpApiKeyHint('M8-ayhfd-G')).toBe('M8-ay********hfd-G');
});

test('shows a concise placeholder while preparing the MCP key', () => {
  jest
    .spyOn(AxBIClient, 'get')
    .mockImplementation(() => new Promise(() => undefined) as never);

  render(<McpApiKey username="akira" />, { useRedux: true, useTheme: true });

  expect(screen.queryByText(/Preparing MCP key/i)).not.toBeInTheDocument();
  expect(screen.getByText('MCP key…')).toBeInTheDocument();
  expect(
    screen.getByRole('button', {
      name: /Generate and copy a new MCP key/i,
    }),
  ).toBeEnabled();
});

test('creates the managed MCP key automatically when none exists', async () => {
  jest.spyOn(AxBIClient, 'get').mockResolvedValue({
    json: { result: [] },
  } as never);
  const post = jest.spyOn(AxBIClient, 'post').mockResolvedValue({
    json: { result: newKey },
  } as never);

  render(<McpApiKey username="akira" />, { useRedux: true, useTheme: true });

  expect(await screen.findByText('akira')).toBeInTheDocument();
  expect(await screen.findByText('M8hay********hfdsG')).toBeInTheDocument();
  expect(screen.queryByText(newKey.key)).not.toBeInTheDocument();
  expect(post).toHaveBeenCalledWith({
    endpoint: '/api/v1/security/api_keys/',
    jsonPayload: { name: 'AX BI MCP' },
  });
});

test('eye action generates a key after initialization could not load one', async () => {
  jest
    .spyOn(AxBIClient, 'get')
    .mockRejectedValueOnce(new Error('Forbidden'))
    .mockResolvedValue({ json: { result: [] } } as never);
  const post = jest.spyOn(AxBIClient, 'post').mockResolvedValue({
    json: { result: newKey },
  } as never);

  render(<McpApiKey username="akira" />, { useRedux: true, useTheme: true });

  await userEvent.click(
    screen.getByRole('button', {
      name: /Generate and copy a new MCP key/i,
    }),
  );

  await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
  expect(navigator.clipboard.writeText).toHaveBeenCalledWith(newKey.key);
  expect(await screen.findByText('M8hay********hfdsG')).toBeInTheDocument();
});

test('eye action generates, copies, and revokes the previous MCP key', async () => {
  jest.spyOn(AxBIClient, 'get').mockResolvedValue({
    json: { result: [oldKey] },
  } as never);
  const post = jest.spyOn(AxBIClient, 'post').mockResolvedValue({
    json: { result: newKey },
  } as never);
  const remove = jest
    .spyOn(AxBIClient, 'delete')
    .mockResolvedValue({} as never);

  render(<McpApiKey username="akira" />, { useRedux: true, useTheme: true });

  const rotate = await screen.findByRole('button', {
    name: /Generate and copy a new MCP key/i,
  });
  await userEvent.click(rotate);

  await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
  expect(navigator.clipboard.writeText).toHaveBeenCalledWith(newKey.key);
  expect(remove).toHaveBeenCalledWith({
    endpoint: '/api/v1/security/api_keys/old-key',
  });
  expect(await screen.findByText('M8hay********hfdsG')).toBeInTheDocument();
  expect(screen.queryByText(newKey.key)).not.toBeInTheDocument();
});
