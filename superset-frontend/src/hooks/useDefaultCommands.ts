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
import { useEffect } from 'react';
import { useHistory } from 'react-router-dom';
import { t } from '@apache-superset/core/translation';
import { useCommandPalette, Command } from 'src/components/CommandPalette';
import { ensureAppRoot } from 'src/utils/pathUtils';

/**
 * Registers the default set of navigation and action commands
 * for the command palette. Commands use React Router's history
 * to navigate within the SPA.
 */
export function useDefaultCommands(): void {
  const history = useHistory();
  const { registerCommand } = useCommandPalette();
  const appRoot = ensureAppRoot('');

  const navigate = (path: string) => {
    history.push(path);
  };

  useEffect(() => {
    const commands: Command[] = [
      // Navigation commands
      {
        id: 'nav-home',
        name: t('Home'),
        description: t('Go to the home page'),
        type: 'navigation',
        keywords: ['welcome', 'start', 'main'],
        action: () => navigate(`${appRoot}/superset/welcome/`),
      },
      {
        id: 'nav-dashboards',
        name: t('Dashboards'),
        description: t('Browse all dashboards'),
        type: 'navigation',
        keywords: ['dashboard', 'list', 'view'],
        action: () => navigate(`${appRoot}/dashboard/list/`),
      },
      {
        id: 'nav-charts',
        name: t('Charts'),
        description: t('Browse all charts'),
        type: 'navigation',
        keywords: ['chart', 'list', 'view', 'visualization'],
        action: () => navigate(`${appRoot}/chart/list/`),
      },
      {
        id: 'nav-datasets',
        name: t('Datasets'),
        description: t('Browse all datasets'),
        type: 'navigation',
        keywords: ['dataset', 'table', 'list', 'data'],
        action: () => navigate(`${appRoot}/tablemodelview/list/`),
      },
      {
        id: 'nav-databases',
        name: t('Databases'),
        description: t('Browse connected databases'),
        type: 'navigation',
        keywords: ['database', 'connection', 'list'],
        action: () => navigate(`${appRoot}/databaseview/list/`),
      },
      {
        id: 'nav-sql-lab',
        name: t('SQL Lab'),
        description: t('Open the SQL editor'),
        type: 'navigation',
        keywords: ['sql', 'query', 'editor', 'lab'],
        action: () => navigate(`${appRoot}/sqllab/`),
      },
      {
        id: 'nav-saved-queries',
        name: t('Saved Queries'),
        description: t('Browse saved SQL queries'),
        type: 'navigation',
        keywords: ['saved', 'query', 'sql', 'history'],
        action: () => navigate(`${appRoot}/savedqueryview/list/`),
      },
      {
        id: 'nav-query-history',
        name: t('Query History'),
        description: t('View recent query executions'),
        type: 'navigation',
        keywords: ['query', 'history', 'recent', 'log'],
        action: () => navigate(`${appRoot}/sqllab/history/`),
      },
      {
        id: 'nav-alerts',
        name: t('Alerts & Reports'),
        description: t('Manage alerts and scheduled reports'),
        type: 'navigation',
        keywords: ['alert', 'report', 'schedule', 'notification'],
        action: () => navigate(`${appRoot}/alert/list/`),
      },

      // Action commands
      {
        id: 'action-new-dashboard',
        name: t('New Dashboard'),
        description: t('Create a new dashboard'),
        type: 'action',
        keywords: ['create', 'new', 'dashboard'],
        action: () => navigate(`${appRoot}/dashboard/new/`),
      },
      {
        id: 'action-new-chart',
        name: t('New Chart'),
        description: t('Create a new chart or visualization'),
        type: 'action',
        keywords: ['create', 'new', 'chart', 'visualization', 'explore'],
        action: () => navigate(`${appRoot}/chart/add`),
      },
      {
        id: 'action-new-sql-query',
        name: t('New SQL Query'),
        description: t('Open a new SQL Lab tab'),
        type: 'action',
        keywords: ['create', 'new', 'sql', 'query', 'editor'],
        action: () => navigate(`${appRoot}/sqllab?new=true`),
      },
      {
        id: 'action-upload-data',
        name: t('Upload Data'),
        description: t('Upload a CSV, Excel, or Parquet file to start exploring'),
        type: 'action',
        keywords: ['upload', 'csv', 'excel', 'file', 'import'],
        action: () => navigate(`${appRoot}/upload/`),
      },
    ];

    const cleanups = commands.map(cmd => registerCommand(cmd));

    return () => {
      cleanups.forEach(cleanup => cleanup());
    };
  }, [registerCommand, history, appRoot]);
}

export default useDefaultCommands;
