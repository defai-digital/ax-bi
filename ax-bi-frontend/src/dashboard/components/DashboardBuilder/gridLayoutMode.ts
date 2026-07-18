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
import { createContext, useContext } from 'react';

// Below this container width the dashboard renders as a read-only
// single-column stack of charts with authoring chrome hidden.
export const DASHBOARD_GRID_STACK_BREAKPOINT = 768;
// Below this container width the grid columns compress proportionally
// to fit the available space instead of keeping their desktop widths.
export const DASHBOARD_GRID_COMPACT_BREAKPOINT = 1200;

export type DashboardGridLayoutMode = 'standard' | 'compact' | 'stack';

export type GridLayoutModeInput = {
  // DASHBOARD_RESPONSIVE feature flag
  responsiveEnabled: boolean;
  // Authoring stays desktop-first; edit mode never reflows
  editMode: boolean;
};

export const getGridLayoutMode = (
  width: number,
  { responsiveEnabled, editMode }: GridLayoutModeInput,
): DashboardGridLayoutMode => {
  // An unmeasured container (width 0, e.g. before the first ResizeObserver
  // tick) keeps the legacy layout to avoid a reflow flash on wide screens.
  if (!responsiveEnabled || editMode || width <= 0) {
    return 'standard';
  }
  if (width < DASHBOARD_GRID_STACK_BREAKPOINT) {
    return 'stack';
  }
  if (width < DASHBOARD_GRID_COMPACT_BREAKPOINT) {
    return 'compact';
  }
  return 'standard';
};

export const DashboardGridLayoutContext =
  createContext<DashboardGridLayoutMode>('standard');

export const useDashboardGridLayoutMode = (): DashboardGridLayoutMode =>
  useContext(DashboardGridLayoutContext);
