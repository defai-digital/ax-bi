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
import { VizType } from '@ax-bi/ui-core';

/**
 * nvd3-era legacy chart types registered by MainPreset from the
 * `@ax-bi/legacy-plugin-chart-*` and `@ax-bi/legacy-preset-chart-nvd3`
 * packages.
 *
 * The plugins stay registered at all times so existing saved charts keep
 * rendering and editing; when the LEGACY_CHART_PLUGINS feature flag is off
 * these types are only hidden from the viz gallery picker.
 */
export const LEGACY_VIZ_TYPES: string[] = [
  VizType.LegacyBubble,
  VizType.Bullet,
  VizType.Calendar,
  VizType.Chord,
  VizType.Compare,
  VizType.CountryMap,
  VizType.Horizon,
  VizType.PairedTTest,
  VizType.ParallelCoordinates,
  VizType.Partition,
  VizType.Rose,
  VizType.TimePivot,
  VizType.WorldMap,
];
