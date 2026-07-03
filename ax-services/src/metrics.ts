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
import { FastifyReply, FastifyRequest } from 'fastify';

import {
  MetricsResponseContract,
  RouteMetricsContract,
  RUNTIME_CONTRACT_VERSION,
} from './contracts/runtime';

interface MutableRouteMetrics {
  count: number;
  errorCount: number;
  totalDurationMs: number;
  maxDurationMs: number;
}

export class ServiceMetrics {
  private readonly startedAtMs = Date.now();

  private readonly requestStarts = new WeakMap<FastifyRequest, bigint>();

  private readonly routes = new Map<string, MutableRouteMetrics>();

  private totalRequests = 0;

  private errorCount = 0;

  private totalDurationMs = 0;

  private maxDurationMs = 0;

  startRequest(request: FastifyRequest): void {
    this.requestStarts.set(request, process.hrtime.bigint());
  }

  recordResponse(request: FastifyRequest, reply: FastifyReply): void {
    const startedAt = this.requestStarts.get(request);
    const durationMs =
      startedAt === undefined
        ? 0
        : Number(process.hrtime.bigint() - startedAt) / 1_000_000;
    const routeKey = `${request.method} ${routeMetricsPath(request)}`;
    const routeMetrics = this.getRouteMetrics(routeKey);
    const isError = reply.statusCode >= 500;

    this.totalRequests += 1;
    this.totalDurationMs += durationMs;
    this.maxDurationMs = Math.max(this.maxDurationMs, durationMs);

    routeMetrics.count += 1;
    routeMetrics.totalDurationMs += durationMs;
    routeMetrics.maxDurationMs = Math.max(routeMetrics.maxDurationMs, durationMs);

    if (isError) {
      this.errorCount += 1;
      routeMetrics.errorCount += 1;
    }
  }

  snapshot(): MetricsResponseContract {
    return {
      contractVersion: RUNTIME_CONTRACT_VERSION,
      service: 'ax-services',
      status: 'ok',
      uptimeSeconds: (Date.now() - this.startedAtMs) / 1000,
      requests: {
        total: this.totalRequests,
        errorCount: this.errorCount,
        averageDurationMs: average(this.totalDurationMs, this.totalRequests),
        maxDurationMs: this.maxDurationMs,
        routes: Object.fromEntries(
          [...this.routes.entries()].map(([route, metrics]) => [
            route,
            toRouteContract(metrics),
          ]),
        ),
      },
    };
  }

  private getRouteMetrics(route: string): MutableRouteMetrics {
    const existing = this.routes.get(route);
    if (existing) {
      return existing;
    }

    const created = {
      count: 0,
      errorCount: 0,
      totalDurationMs: 0,
      maxDurationMs: 0,
    };
    this.routes.set(route, created);
    return created;
  }
}

function routeMetricsPath(request: FastifyRequest): string {
  return request.routeOptions.url ?? stripQueryString(request.url);
}

function stripQueryString(url: string): string {
  const queryIndex = url.indexOf('?');

  return queryIndex === -1 ? url : url.slice(0, queryIndex);
}

function toRouteContract(metrics: MutableRouteMetrics): RouteMetricsContract {
  return {
    count: metrics.count,
    errorCount: metrics.errorCount,
    averageDurationMs: average(metrics.totalDurationMs, metrics.count),
    maxDurationMs: metrics.maxDurationMs,
  };
}

function average(total: number, count: number): number {
  return count === 0 ? 0 : total / count;
}
