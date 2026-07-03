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
import { warningSchema } from './listColumn';

export const ASSET_SEARCH_CONTRACT_VERSION = 'asset-search.v1';

export type AssetType = 'chart' | 'dashboard' | 'dataset' | 'metric';

export interface AssetSearchRequest {
  contractVersion: typeof ASSET_SEARCH_CONTRACT_VERSION;
  query: string;
  assetTypes: AssetType[];
  includeCertifiedOnly: boolean;
  limit: number;
}

export interface AssetSearchResult {
  assetType: AssetType;
  id: number;
  uuid: string;
  name: string;
  description?: string;
  certified: boolean;
  relevanceScore: number;
  relevanceReason?: string;
  owners: string[];
  tags: string[];
}

export interface AssetSearchResponse {
  contractVersion: typeof ASSET_SEARCH_CONTRACT_VERSION;
  assets: AssetSearchResult[];
  warnings: string[];
}

const cleanAssetStringSchema = {
  type: 'string',
  maxLength: 256,
  pattern: '^[^\\u0000-\\u001F\\u007F]*$',
} as const;

const cleanAssetDescriptionSchema = {
  type: 'string',
  maxLength: 1024,
  pattern: '^[^\\u0000-\\u001F\\u007F]*$',
} as const;

const cleanAssetListStringSchema = {
  type: 'string',
  minLength: 1,
  maxLength: 128,
  pattern: '^[^\\u0000-\\u001F\\u007F]+$',
} as const;

const assetSearchResultSchema = {
  type: 'object',
  required: [
    'assetType',
    'id',
    'uuid',
    'name',
    'certified',
    'relevanceScore',
    'owners',
    'tags',
  ],
  additionalProperties: false,
  properties: {
    assetType: { enum: ['chart', 'dashboard', 'dataset', 'metric'] },
    id: { type: 'integer', minimum: 0 },
    uuid: cleanAssetStringSchema,
    name: cleanAssetStringSchema,
    description: cleanAssetDescriptionSchema,
    certified: { type: 'boolean' },
    relevanceScore: { type: 'number', minimum: 0, maximum: 2 },
    relevanceReason: cleanAssetStringSchema,
    owners: {
      type: 'array',
      items: cleanAssetListStringSchema,
    },
    tags: {
      type: 'array',
      items: cleanAssetListStringSchema,
    },
  },
} as const;

export const assetSearchRequestSchema = {
  $id: 'ax-services.asset-search.v1.request',
  type: 'object',
  required: [
    'contractVersion',
    'query',
    'assetTypes',
    'includeCertifiedOnly',
    'limit',
  ],
  additionalProperties: false,
  properties: {
    contractVersion: { const: ASSET_SEARCH_CONTRACT_VERSION },
    query: {
      type: 'string',
      maxLength: 256,
      pattern: '^(?=.*\\S)[^\\u0000-\\u001F\\u007F]+$',
    },
    assetTypes: {
      type: 'array',
      items: { enum: ['chart', 'dashboard', 'dataset', 'metric'] },
    },
    includeCertifiedOnly: { type: 'boolean' },
    limit: { type: 'integer', minimum: 1, maximum: 100 },
  },
} as const;

export const assetSearchResponseSchema = {
  $id: 'ax-services.asset-search.v1.response',
  type: 'object',
  required: ['contractVersion', 'assets', 'warnings'],
  additionalProperties: false,
  properties: {
    contractVersion: { const: ASSET_SEARCH_CONTRACT_VERSION },
    assets: {
      type: 'array',
      maxItems: 100,
      items: assetSearchResultSchema,
    },
    warnings: warningSchema,
  },
} as const;

export const assetSearchContractSchemas = {
  assetSearchRequestSchema,
  assetSearchResponseSchema,
} as const;
