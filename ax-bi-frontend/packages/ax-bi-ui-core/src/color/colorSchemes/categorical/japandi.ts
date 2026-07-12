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

/**
 * Japandi / Japanese-inspired categorical palette.
 *
 * Soft teal, moss, clay, sand, ink, and muted plum — calm multi-series
 * colors aligned with AX Office library chrome (paper + stone materials).
 * Lower chroma than rainbow defaults so charts stay scannable without
 * competing with the product shell.
 */
const schemes = [
  {
    id: 'japandiColors',
    label: 'Japandi',
    group: ColorSchemeGroup.Featured,
    // AX-BI product default: nature-connected, calm series colors.
    isDefault: true,
    colors: [
      // Full color — distinct hues, soft saturation
      '#0f766e', // soft teal (brand)
      '#2f7a5c', // moss
      '#9a6a1c', // wood amber
      '#b54a38', // clay
      '#6d5a9a', // muted violet
      '#3b5b8a', // ink blue
      '#8a6a2a', // sand gold
      '#5b6b5a', // stone green-gray
      '#7a5a4a', // warm earth
      '#4a6a7a', // quiet slate-teal
      // Pastels — same family, lighter for overflow series
      '#7db8b2',
      '#8fbfa8',
      '#d4b07a',
      '#d4a090',
      '#b5a8d0',
      '#8fa3c4',
      '#c4b090',
      '#a8b5a8',
      '#c4a898',
      '#98b0b8',
    ],
  },
].map(s => new CategoricalScheme(s));

export default schemes;
