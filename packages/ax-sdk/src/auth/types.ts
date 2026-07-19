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

/** Username/password authentication. */
export interface CredentialsAuth {
  type: 'credentials';
  username: string;
  password: string;
}

/** Pre-existing access token (and optional refresh token). */
export interface TokenAuth {
  type: 'token';
  accessToken: string;
  refreshToken?: string;
}

/** User-bound AX BI API key passed as a header. */
export interface ApiKeyAuth {
  type: 'apiKey';
  apiKey: string;
  /** Header name. Defaults to `Authorization` for REST and MCP. */
  headerName?: string;
  /** Prefix before the key value. Defaults to `Bearer `. */
  headerPrefix?: string;
}

/** Guest token for embedded dashboard access. */
export interface GuestTokenAuth {
  type: 'guestToken';
  guestToken: string;
}

/** Union of all supported authentication strategies. */
export type AuthConfig = CredentialsAuth | TokenAuth | ApiKeyAuth | GuestTokenAuth;
