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
type LogContext = Record<string, unknown>;

export interface ServiceLogger {
  info(message: string, context?: LogContext): void;
  error(message: string, context?: LogContext): void;
}

function serializeError(value: unknown): unknown {
  if (value instanceof Error) {
    return {
      message: value.message,
      name: value.name,
      stack: value.stack,
    };
  }
  return value;
}

function normalizeContext(context: LogContext = {}): LogContext {
  return Object.fromEntries(
    Object.entries(context).map(([key, value]) => [key, serializeError(value)]),
  );
}

export function createLogger(logLevel: string): ServiceLogger {
  return {
    info(message: string, context: LogContext = {}) {
      if (logLevel === 'silent') {
        return;
      }
      console.log(
        JSON.stringify({
          level: 'info',
          message,
          ...normalizeContext(context),
        }),
      );
    },
    error(message: string, context: LogContext = {}) {
      if (logLevel === 'silent') {
        return;
      }
      console.error(
        JSON.stringify({
          level: 'error',
          message,
          ...normalizeContext(context),
        }),
      );
    },
  };
}
