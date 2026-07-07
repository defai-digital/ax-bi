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

/** HTTP methods supported by the transport. */
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

/** Response body parser to use for successful responses. */
export type ResponseType = 'json' | 'text' | 'blob' | 'arrayBuffer';

/** Options for a single HTTP request. */
export interface RequestOptions {
  method?: HttpMethod;
  path: string;
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined>;
  headers?: Record<string, string>;
  /** Parser to use for successful responses. Defaults to JSON/text auto-detect. */
  responseType?: ResponseType;
  /** Override the default timeout for this call (ms). */
  timeout?: number;
}

/** Raw response wrapper before JSON parsing. */
export interface RawResponse {
  status: number;
  headers: Headers;
  body: unknown;
}
