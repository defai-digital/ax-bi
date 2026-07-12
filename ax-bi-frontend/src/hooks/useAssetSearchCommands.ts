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
import { useHistory } from 'src/hooks/useAppHistory';
import { useEffect, useRef } from 'react';
import rison from 'rison';
import { t } from '@ax-bi/core/translation';
import { AxBIClient } from '@ax-bi/ui-core';
import {
  useOptionalCommandPalette,
  Command,
} from 'src/components/CommandPalette';
import { ensureAppRoot } from 'src/utils/pathUtils';

const DEBOUNCE_MS = 280;
const PAGE_SIZE = 5;
const ASSET_PREFIX = 'asset-search-';

interface ListResult {
  id: number;
  dashboard_title?: string;
  slice_name?: string;
  url?: string;
}

/**
 * While the command palette is open, registers transient asset commands for
 * dashboards and charts matching the latest search query (debounced).
 *
 * Note: the palette UI does not yet pass the query into this hook. Callers
 * should use {@link useAssetSearchForQuery} with the live query string from
 * CommandPalette, or we listen via a shared module event. For v1 we poll
 * nothing — instead CommandPalette calls `window` custom event.
 */
export function useAssetSearchCommands(): void {
  const history = useHistory();
  const palette = useOptionalCommandPalette();
  const cleanupsRef = useRef<Array<() => void>>([]);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const requestIdRef = useRef(0);

  useEffect(() => {
    if (!palette) {
      return undefined;
    }

    const clearAssetCommands = () => {
      cleanupsRef.current.forEach(fn => fn());
      cleanupsRef.current = [];
    };

    const runSearch = async (query: string) => {
      const q = query.trim();
      clearAssetCommands();
      if (q.length < 2) {
        return;
      }

      requestIdRef.current += 1;
      const requestId = requestIdRef.current;
      const appRoot = ensureAppRoot('');

      try {
        const filter = {
          filters: [
            {
              col: 'dashboard_title',
              opr: 'ct',
              value: q,
            },
          ],
          page_size: PAGE_SIZE,
          order_column: 'changed_on_delta_humanized',
          order_direction: 'desc',
        };
        const chartFilter = {
          filters: [
            {
              col: 'slice_name',
              opr: 'ct',
              value: q,
            },
          ],
          page_size: PAGE_SIZE,
          order_column: 'changed_on_delta_humanized',
          order_direction: 'desc',
        };

        const [dashRes, chartRes] = await Promise.all([
          AxBIClient.get({
            endpoint: `/api/v1/dashboard/?q=${rison.encode(filter)}`,
          }),
          AxBIClient.get({
            endpoint: `/api/v1/chart/?q=${rison.encode(chartFilter)}`,
          }),
        ]);

        if (requestId !== requestIdRef.current) {
          return;
        }

        const dashboards: ListResult[] = dashRes.json?.result ?? [];
        const charts: ListResult[] = chartRes.json?.result ?? [];
        const commands: Command[] = [
          ...dashboards.map(d => ({
            id: `${ASSET_PREFIX}dashboard-${d.id}`,
            name: d.dashboard_title || t('Untitled dashboard'),
            description: t('Dashboard'),
            type: 'asset' as const,
            keywords: ['dashboard', d.dashboard_title || ''],
            action: () => {
              history.push(
                d.url
                  ? ensureAppRoot(d.url)
                  : `${appRoot}/ax-bi/dashboard/${d.id}/`,
              );
            },
          })),
          ...charts.map(c => ({
            id: `${ASSET_PREFIX}chart-${c.id}`,
            name: c.slice_name || t('Untitled chart'),
            description: t('Chart'),
            type: 'asset' as const,
            keywords: ['chart', c.slice_name || ''],
            action: () => {
              history.push(
                c.url
                  ? ensureAppRoot(c.url)
                  : `${appRoot}/explore/?slice_id=${c.id}`,
              );
            },
          })),
        ];

        cleanupsRef.current = commands.map(cmd => palette.registerCommand(cmd));
      } catch {
        // Soft-fail: navigation commands remain available
      }
    };

    const onQuery = (event: Event) => {
      const detail = (event as CustomEvent<string>).detail ?? '';
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
      timerRef.current = setTimeout(() => {
        runSearch(detail);
      }, DEBOUNCE_MS);
    };

    window.addEventListener('axbi-command-palette-query', onQuery);
    return () => {
      window.removeEventListener('axbi-command-palette-query', onQuery);
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
      clearAssetCommands();
    };
  }, [palette, history]);
}

export default useAssetSearchCommands;
