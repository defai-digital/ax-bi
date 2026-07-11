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
      request: {
        query: 'sales',
        asset_types: ['dashboard', 'chart', 'dataset'],
        include_certified_only: false,
        limit: 20,
      },
    });
  });

  test('promptToDashboard calls the orchestrator tool with defaults', async () => {
    const callTool = jest.fn(async (): Promise<MCPToolResult> => ({
      content: [],
      structuredContent: {
        dashboard_url: 'http://localhost:8088/superset/dashboard/1/',
        charts: [],
        warnings: [],
      },
    }));
    const ai = new AIResource({ callTool } as unknown as MCPClient);

    await expect(
      ai.promptToDashboard({
        prompt: 'Create an executive sales dashboard',
      }),
    ).resolves.toMatchObject({
      dashboard_url: 'http://localhost:8088/superset/dashboard/1/',
    });
    expect(callTool).toHaveBeenCalledWith('prompt_to_dashboard', {
      request: {
        prompt: 'Create an executive sales dashboard',
        dataset_ids: [],
        max_charts: 6,
        draft: true,
        save_charts: true,
        dry_run: false,
      },
    });
  });

  test('createChartFromIntent forwards structured plan fields', async () => {
    const callTool = jest.fn(async (): Promise<MCPToolResult> => ({
      content: [],
      structuredContent: { success: true, chart_type_selected: 'xy' },
    }));
    const ai = new AIResource({ callTool } as unknown as MCPClient);

    await ai.createChartFromIntent({
      prompt: 'Revenue by region',
      dataset_id: 42,
      chart_type: 'xy',
      metrics: ['revenue'],
      dimensions: ['region'],
      kind: 'bar',
    });

    expect(callTool).toHaveBeenCalledWith('create_chart_from_intent', {
      request: {
        prompt: 'Revenue by region',
        dataset_id: 42,
        save_chart: true,
        max_preview_rows: 100,
        chart_type: 'xy',
        metrics: ['revenue'],
        dimensions: ['region'],
        filters: [],
        time_range: undefined,
        kind: 'bar',
      },
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

  test('throws AxBIError when a typed tool result is marked as error', async () => {
    const toolResult: MCPToolResult = {
      isError: true,
      content: [{ type: 'text', text: 'tool failed' }],
      structuredContent: { assets: [], warnings: [] },
    };
    const callTool = jest.fn(async (): Promise<MCPToolResult> => toolResult);
    const ai = new AIResource({ callTool } as unknown as MCPClient);

    await expect(ai.searchAssets({ query: 'sales' })).rejects.toMatchObject({
      message: 'MCP tool "search_business_assets" returned an error',
      responseBody: toolResult,
    });
  });

  test('throws AxBIError when a typed tool returns malformed JSON text', async () => {
    const callTool = jest.fn(async (): Promise<MCPToolResult> => ({
      content: [{ type: 'text', text: 'not-json' }],
    }));
    const ai = new AIResource({ callTool } as unknown as MCPClient);

    await expect(ai.searchAssets({ query: 'sales' })).rejects.toMatchObject({
      message: 'MCP tool "search_business_assets" returned malformed JSON',
      responseBody: 'not-json',
    });
  });

  test('throws AxBIError when a typed tool returns a non-object result', async () => {
    const callTool = jest.fn(async () => null);
    const ai = new AIResource({ callTool } as unknown as MCPClient);

    await expect(ai.searchAssets({ query: 'sales' })).rejects.toMatchObject({
      message: 'MCP tool "search_business_assets" returned malformed result',
      responseBody: null,
    });
  });

  test('throws AxBIError when structured content is not an object', async () => {
    const toolResult = {
      content: [],
      structuredContent: [],
    };
    const callTool = jest.fn(async () => toolResult);
    const ai = new AIResource({ callTool } as unknown as MCPClient);

    await expect(ai.searchAssets({ query: 'sales' })).rejects.toMatchObject({
      message:
        'MCP tool "search_business_assets" returned malformed structured content',
      responseBody: toolResult,
    });
  });

  test('throws AxBIError when fallback content is not an array', async () => {
    const toolResult = {
      content: 'not-an-array',
    };
    const callTool = jest.fn(async () => toolResult);
    const ai = new AIResource({ callTool } as unknown as MCPClient);

    await expect(ai.searchAssets({ query: 'sales' })).rejects.toMatchObject({
      message: 'MCP tool "search_business_assets" returned malformed content',
      responseBody: toolResult,
    });
  });

  test('returns raw MCP errors from raw tool calls', async () => {
    const toolResult: MCPToolResult = {
      isError: true,
      content: [{ type: 'text', text: 'tool failed' }],
    };
    const callTool = jest.fn(async (): Promise<MCPToolResult> => toolResult);
    const ai = new AIResource({ callTool } as unknown as MCPClient);

    await expect(ai.callTool('raw_tool')).resolves.toBe(toolResult);
  });
});
