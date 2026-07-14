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
  GenaiCapabilities,
  LlmProviderSettings,
  LlmProviderTestResult,
  LlmProviderUpdatePayload,
} from './types';

const PROVIDER_ENDPOINT = '/api/v1/admin/genai/llm/provider/';
const CAPABILITIES_ENDPOINT = '/api/v1/genai/capabilities/';

export async function fetchLlmProviderSettings(): Promise<LlmProviderSettings> {
  const { json } = await AxBIClient.get({ endpoint: PROVIDER_ENDPOINT });
  return json.result as LlmProviderSettings;
}

export async function saveLlmProviderSettings(
  payload: LlmProviderUpdatePayload,
): Promise<{ result: LlmProviderSettings; message?: string }> {
  const { json } = await AxBIClient.put({
    endpoint: PROVIDER_ENDPOINT,
    jsonPayload: payload,
  });
  return {
    result: json.result as LlmProviderSettings,
    message: json.message as string | undefined,
  };
}

export async function clearLlmProviderSettings(): Promise<LlmProviderSettings> {
  const { json } = await AxBIClient.delete({ endpoint: PROVIDER_ENDPOINT });
  return json.result as LlmProviderSettings;
}

export async function testLlmProvider(
  payload?: Partial<LlmProviderUpdatePayload>,
): Promise<LlmProviderTestResult> {
  const { json } = await AxBIClient.post({
    endpoint: `${PROVIDER_ENDPOINT}test/`,
    jsonPayload: payload ?? {},
  });
  return json.result as LlmProviderTestResult;
}

export async function fetchGenaiCapabilities(): Promise<GenaiCapabilities> {
  const { json } = await AxBIClient.get({ endpoint: CAPABILITIES_ENDPOINT });
  return json.result as GenaiCapabilities;
}
