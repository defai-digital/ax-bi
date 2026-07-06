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

export type ListFilterValue =
  | string
  | number
  | boolean
  | string[]
  | number[]
  | boolean[];

export interface ListFilter {
  col: string;
  opr: string;
  value: ListFilterValue;
}

export interface ListRequestBase<TContractVersion extends string> {
  contractVersion: TContractVersion;
  filters: ListFilter[];
  selectColumns: string[];
  search?: string;
  orderColumn?: string;
  orderDirection: 'asc' | 'desc';
  page: number;
  pageSize: number;
}

export interface ListResponseBase<TContractVersion extends string> {
  contractVersion: TContractVersion;
  count: number;
  totalCount: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
  columnsRequested: string[];
  columnsLoaded: string[];
  warnings: string[];
}

export const listIdentifierSchema = {
  type: 'string',
  pattern: '^[A-Za-z0-9_]+$',
} as const;

export const listColumnSchema = {
  type: 'array',
  items: listIdentifierSchema,
} as const;

export const listOrderColumnSchema = {
  anyOf: [{ const: '' }, listIdentifierSchema],
} as const;

export const listSearchSchema = {
  type: 'string',
  pattern: '^(?:$|(?=.*\\S)[^\\u0000-\\u001F\\u007F]+)$',
} as const;

export const listFilterStringSchema = {
  type: 'string',
  pattern: '^[^\\u0000-\\u001F\\u007F]*$',
} as const;

export const listFilterStringArraySchema = {
  type: 'array',
  items: listFilterStringSchema,
} as const;

export const listFilterSchema = {
  type: 'object',
  required: ['col', 'opr', 'value'],
  additionalProperties: false,
  properties: {
    col: listIdentifierSchema,
    opr: listIdentifierSchema,
    value: {
      anyOf: [
        listFilterStringSchema,
        { type: 'number' },
        { type: 'boolean' },
        listFilterStringArraySchema,
        { type: 'array', items: { type: 'number' } },
        { type: 'array', items: { type: 'boolean' } },
      ],
    },
  },
} as const;

export const listPageSchema = {
  type: 'integer',
  minimum: 1,
} as const;

export const listPageSizeSchema = {
  type: 'integer',
  minimum: 1,
  maximum: 100,
} as const;

export const listCountSchema = {
  type: 'integer',
  minimum: 0,
} as const;

export const listTotalPagesSchema = listCountSchema;

export const warningSchema = {
  type: 'array',
  maxItems: 10,
  items: {
    type: 'string',
    minLength: 1,
    maxLength: 512,
    pattern: '^[^\\u0000-\\u001F\\u007F]+$',
  },
} as const;

const baseListRequestFields = [
  'filters',
  'selectColumns',
  'orderDirection',
  'page',
  'pageSize',
] as const;

const baseListRequestProperties = {
  filters: {
    type: 'array',
    items: listFilterSchema,
  },
  selectColumns: listColumnSchema,
  search: listSearchSchema,
  orderColumn: listOrderColumnSchema,
  orderDirection: { enum: ['asc', 'desc'] },
  page: listPageSchema,
  pageSize: listPageSizeSchema,
} as const;

export function buildListRequestSchema<
  TContractVersion extends string,
  TLeadingProperties extends Record<string, unknown> = Record<never, never>,
  TExtraProperties extends Record<string, unknown> = Record<never, never>,
>({
  schemaId,
  contractVersion,
  leadingRequired = [],
  leadingProperties,
  extraRequired = [],
  extraProperties,
}: {
  schemaId: string;
  contractVersion: TContractVersion;
  leadingRequired?: readonly (keyof TLeadingProperties & string)[];
  leadingProperties?: TLeadingProperties;
  extraRequired?: readonly (keyof TExtraProperties & string)[];
  extraProperties?: TExtraProperties;
}) {
  const properties = {
    contractVersion: { const: contractVersion },
    ...leadingProperties,
    ...baseListRequestProperties,
    ...extraProperties,
  } as { contractVersion: { const: TContractVersion } } &
    TLeadingProperties &
    typeof baseListRequestProperties &
    TExtraProperties;

  return {
    $id: schemaId,
    type: 'object',
    required: [
      'contractVersion',
      ...leadingRequired,
      ...baseListRequestFields,
      ...extraRequired,
    ],
    additionalProperties: false,
    properties,
  } as const;
}

const listResponseMetricsRequired = [
  'count',
  'totalCount',
  'page',
  'pageSize',
  'totalPages',
  'hasNext',
  'hasPrevious',
] as const;

const listResponseColumnRequired = [
  'columnsRequested',
  'columnsLoaded',
  'warnings',
] as const;

const listResponseMetricProperties = {
  count: listCountSchema,
  totalCount: listCountSchema,
  page: listPageSchema,
  pageSize: listPageSizeSchema,
  totalPages: listTotalPagesSchema,
  hasNext: { type: 'boolean' },
  hasPrevious: { type: 'boolean' },
} as const;

const listResponseColumnProperties = {
  columnsRequested: listColumnSchema,
  columnsLoaded: listColumnSchema,
  warnings: warningSchema,
} as const;

export function buildListResponseSchema<
  TContractVersion extends string,
  TCollectionKey extends string,
  TItemSchema extends Record<string, unknown>,
  TMiddleProperties extends Record<string, unknown> = Record<never, never>,
>({
  schemaId,
  contractVersion,
  collectionKey,
  itemSchema,
  middleRequired = [],
  middleProperties,
}: {
  schemaId: string;
  contractVersion: TContractVersion;
  collectionKey: TCollectionKey;
  itemSchema: TItemSchema;
  middleRequired?: readonly (keyof TMiddleProperties & string)[];
  middleProperties?: TMiddleProperties;
}) {
  const collectionProperty = {
    type: 'array',
    items: itemSchema,
  } as const;
  const properties = {
    contractVersion: { const: contractVersion },
    [collectionKey]: collectionProperty,
    ...listResponseMetricProperties,
    ...middleProperties,
    ...listResponseColumnProperties,
  } as { contractVersion: { const: TContractVersion } } &
    Record<TCollectionKey, typeof collectionProperty> &
    typeof listResponseMetricProperties &
    TMiddleProperties &
    typeof listResponseColumnProperties;

  return {
    $id: schemaId,
    type: 'object',
    required: [
      'contractVersion',
      collectionKey,
      ...listResponseMetricsRequired,
      ...middleRequired,
      ...listResponseColumnRequired,
    ],
    additionalProperties: false,
    properties,
  } as const;
}
