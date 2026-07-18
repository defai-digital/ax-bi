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

export type LlmProviderType = 'anthropic' | 'openai' | 'openai_compatible';

export interface LlmProviderSettings {
  enabled: boolean;
  provider: LlmProviderType | null;
  base_url: string | null;
  model: string | null;
  api_key_set: boolean;
  timeout_seconds: number;
  verify_tls: boolean;
  allow_http: boolean;
  allow_private_network: boolean;
  configured: boolean;
}

export interface LlmProviderUpdatePayload {
  enabled: boolean;
  provider: LlmProviderType;
  base_url?: string | null;
  model: string;
  api_key?: string | null;
  timeout_seconds?: number;
  verify_tls?: boolean;
  allow_http?: boolean;
  allow_private_network?: boolean;
}

export interface LlmProviderTestResult {
  ok: boolean;
  provider?: string;
  model?: string;
}

export interface GenaiCapabilities {
  llm_configured: boolean;
  llm_provider_type: string | null;
  llm_model: string | null;
  bounded_samples_allowed?: boolean;
  genai_features?: Record<string, boolean>;
  source?: string;
}
