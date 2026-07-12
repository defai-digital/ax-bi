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
import { pointer } from 'd3-selection';
import Partition from '../src/Partition';

const sampleTree = [
  {
    name: 'metric_a',
    val: 100,
    children: [
      {
        name: 'group_1',
        val: 60,
        children: [
          { name: 'leaf_a', val: 40 },
          { name: 'leaf_b', val: 20 },
        ],
      },
      {
        name: 'group_2',
        val: 40,
        children: [{ name: 'leaf_c', val: 40 }],
      },
    ],
  },
];

const baseProps = {
  width: 200,
  height: 150,
  colorScheme: 'bnbColors',
  dateTimeFormat: '%Y-%m-%d',
  equalDateSize: false,
  levels: [] as string[],
  metrics: [] as string[],
  numberFormat: '.2f',
  partitionLimit: 0,
  partitionThreshold: 0,
  timeSeriesOption: 'not_time',
  useLogScale: false,
  useRichTooltip: false,
  sliceId: 1,
};

test('Partition does not throw when query data is empty', () => {
  const el = document.createElement('div');
  document.body.appendChild(el);

  expect(() =>
    Partition(el, {
      ...baseProps,
      data: [],
    }),
  ).not.toThrow();
  expect(el.querySelector('svg[data-test="partition-empty"]')).not.toBeNull();

  el.remove();
});

test('Partition re-render to empty data clears stale hierarchy DOM', () => {
  const el = document.createElement('div');
  document.body.appendChild(el);

  Partition(el, {
    ...baseProps,
    width: 400,
    height: 300,
    levels: ['group'],
    metrics: ['metric_a'],
    useRichTooltip: true,
    data: sampleTree,
  });

  expect(el.querySelectorAll('rect').length).toBeGreaterThan(1);
  expect(el.querySelectorAll('text').length).toBeGreaterThan(0);
  expect(el.querySelector('.partition-tooltip')).not.toBeNull();

  // reactify re-invokes the same host element when props become empty.
  Partition(el, {
    ...baseProps,
    data: [],
  });

  expect(el.querySelector('svg[data-test="partition-empty"]')).not.toBeNull();
  expect(el.querySelectorAll('rect').length).toBe(0);
  expect(el.querySelectorAll('text').length).toBe(0);
  expect(el.querySelector('.partition-tooltip')).toBeNull();
  // Only the empty shell svg remains (no leftover chart groups).
  expect(el.querySelectorAll('svg').length).toBe(1);

  el.remove();
});

test('Partition renders hierarchical svg rects with d3 v7 scale/selection APIs', () => {
  const el = document.createElement('div');
  document.body.appendChild(el);

  Partition(el, {
    data: sampleTree,
    width: 400,
    height: 300,
    colorScheme: 'bnbColors',
    dateTimeFormat: '%Y-%m-%d',
    equalDateSize: false,
    levels: ['group'],
    metrics: ['metric_a'],
    numberFormat: '.2f',
    partitionLimit: 0,
    partitionThreshold: 0,
    timeSeriesOption: 'not_time',
    useLogScale: false,
    useRichTooltip: true,
    sliceId: 1,
  });

  expect(el.classList.contains('axbi-legacy-chart-partition')).toBe(true);
  expect(el.querySelector('svg')).not.toBeNull();
  expect(el.querySelectorAll('rect').length).toBeGreaterThan(1);
  expect(el.querySelectorAll('text').length).toBeGreaterThan(0);
  expect(el.querySelector('.partition-tooltip')).not.toBeNull();

  el.remove();
});

test('Partition pointer-based tooltip path does not throw on mouseover', () => {
  const el = document.createElement('div');
  // Offset parent geometry for pointer() in jsdom.
  Object.defineProperty(el, 'getBoundingClientRect', {
    value: () => ({
      left: 0,
      top: 0,
      right: 400,
      bottom: 300,
      width: 400,
      height: 300,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    }),
  });
  document.body.appendChild(el);

  Partition(el, {
    data: sampleTree,
    width: 400,
    height: 300,
    colorScheme: 'bnbColors',
    dateTimeFormat: '%Y-%m-%d',
    equalDateSize: false,
    levels: ['group'],
    metrics: ['metric_a'],
    numberFormat: '.2f',
    partitionLimit: 0,
    partitionThreshold: 0,
    timeSeriesOption: 'not_time',
    useLogScale: false,
    useRichTooltip: false,
    sliceId: 1,
  });

  const node = el.querySelector('g');
  expect(node).not.toBeNull();

  const event = new MouseEvent('mouseover', {
    clientX: 40,
    clientY: 50,
    bubbles: true,
  });
  expect(() => node!.dispatchEvent(event)).not.toThrow();

  // Sanity: d3-selection pointer is the module Partition uses for tip position.
  const [px, py] = pointer(event, el);
  expect(Number.isFinite(px)).toBe(true);
  expect(Number.isFinite(py)).toBe(true);

  el.remove();
});
