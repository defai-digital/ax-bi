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

/**
 * Stable icon keys for Settings dropdown items. Keys match
 * `@ax-bi/ui-core/components/Icons` exports so RightMenu can render
 * `<Icons[key] />` without stringly-typed React nodes in this module.
 */
export type SettingsMenuIconName =
  | 'DatabaseOutlined'
  | 'TableOutlined'
  | 'DashboardOutlined'
  | 'BarChartOutlined'
  | 'UserOutlined'
  | 'UserAddOutlined'
  | 'UsergroupAddOutlined'
  | 'GroupOutlined'
  | 'KeyOutlined'
  | 'LockOutlined'
  | 'AppstoreOutlined'
  | 'FormatPainterOutlined'
  | 'BgColorsOutlined'
  | 'ApiOutlined'
  | 'ClockCircleOutlined'
  | 'TagsOutlined'
  | 'ConsoleSqlOutlined'
  | 'SaveOutlined'
  | 'HistoryOutlined'
  | 'UnorderedListOutlined'
  | 'BellOutlined'
  | 'CommentOutlined'
  | 'InfoCircleOutlined'
  | 'LogoutOutlined'
  | 'SettingOutlined'
  | 'BookOutlined'
  | 'BugOutlined'
  | 'SafetyCertificateOutlined';

/** Menu child fields used for icon resolution (name preferred over label). */
export type SettingsMenuIconSource = {
  name?: string;
  label?: string;
  url?: string;
};

/**
 * Exact matches on FAB `name` (stable English identifiers from backend menu
 * registration). Prefer these over translated labels.
 */
const NAME_ICON_MAP: Record<string, SettingsMenuIconName> = {
  // Data
  Databases: 'DatabaseOutlined',
  Datasets: 'TableOutlined',
  // Security
  'List Roles': 'SafetyCertificateOutlined',
  'List Users': 'UserOutlined',
  'List Groups': 'GroupOutlined',
  'User Registrations': 'UserAddOutlined',
  'Action Log': 'UnorderedListOutlined',
  'Row Level Security': 'LockOutlined',
  // Manage
  Plugins: 'AppstoreOutlined',
  'CSS Templates': 'FormatPainterOutlined',
  Themes: 'BgColorsOutlined',
  Extensions: 'ApiOutlined',
  Tasks: 'ClockCircleOutlined',
  Tags: 'TagsOutlined',
  'Alerts & Report': 'BellOutlined',
  'Alerts & Reports': 'BellOutlined',
  'Annotation Layers': 'CommentOutlined',
  // SQL / Advanced
  'SQL Editor': 'ConsoleSqlOutlined',
  'SQL Lab': 'ConsoleSqlOutlined',
  'Saved Queries': 'SaveOutlined',
  'Query Search': 'HistoryOutlined',
  'Query History': 'HistoryOutlined',
  // User
  Info: 'InfoCircleOutlined',
  Logout: 'LogoutOutlined',
};

/** Substring / keyword rules applied to lowercased name+label+url. */
const KEYWORD_RULES: { match: RegExp; icon: SettingsMenuIconName }[] = [
  { match: /database|connection/, icon: 'DatabaseOutlined' },
  { match: /dataset|tablemodel/, icon: 'TableOutlined' },
  { match: /dashboard/, icon: 'DashboardOutlined' },
  { match: /chart|slice/, icon: 'BarChartOutlined' },
  { match: /role/, icon: 'SafetyCertificateOutlined' },
  { match: /registration/, icon: 'UserAddOutlined' },
  { match: /user/, icon: 'UserOutlined' },
  { match: /group/, icon: 'GroupOutlined' },
  { match: /row.?level|rls/, icon: 'LockOutlined' },
  { match: /action.?log|audit/, icon: 'UnorderedListOutlined' },
  { match: /plugin/, icon: 'AppstoreOutlined' },
  { match: /css/, icon: 'FormatPainterOutlined' },
  { match: /theme/, icon: 'BgColorsOutlined' },
  { match: /extension/, icon: 'ApiOutlined' },
  { match: /task/, icon: 'ClockCircleOutlined' },
  { match: /tag/, icon: 'TagsOutlined' },
  { match: /alert|report/, icon: 'BellOutlined' },
  { match: /annotation/, icon: 'CommentOutlined' },
  { match: /sql.?lab|sqllab|sql editor/, icon: 'ConsoleSqlOutlined' },
  { match: /saved.?quer/, icon: 'SaveOutlined' },
  { match: /query.?history|query.?search|history/, icon: 'HistoryOutlined' },
  { match: /logout|sign.?out/, icon: 'LogoutOutlined' },
  { match: /info|profile/, icon: 'InfoCircleOutlined' },
  { match: /security|permission/, icon: 'KeyOutlined' },
  { match: /setting|manage/, icon: 'SettingOutlined' },
  { match: /doc|help/, icon: 'BookOutlined' },
  { match: /bug/, icon: 'BugOutlined' },
];

/**
 * Resolve a Settings menu icon key for a backend menu child or synthetic item.
 * Pure: no React / i18n dependency so unit tests stay fast and stable.
 */
export function resolveSettingsMenuIconKey(
  item: SettingsMenuIconSource,
): SettingsMenuIconName | undefined {
  const name = (item.name || '').trim();
  if (name && NAME_ICON_MAP[name]) {
    return NAME_ICON_MAP[name];
  }

  const haystack = [item.name, item.label, item.url]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();

  if (!haystack) {
    return undefined;
  }

  for (const rule of KEYWORD_RULES) {
    if (rule.match.test(haystack)) {
      return rule.icon;
    }
  }

  return undefined;
}
