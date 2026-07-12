/*
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
  CategoricalAirbnb,
  CategoricalD3,
  CategoricalEcharts,
  CategoricalGoogle,
  CategoricalLyft,
  CategoricalPreset,
  CategoricalAxBI,
  SequentialCommon,
  SequentialD3,
} from '@ax-bi/ui-core';
import RenderPalettes from './RenderPalettes';

export default {
  title: 'Core Packages/@ax-bi/ui-core/color',
};

export const categoricalPalettes = () =>
  [
    { palettes: CategoricalAxBI, storyName: 'AxBI' },
    { palettes: CategoricalAirbnb, storyName: 'Airbnb' },
    { palettes: CategoricalD3, storyName: 'd3' },
    { palettes: CategoricalEcharts, storyName: 'ECharts' },
    { palettes: CategoricalGoogle, storyName: 'Google' },
    { palettes: CategoricalLyft, storyName: 'Lyft' },
    { palettes: CategoricalPreset, storyName: 'Preset' },
  ].map(({ palettes, storyName }) => (
    <RenderPalettes key={storyName} title={storyName} palettes={palettes} />
  ));

export const sequentialPalettes = () =>
  [
    { palettes: SequentialCommon, storyName: 'Common' },
    { palettes: SequentialD3, storyName: 'd3' },
  ].map(({ palettes, storyName }) => (
    <RenderPalettes key={storyName} title={storyName} palettes={palettes} />
  ));
