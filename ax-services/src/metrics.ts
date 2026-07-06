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

const UNMATCHED_ROUTE_METRIC_PATH = '<unmatched>';

interface MutableRouteMetrics {
  count: number;
  errorCount: number;
  totalDurationMs: number;
  maxDurationMs: number;
}

interface MutableDurationMetrics {
  count: number;
  totalDurationMs: number;
  maxDurationMs: number;
}

export class ServiceMetrics {
  private readonly startedAtMs = Date.now();

  private readonly requestStarts = new WeakMap<FastifyRequest, bigint>();

  private readonly routes = new Map<string, MutableRouteMetrics>();

  private readonly totals: MutableDurationMetrics = {
    count: 0,
    totalDurationMs: 0,
    maxDurationMs: 0,
  };

  private errorCount = 0;

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

    recordDuration(this.totals, durationMs);
    recordDuration(routeMetrics, durationMs);

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
        total: this.totals.count,
        errorCount: this.errorCount,
        averageDurationMs: average(
          this.totals.totalDurationMs,
          this.totals.count,
        ),
        maxDurationMs: this.totals.maxDurationMs,
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
  return request.routeOptions.url ?? UNMATCHED_ROUTE_METRIC_PATH;
}

function toRouteContract(metrics: MutableRouteMetrics): RouteMetricsContract {
  return {
    count: metrics.count,
    errorCount: metrics.errorCount,
    averageDurationMs: average(metrics.totalDurationMs, metrics.count),
    maxDurationMs: metrics.maxDurationMs,
  };
}

function recordDuration(
  metrics: MutableDurationMetrics,
  durationMs: number,
): void {
  metrics.count += 1;
  metrics.totalDurationMs += durationMs;
  metrics.maxDurationMs = Math.max(metrics.maxDurationMs, durationMs);
}

function average(total: number, count: number): number {
  return count === 0 ? 0 : total / count;
}
