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
import Chord from '../src/Chord';

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
      nodes: ['A', 'B'],
      matrix: [
        [0, 5],
        [3, 0],
      ],
    },
  });

  expect(el.querySelector('svg')).not.toBeNull();
  expect(el.querySelectorAll('path.chord').length).toBeGreaterThan(0);
  expect(el.querySelectorAll('g.group').length).toBe(2);

  el.remove();
});
