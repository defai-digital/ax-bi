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
import { ServiceConfig } from './config';

export interface DependencyHealth {
  ok: boolean;
  url: string;
  statusCode?: number;
  error?: string;
}

export interface SupersetHealthClient {
  checkHealth(): Promise<DependencyHealth>;
}

export class SupersetClient implements SupersetHealthClient {
  private readonly healthUrl: string;

  constructor(private readonly config: ServiceConfig) {
    this.healthUrl = `${config.supersetBaseUrl}${config.supersetHealthPath}`;
  }

  async checkHealth(): Promise<DependencyHealth> {
    try {
      const response = await fetch(this.healthUrl, {
        signal: AbortSignal.timeout(this.config.supersetTimeoutMs),
      });

      return {
        ok: response.ok,
        statusCode: response.status,
        url: this.healthUrl,
      };
    } catch (error) {
      return {
        ok: false,
        error: error instanceof Error ? error.message : String(error),
        url: this.healthUrl,
      };
    }
  }
}
