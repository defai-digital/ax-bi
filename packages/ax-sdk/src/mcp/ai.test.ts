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

import { jest } from '@jest/globals';

import { AxBIError } from '../shared/errors.js';
import { AIResource } from './ai.js';
import type { MCPClient, MCPToolResult } from './mcpClient.js';

describe('AIResource', () => {
  test('extracts structured content after ensuring MCP initialization', async () => {
    const callTool = jest.fn(async (): Promise<MCPToolResult> => ({
      content: [],
      structuredContent: { assets: [], warnings: [] },
    }));
    const ensureInitialized = jest.fn(async () => {});
    const ai = new AIResource(
      { callTool } as unknown as MCPClient,
      ensureInitialized,
    );

    await expect(ai.searchAssets({ query: 'sales' })).resolves.toEqual({
      assets: [],
      warnings: [],
    });
    expect(ensureInitialized).toHaveBeenCalledTimes(1);
    expect(callTool).toHaveBeenCalledWith('search_business_assets', {
      query: 'sales',
      asset_types: ['dashboard', 'chart', 'dataset'],
      include_certified_only: false,
      limit: 20,
    });
  });

  test('throws AxBIError when a tool returns no content', async () => {
    const callTool = jest.fn(async (): Promise<MCPToolResult> => ({
      content: [],
    }));
    const ai = new AIResource({ callTool } as unknown as MCPClient);

    await expect(ai.searchAssets({ query: 'sales' })).rejects.toThrow(
      AxBIError,
    );
  });
});
