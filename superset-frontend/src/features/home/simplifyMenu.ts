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
import {
  MenuObjectChildProps,
  MenuObjectProps,
} from 'src/types/bootstrapTypes';

/**
 * Simplified Navigation (SIMPLIFIED_NAV feature flag).
 *
 * Pure, framework-free helpers that reshape the already-built top navigation so
 * that power-user destinations are relocated out of the primary nav bar into a
 * grouped "Advanced" submenu. This is presentation-only: items reaching these
 * helpers have already passed Flask-AppBuilder permission filtering, so
 * relocation cannot widen access (a user without `can_sqllab` has no SQL item to
 * demote). See ax-docs/ux-simplification-tech-spec.md.
 */

// Stable identifiers (FAB `name`/category and `category_label`) of the
// top-level nav items that should be demoted in simplified mode. The SQL group
// is registered with category="SQL Lab" / category_label="SQL"
// (superset/initialization/__init__.py), so we match either to be resilient to
// translation and to which field the bootstrap payload carries.
export const DEMOTED_NAV_IDENTIFIERS: ReadonlySet<string> = new Set([
  'SQL Lab',
  'SQL',
]);

const isDemoted = (item: MenuObjectProps): boolean =>
  (!!item.name && DEMOTED_NAV_IDENTIFIERS.has(item.name)) ||
  (!!item.label && DEMOTED_NAV_IDENTIFIERS.has(item.label));

/**
 * Partition the primary nav into the items that remain in the top bar and the
 * items that are demoted. When `enabled` is false, the input is returned
 * unchanged with no demoted items, guaranteeing zero behavior change while the
 * flag is off. No item is ever dropped: `menu ∪ demoted` equals the input.
 */
export function simplifyMenuData(
  menu: MenuObjectProps[],
  enabled: boolean,
): { menu: MenuObjectProps[]; demoted: MenuObjectProps[] } {
  if (!enabled) {
    return { menu, demoted: [] };
  }

  const kept: MenuObjectProps[] = [];
  const demoted: MenuObjectProps[] = [];
  menu.forEach(item => {
    if (isDemoted(item)) {
      demoted.push(item);
    } else {
      kept.push(item);
    }
  });

  return { menu: kept, demoted };
}

/**
 * Flatten the children of demoted top-level items into a single list of leaf
 * menu entries suitable for a Settings-style group. String entries (dividers)
 * are dropped; a demoted item with no children contributes itself as a leaf so
 * its destination stays reachable.
 */
export function flattenChilds(
  demoted: MenuObjectProps[],
): MenuObjectChildProps[] {
  const leaves: MenuObjectChildProps[] = [];
  demoted.forEach(item => {
    const objectChilds = (item.childs ?? []).filter(
      (child): child is MenuObjectChildProps => typeof child !== 'string',
    );
    if (objectChilds.length) {
      leaves.push(...objectChilds);
    } else {
      // A demoted item with no object children stays reachable as its own leaf.
      const leaf: MenuObjectChildProps = { ...item };
      delete (leaf as { childs?: unknown }).childs;
      leaves.push(leaf);
    }
  });
  return leaves;
}
