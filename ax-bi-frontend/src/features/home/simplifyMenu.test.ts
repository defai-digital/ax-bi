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
import { MenuObjectProps } from 'src/types/bootstrapTypes';
import { simplifyMenuData, flattenChilds } from './simplifyMenu';

const dashboards: MenuObjectProps = { name: 'Dashboards', label: 'Dashboards' };
const charts: MenuObjectProps = { name: 'Charts', label: 'Charts' };
const datasets: MenuObjectProps = { name: 'Datasets', label: 'Datasets' };
const sql: MenuObjectProps = {
  name: 'SQL Lab',
  label: 'SQL',
  childs: [
    { name: 'SQL Lab', label: 'SQL Lab', url: '/sqllab' },
    '-',
    {
      name: 'Saved Queries',
      label: 'Saved Queries',
      url: '/savedqueryview/list/',
    },
    { name: 'Query History', label: 'Query History', url: '/sqllab/history/' },
  ],
};

const fullMenu = (): MenuObjectProps[] => [
  { ...dashboards },
  { ...charts },
  { ...datasets },
  { ...sql, childs: [...(sql.childs ?? [])] },
];

test('flag off returns the input unchanged with no demoted items', () => {
  const input = fullMenu();
  const { menu, demoted } = simplifyMenuData(input, false);
  expect(menu).toBe(input);
  expect(demoted).toEqual([]);
});

test('flag on demotes the SQL group out of the primary nav', () => {
  const { menu, demoted } = simplifyMenuData(fullMenu(), true);
  expect(menu.map(i => i.label)).toEqual(['Dashboards', 'Charts', 'Datasets']);
  expect(demoted.map(i => i.name)).toEqual(['SQL Lab']);
});

test('flag on with no SQL item (e.g. Gamma) leaves the nav untouched', () => {
  const gammaMenu = [{ ...dashboards }, { ...charts }];
  const { menu, demoted } = simplifyMenuData(gammaMenu, true);
  expect(menu.map(i => i.label)).toEqual(['Dashboards', 'Charts']);
  expect(demoted).toEqual([]);
});

test('matches on either name or label so translation cannot break demotion', () => {
  const labelOnly: MenuObjectProps[] = [{ label: 'SQL' }];
  expect(simplifyMenuData(labelOnly, true).demoted).toHaveLength(1);
  const nameOnly: MenuObjectProps[] = [
    { label: 'translated', name: 'SQL Lab' },
  ];
  expect(simplifyMenuData(nameOnly, true).demoted).toHaveLength(1);
});

test('no destination is lost: kept and demoted partition the input', () => {
  const input = fullMenu();
  const { menu, demoted } = simplifyMenuData(input, true);
  expect(menu.length + demoted.length).toBe(input.length);
});

test('flattenChilds lifts leaf entries out of demoted groups and drops dividers', () => {
  const { demoted } = simplifyMenuData(fullMenu(), true);
  const leaves = flattenChilds(demoted);
  expect(leaves.map(l => l.label)).toEqual([
    'SQL Lab',
    'Saved Queries',
    'Query History',
  ]);
});

test('flattenChilds keeps a childless demoted item reachable as its own leaf', () => {
  const leaves = flattenChilds([{ name: 'SQL', label: 'SQL', url: '/sqllab' }]);
  expect(leaves).toEqual([{ name: 'SQL', label: 'SQL', url: '/sqllab' }]);
});
