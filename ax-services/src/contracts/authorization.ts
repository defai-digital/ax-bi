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
export const AUTHORIZATION_CONTRACT_VERSION = 'authorization.v1';

export type PrincipalType = 'user' | 'guest' | 'service';
export type ResourceType =
  | 'chart'
  | 'dashboard'
  | 'database'
  | 'dataset'
  | 'query';
export type PermissionAction = 'create' | 'delete' | 'read' | 'write';

export interface AuthorizationPrincipal {
  type: PrincipalType;
  userId?: number;
  username?: string;
  roles?: string[];
}

export interface AuthorizationResource {
  type: ResourceType;
  id?: number;
  uuid?: string;
}

export interface PermissionCheckRequest {
  contractVersion: typeof AUTHORIZATION_CONTRACT_VERSION;
  principal: AuthorizationPrincipal;
  resource: AuthorizationResource;
  action: PermissionAction;
}

export interface PermissionCheckResponse {
  contractVersion: typeof AUTHORIZATION_CONTRACT_VERSION;
  allowed: boolean;
  reason?: string;
}

export interface PermissionCheckResult extends PermissionCheckResponse {
  statusCode?: number;
  error?: string;
}

const cleanAuthorizationStringSchema = {
  type: 'string',
  pattern: '^(?=.*\\S)[^\\u0000-\\u001F\\u007F]+$',
} as const;

const externalMessageSchema = {
  type: 'string',
  minLength: 1,
  maxLength: 256,
  pattern: '^[^\\u0000-\\u001F\\u007F]+$',
} as const;

export const permissionCheckRequestSchema = {
  $id: 'ax-services.permission-check.v1.request',
  type: 'object',
  required: ['contractVersion', 'principal', 'resource', 'action'],
  additionalProperties: false,
  properties: {
    contractVersion: { const: AUTHORIZATION_CONTRACT_VERSION },
    principal: {
      type: 'object',
      required: ['type'],
      additionalProperties: false,
      properties: {
        type: { enum: ['user', 'guest', 'service'] },
        userId: { type: 'integer', minimum: 0 },
        username: cleanAuthorizationStringSchema,
        roles: {
          type: 'array',
          items: cleanAuthorizationStringSchema,
        },
      },
    },
    resource: {
      type: 'object',
      required: ['type'],
      additionalProperties: false,
      properties: {
        type: { enum: ['chart', 'dashboard', 'database', 'dataset', 'query'] },
        id: { type: 'integer', minimum: 0 },
        uuid: cleanAuthorizationStringSchema,
      },
    },
    action: { enum: ['create', 'delete', 'read', 'write'] },
  },
} as const;

export const permissionCheckResponseSchema = {
  $id: 'ax-services.permission-check.v1.response',
  type: 'object',
  required: ['contractVersion', 'allowed'],
  additionalProperties: false,
  properties: {
    contractVersion: { const: AUTHORIZATION_CONTRACT_VERSION },
    allowed: { type: 'boolean' },
    reason: externalMessageSchema,
    statusCode: { type: 'integer', minimum: 100, maximum: 599 },
    error: externalMessageSchema,
  },
} as const;

export const authorizationContractSchemas = {
  permissionCheckRequestSchema,
  permissionCheckResponseSchema,
} as const;
