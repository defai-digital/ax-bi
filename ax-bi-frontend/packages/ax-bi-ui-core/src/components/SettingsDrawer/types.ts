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
import type { ReactNode } from 'react';

/**
 * Preset widths ('default' | 'wide') resolve to theme-token-based pixel
 * values; a number is passed through as an explicit pixel width.
 */
export type SettingsDrawerWidth = 'default' | 'wide' | number;

export interface SettingsDrawerSection {
  key: string;
  label: ReactNode;
  content: ReactNode;
}

export interface SettingsDrawerProps {
  /** Whether the drawer is visible. */
  open: boolean;
  /**
   * Called when the drawer requests to close (close button, mask click,
   * Escape) and the dirty guard does not intercept it.
   */
  onClose: () => void;
  /** Title rendered in the drawer header. */
  title: ReactNode;
  /** Preset width or explicit pixel width. Defaults to 'default'. */
  width?: SettingsDrawerWidth;
  /**
   * Optional sections rendered as left-hand tabs inside the drawer body.
   * When omitted, `children` is rendered as the drawer body instead.
   */
  sections?: SettingsDrawerSection[];
  /** Controlled active section key. Omit for uncontrolled (first section). */
  activeSection?: string;
  /** Called with the section key whenever the user switches sections. */
  onSectionChange?: (sectionKey: string) => void;
  /** Sticky footer area for primary actions, rendered right-aligned. */
  footer?: ReactNode;
  /**
   * When true, any close request opens a discard-changes confirmation
   * instead of closing the drawer.
   */
  dirty?: boolean;
  /**
   * Called when the user confirms closing while `dirty` is true.
   * Falls back to `onClose` when not provided.
   */
  onConfirmClose?: () => void;
  /** Drawer body content when `sections` is not provided. */
  children?: ReactNode;
  /**
   * Test id forwarded to the antd Drawer (lands on the drawer content
   * wrapper), so E2E suites can scope queries inside the drawer the same
   * way they scoped the legacy modal wrappers.
   */
  'data-test'?: string;
}
