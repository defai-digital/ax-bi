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
import { descending } from 'd3-array';
import { chord as d3Chord } from 'd3-chord';
import Chord from '../src/Chord';

test('descending sort helper is provided by d3-array (not d3-selection)', () => {
  // Regression: importing descending from d3-selection yields undefined and
  // silently disables chord subgroup/chord sort at runtime.
  expect(typeof descending).toBe('function');
  expect(descending(2, 1)).toBeLessThan(0);
  expect(descending(1, 2)).toBeGreaterThan(0);

  // eslint-disable-next-line @typescript-eslint/no-require-imports, global-require
  const selection = require('d3-selection');
  expect(selection.descending).toBeUndefined();
});

test('d3-chord layout accepts d3-array descending comparators without throwing', () => {
  const layout = d3Chord()
    .padAngle(0.04)
    .sortSubgroups(descending)
    .sortChords(descending);
  const chords = layout([
    [0, 5, 1],
    [3, 0, 2],
    [4, 1, 0],
  ]);
  expect(chords.groups).toHaveLength(3);
  expect(chords.length).toBeGreaterThan(0);
  // Groups must carry finite angles so ribbon paths can be drawn.
  chords.groups.forEach((g: { startAngle: number; endAngle: number }) => {
    expect(Number.isFinite(g.startAngle)).toBe(true);
    expect(Number.isFinite(g.endAngle)).toBe(true);
    expect(g.endAngle).toBeGreaterThanOrEqual(g.startAngle);
  });
});

test('Chord does not throw on empty or malformed data payloads', () => {
  const el = document.createElement('div');
  document.body.appendChild(el);

  expect(() =>
    Chord(el, {
      width: 200,
      height: 200,
      colorScheme: 'bnbColors',
      numberFormat: '.2f',
      sliceId: 1,
      // transformProps historically fell back to [] when queries return no rows
      data: [] as unknown as { nodes: string[]; matrix: number[][] },
    }),
  ).not.toThrow();
  expect(el.querySelector('svg[data-test="chord-empty"]')).not.toBeNull();

  el.innerHTML = '';
  expect(() =>
    Chord(el, {
      width: 200,
      height: 200,
      colorScheme: 'bnbColors',
      numberFormat: '.2f',
      sliceId: 1,
      data: { nodes: [], matrix: [] },
    }),
  ).not.toThrow();
  expect(el.querySelector('svg[data-test="chord-empty"]')).not.toBeNull();

  el.remove();
});

test('Chord renders svg groups and paths with d3 v7 layout API', () => {
  const el = document.createElement('div');
  document.body.appendChild(el);

  Chord(el, {
    width: 400,
    height: 400,
    colorScheme: 'bnbColors',
    numberFormat: '.2f',
    sliceId: 1,
    data: {
      nodes: ['A', 'B', 'C'],
      matrix: [
        [0, 5, 1],
        [3, 0, 2],
        [4, 1, 0],
      ],
    },
  });

  expect(el.querySelector('svg')).not.toBeNull();
  expect(el.querySelectorAll('path.chord').length).toBeGreaterThan(0);
  expect(el.querySelectorAll('g.group').length).toBe(3);
  // Each group arc must produce a path `d` attribute from d3-shape.
  el.querySelectorAll('g.group path').forEach(path => {
    expect(path.getAttribute('d')).toBeTruthy();
  });
  el.querySelectorAll('path.chord').forEach(path => {
    expect(path.getAttribute('d')).toBeTruthy();
  });

  el.remove();
});
