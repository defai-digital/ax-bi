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

export const listColumnSchema = {
  type: 'array',
  items: { type: 'string', pattern: '^[A-Za-z0-9_]+$' },
} as const;

export const listOrderColumnSchema = {
  anyOf: [
    { const: '' },
    { type: 'string', pattern: '^[A-Za-z0-9_]+$' },
  ],
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
