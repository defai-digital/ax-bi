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

import {
  axbiGetCache,
  clearDatasetCache,
  clearAllDatasetCache,
} from './cachedAxBIGet';

describe('cachedAxBIGet', () => {
  beforeEach(() => {
    axbiGetCache.clear();
  });

  describe('clearDatasetCache', () => {
    test('clears cache entries for specific dataset ID', () => {
      axbiGetCache.set('/api/v1/dataset/123', { data: 'dataset123' });
      axbiGetCache.set('/api/v1/dataset/123/', { data: 'dataset123slash' });
      axbiGetCache.set('/api/v1/dataset/123?query=1', {
        data: 'dataset123query',
      });
      axbiGetCache.set('/api/v1/dataset/456', { data: 'dataset456' });
      axbiGetCache.set('/api/v1/other/123', { data: 'other' });

      clearDatasetCache(123);

      expect(axbiGetCache.has('/api/v1/dataset/123')).toBe(false);
      expect(axbiGetCache.has('/api/v1/dataset/123/')).toBe(false);
      expect(axbiGetCache.has('/api/v1/dataset/123?query=1')).toBe(false);
      expect(axbiGetCache.has('/api/v1/dataset/456')).toBe(true);
      expect(axbiGetCache.has('/api/v1/other/123')).toBe(true);
    });

    test('clears cache entries for string dataset ID', () => {
      axbiGetCache.set('/api/v1/dataset/abc-123', { data: 'datasetAbc' });
      axbiGetCache.set('/api/v1/dataset/abc-123/', {
        data: 'datasetAbcSlash',
      });
      axbiGetCache.set('/api/v1/dataset/def-456', { data: 'datasetDef' });

      clearDatasetCache('abc-123');

      expect(axbiGetCache.has('/api/v1/dataset/abc-123')).toBe(false);
      expect(axbiGetCache.has('/api/v1/dataset/abc-123/')).toBe(false);
      expect(axbiGetCache.has('/api/v1/dataset/def-456')).toBe(true);
    });

    test('handles null dataset ID gracefully', () => {
      axbiGetCache.set('/api/v1/dataset/123', { data: 'dataset123' });

      clearDatasetCache(null as any);

      expect(axbiGetCache.has('/api/v1/dataset/123')).toBe(true);
    });

    test('handles undefined dataset ID gracefully', () => {
      axbiGetCache.set('/api/v1/dataset/123', { data: 'dataset123' });

      clearDatasetCache(undefined as any);

      expect(axbiGetCache.has('/api/v1/dataset/123')).toBe(true);
    });

    test('handles empty string dataset ID gracefully', () => {
      axbiGetCache.set('/api/v1/dataset/123', { data: 'dataset123' });

      clearDatasetCache('');

      expect(axbiGetCache.has('/api/v1/dataset/123')).toBe(true);
    });

    test('does not clear unrelated cache entries', () => {
      axbiGetCache.set('/api/v1/chart/123', { data: 'chart123' });
      axbiGetCache.set('/api/v1/dashboard/123', { data: 'dashboard123' });
      axbiGetCache.set('/api/v1/database/123', { data: 'database123' });
      axbiGetCache.set('/api/v1/dataset/123', { data: 'dataset123' });

      clearDatasetCache(123);

      expect(axbiGetCache.has('/api/v1/chart/123')).toBe(true);
      expect(axbiGetCache.has('/api/v1/dashboard/123')).toBe(true);
      expect(axbiGetCache.has('/api/v1/database/123')).toBe(true);
      expect(axbiGetCache.has('/api/v1/dataset/123')).toBe(false);
    });

    test('only clears exact dataset ID matches', () => {
      axbiGetCache.set('/api/v1/dataset/1', { data: 'dataset1' });
      axbiGetCache.set('/api/v1/dataset/12', { data: 'dataset12' });
      axbiGetCache.set('/api/v1/dataset/123', { data: 'dataset123' });
      axbiGetCache.set('/api/v1/dataset/1234', { data: 'dataset1234' });
      axbiGetCache.set('/api/v1/dataset/456', { data: 'dataset456' });

      clearDatasetCache(123);

      expect(axbiGetCache.has('/api/v1/dataset/1')).toBe(true);
      expect(axbiGetCache.has('/api/v1/dataset/12')).toBe(true);
      expect(axbiGetCache.has('/api/v1/dataset/123')).toBe(false);
      expect(axbiGetCache.has('/api/v1/dataset/1234')).toBe(true); // Should not be cleared - different ID
      expect(axbiGetCache.has('/api/v1/dataset/456')).toBe(true);
    });

    test('clears cache entries with various URL patterns', () => {
      axbiGetCache.set('/api/v1/dataset/789', { data: 'base' });
      axbiGetCache.set('/api/v1/dataset/789/columns', { data: 'columns' });
      axbiGetCache.set('/api/v1/dataset/789/related', { data: 'related' });
      axbiGetCache.set('/api/v1/dataset/789?full=true', {
        data: 'withQuery',
      });

      clearDatasetCache(789);

      expect(axbiGetCache.has('/api/v1/dataset/789')).toBe(false);
      expect(axbiGetCache.has('/api/v1/dataset/789/columns')).toBe(false);
      expect(axbiGetCache.has('/api/v1/dataset/789/related')).toBe(false);
      expect(axbiGetCache.has('/api/v1/dataset/789?full=true')).toBe(false);
    });
  });

  describe('clearAllDatasetCache', () => {
    test('clears all dataset cache entries', () => {
      axbiGetCache.set('/api/v1/dataset/123', { data: 'dataset123' });
      axbiGetCache.set('/api/v1/dataset/456', { data: 'dataset456' });
      axbiGetCache.set('/api/v1/dataset/789/columns', { data: 'columns' });
      axbiGetCache.set('/api/v1/chart/123', { data: 'chart123' });
      axbiGetCache.set('/api/v1/dashboard/456', { data: 'dashboard456' });

      clearAllDatasetCache();

      expect(axbiGetCache.has('/api/v1/dataset/123')).toBe(false);
      expect(axbiGetCache.has('/api/v1/dataset/456')).toBe(false);
      expect(axbiGetCache.has('/api/v1/dataset/789/columns')).toBe(false);
      expect(axbiGetCache.has('/api/v1/chart/123')).toBe(true);
      expect(axbiGetCache.has('/api/v1/dashboard/456')).toBe(true);
    });

    test('handles empty cache gracefully', () => {
      expect(axbiGetCache.size).toBe(0);

      clearAllDatasetCache();

      expect(axbiGetCache.size).toBe(0);
    });

    test('preserves non-dataset cache entries', () => {
      axbiGetCache.set('/api/v1/chart/list', { data: 'chartList' });
      axbiGetCache.set('/api/v1/dashboard/list', { data: 'dashboardList' });
      axbiGetCache.set('/api/v1/database/list', { data: 'databaseList' });
      axbiGetCache.set('/api/v1/query/list', { data: 'queryList' });

      clearAllDatasetCache();

      expect(axbiGetCache.has('/api/v1/chart/list')).toBe(true);
      expect(axbiGetCache.has('/api/v1/dashboard/list')).toBe(true);
      expect(axbiGetCache.has('/api/v1/database/list')).toBe(true);
      expect(axbiGetCache.has('/api/v1/query/list')).toBe(true);
    });

    test('clears all variations of dataset endpoints', () => {
      axbiGetCache.set('/api/v1/dataset/', { data: 'list' });
      axbiGetCache.set('/api/v1/dataset/export', { data: 'export' });
      axbiGetCache.set('/api/v1/dataset/import', { data: 'import' });
      axbiGetCache.set('/api/v1/dataset/duplicate', { data: 'duplicate' });
      axbiGetCache.set('/api/v1/dataset/1/refresh', { data: 'refresh' });

      clearAllDatasetCache();

      expect(axbiGetCache.has('/api/v1/dataset/')).toBe(false);
      expect(axbiGetCache.has('/api/v1/dataset/export')).toBe(false);
      expect(axbiGetCache.has('/api/v1/dataset/import')).toBe(false);
      expect(axbiGetCache.has('/api/v1/dataset/duplicate')).toBe(false);
      expect(axbiGetCache.has('/api/v1/dataset/1/refresh')).toBe(false);
    });
  });
});
