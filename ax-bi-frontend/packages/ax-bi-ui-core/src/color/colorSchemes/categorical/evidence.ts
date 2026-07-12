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

import CategoricalScheme from '../../CategoricalScheme';
import { ColorSchemeGroup } from '../../types';

// Muted, desaturated categorical palette adapted from Evidence.dev's default
// chart theme. The lower saturation keeps multi-series charts legible and
// reduces visual noise compared with fully saturated palettes.
const schemes = [
  {
    id: 'evidence',
    label: 'Evidence',
    group: ColorSchemeGroup.Featured,
    // Muted and consistent-chroma by design, unlike the fully-saturated
    // "AxBI Colors" baseline. Product default is japandiColors.
    colors: [
      '#236aa4',
      '#45a1bf',
      '#a5cdee',
      '#8dacbf',
      '#85c7c6',
      '#d2c6ac',
      '#f4b548',
      '#8f3d56',
      '#71b9f4',
      '#46a485',
    ],
  },
].map(s => new CategoricalScheme(s));

export default schemes;
