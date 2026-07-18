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
import { createElement, useEffect, useRef } from 'react';
import { t } from '@ax-bi/core/translation';
import { FeatureFlag, isFeatureEnabled } from '@ax-bi/ui-core';
import { Icons } from '@ax-bi/ui-core/components';
import {
  useOptionalCommandPalette,
  Command,
} from 'src/components/CommandPalette';
import { ensureAppRoot } from 'src/utils/pathUtils';
import {
  AssetSearchResults,
  AssetSearchType,
  searchAssets,
} from 'src/services/assetSearch';

const DEBOUNCE_MS = 250;
const MIN_QUERY_LENGTH = 2;
const ASSET_PREFIX = 'asset-search-';

/**
 * Search coverage without GLOBAL_SEARCH_V2: dashboards and charts only.
 */
const LEGACY_TYPES: AssetSearchType[] = ['dashboards', 'charts'];

type HistoryPush = ReturnType<typeof useHistory>['push'];

const buildAssetCommands = (
  results: AssetSearchResults,
  appRoot: string,
  push: HistoryPush,
): Command[] => [
  ...results.dashboards.map(dashboard => ({
    id: `${ASSET_PREFIX}dashboard-${dashboard.id}`,
    name: dashboard.title || t('Untitled dashboard'),
    description: t('Dashboard'),
    type: 'asset' as const,
    icon: createElement(Icons.DashboardOutlined, { iconSize: 'm' }),
    keywords: ['dashboard', dashboard.title],
    action: () => {
      push(
        dashboard.url
          ? ensureAppRoot(dashboard.url)
          : `${appRoot}/ax-bi/dashboard/${dashboard.id}/`,
      );
    },
  })),
  ...results.charts.map(chart => ({
    id: `${ASSET_PREFIX}chart-${chart.id}`,
    name: chart.title || t('Untitled chart'),
    description: t('Chart'),
    type: 'asset' as const,
    icon: createElement(Icons.BarChartOutlined, { iconSize: 'm' }),
    keywords: ['chart', chart.title],
    action: () => {
      push(
        chart.url
          ? ensureAppRoot(chart.url)
          : `${appRoot}/explore/?slice_id=${chart.id}`,
      );
    },
  })),
  ...results.datasets.map(dataset => ({
    id: `${ASSET_PREFIX}dataset-${dataset.id}`,
    name: dataset.title || t('Untitled dataset'),
    description: t('Dataset'),
    type: 'asset' as const,
    icon: createElement(Icons.TableOutlined, { iconSize: 'm' }),
    keywords: ['dataset', dataset.title],
    action: () => {
      push(`${appRoot}/dataset/${dataset.id}`);
    },
  })),
  ...results.databases.map(database => ({
    id: `${ASSET_PREFIX}database-${database.id}`,
    name: database.title || t('Untitled database'),
    description: t('Database'),
    type: 'asset' as const,
    icon: createElement(Icons.DatabaseOutlined, { iconSize: 'm' }),
    keywords: ['database', database.title],
    action: () => {
      push(`${appRoot}/databases`);
    },
  })),
  ...results.savedQueries.map(savedQuery => ({
    id: `${ASSET_PREFIX}saved-query-${savedQuery.id}`,
    name: savedQuery.title || t('Untitled query'),
    description: t('Saved query'),
    type: 'asset' as const,
    icon: createElement(Icons.ConsoleSqlOutlined, { iconSize: 'm' }),
    keywords: ['saved', 'query', 'sql', savedQuery.title],
    action: () => {
      push(`${appRoot}/sqllab?savedQueryId=${savedQuery.id}`);
    },
  })),
];

/**
 * While the command palette is open, registers transient asset commands for
 * assets matching the live palette query (debounced via the palette context).
 *
 * Coverage is controlled by the GLOBAL_SEARCH_V2 feature flag: when enabled
 * all five asset types are searched; when disabled only dashboards and
 * charts are searched, matching the pre-v2 behavior.
 */
export function useAssetSearchCommands(): void {
  const history = useHistory();
  const palette = useOptionalCommandPalette();
  const cleanupsRef = useRef<Array<() => void>>([]);
  const requestIdRef = useRef(0);

  const isOpen = palette?.isOpen ?? false;
  const query = palette?.query ?? '';

  useEffect(() => {
    if (!palette) {
      return undefined;
    }

    const clearAssetCommands = () => {
      cleanupsRef.current.forEach(fn => fn());
      cleanupsRef.current = [];
    };

    const trimmed = query.trim();
    if (!isOpen || trimmed.length < MIN_QUERY_LENGTH) {
      clearAssetCommands();
      return undefined;
    }

    const appRoot = ensureAppRoot('');
    const controller = new AbortController();

    const runSearch = async () => {
      requestIdRef.current += 1;
      const requestId = requestIdRef.current;
      const types = isFeatureEnabled(FeatureFlag.GlobalSearchV2)
        ? undefined
        : LEGACY_TYPES;

      try {
        const results = await searchAssets(trimmed, {
          types,
          signal: controller.signal,
        });

        if (requestId !== requestIdRef.current) {
          return;
        }

        clearAssetCommands();
        cleanupsRef.current = buildAssetCommands(
          results,
          appRoot,
          history.push,
        ).map(cmd => palette.registerCommand(cmd));
      } catch {
        // Soft-fail: navigation commands remain available
      }
    };

    const timer = setTimeout(() => {
      runSearch();
    }, DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      controller.abort();
      // Invalidate any in-flight search so stale results never register.
      requestIdRef.current += 1;
    };
  }, [palette, isOpen, query, history]);

  // Unregister asset commands when the hook unmounts.
  useEffect(
    () => () => {
      cleanupsRef.current.forEach(fn => fn());
      cleanupsRef.current = [];
    },
    [],
  );
}

export default useAssetSearchCommands;
