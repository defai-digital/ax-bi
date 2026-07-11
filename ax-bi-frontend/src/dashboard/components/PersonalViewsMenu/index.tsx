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
import { useCallback, useMemo, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { t } from '@apache-superset/core/translation';
import { MenuItem } from '@superset-ui/core/components/Menu';
import { DataMaskStateWithId } from '@superset-ui/core';
import { RootState } from 'src/dashboard/types';
import { updateDataMask } from 'src/dataMask/actions';
import {
  deletePersonalView,
  filterDataMaskToKnownIds,
  loadPersonalViewsStore,
  PersonalView,
  savePersonalView,
} from 'src/dashboard/util/personalViews';

export interface UsePersonalViewsMenuItemsArgs {
  dashboardId: number | string;
  userId?: number | string | null;
  editMode: boolean;
  addSuccessToast: (msg: string) => void;
  addDangerToast: (msg: string) => void;
}

/**
 * Builds a "My views" submenu for the dashboard header (view mode only).
 * Stores personal filter state in localStorage — does not mutate shared metadata.
 */
export function usePersonalViewsMenuItems({
  dashboardId,
  userId,
  editMode,
  addSuccessToast,
  addDangerToast,
}: UsePersonalViewsMenuItemsArgs): MenuItem | null {
  const dispatch = useDispatch();
  const dataMask = useSelector<RootState, DataMaskStateWithId>(
    state => state.dataMask,
  );
  const nativeFilters = useSelector(
    (state: RootState) => state.nativeFilters?.filters ?? {},
  );
  const [revision, setRevision] = useState(0);
  const refresh = useCallback(() => setRevision(x => x + 1), []);

  const applyView = useCallback(
    (view: PersonalView) => {
      const known = new Set(Object.keys(nativeFilters).map(String));
      const filtered = filterDataMaskToKnownIds(view.dataMask, known);
      Object.entries(filtered).forEach(([filterId, mask]) => {
        dispatch(updateDataMask(filterId, mask));
      });
      addSuccessToast(t('Applied view “%s”', view.name));
    },
    [addSuccessToast, dispatch, nativeFilters],
  );

  return useMemo(() => {
    if (editMode || userId == null || userId === '') {
      return null;
    }

    const store = loadPersonalViewsStore(userId, dashboardId);

    const children: MenuItem[] = [
      {
        key: 'personal-view-save',
        label: t('Save current filters as view'),
        onClick: () => {
          const name =
            window.prompt(t('Name this view'), t('My view')) ?? '';
          if (!name.trim()) {
            return;
          }
          try {
            savePersonalView(userId, dashboardId, name, dataMask);
            addSuccessToast(t('Saved personal view “%s”', name.trim()));
            refresh();
          } catch {
            addDangerToast(t('Could not save personal view'));
          }
        },
      },
    ];

    if (store.views.length) {
      children.push({ type: 'divider' });
      store.views.forEach(view => {
        children.push({
          key: `personal-view-load-${view.id}`,
          label: view.name,
          onClick: () => applyView(view),
        });
      });
      children.push({ type: 'divider' });
      store.views.forEach(view => {
        children.push({
          key: `personal-view-delete-${view.id}`,
          label: t('Delete “%s”', view.name),
          danger: true,
          onClick: () => {
            deletePersonalView(userId, dashboardId, view.id);
            addSuccessToast(t('Deleted view “%s”', view.name));
            refresh();
          },
        });
      });
    }

    return {
      key: 'personal-views',
      label: t('My views'),
      children,
    };
  }, [
    addDangerToast,
    addSuccessToast,
    applyView,
    dashboardId,
    dataMask,
    editMode,
    refresh,
    revision,
    userId,
  ]);
}

export default usePersonalViewsMenuItems;
