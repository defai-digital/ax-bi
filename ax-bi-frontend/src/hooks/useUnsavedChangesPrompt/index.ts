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
import { useHistory } from 'src/hooks/useAppHistory';
import { t } from '@ax-bi/core/translation';
import { getClientErrorObject } from '@ax-bi/ui-core';
import { useEffect, useRef, useCallback, useState } from 'react';
import { useBeforeUnload } from 'src/hooks/useBeforeUnload';
import type { Action, Transition } from 'history';

type UseUnsavedChangesPromptProps = {
  hasUnsavedChanges: boolean;
  onSave: () => Promise<void> | void;
  isSaveModalVisible?: boolean;
  manualSaveOnUnsavedChanges?: boolean;
};

/**
 * history v5 always blocks when a blocker is registered and invokes the
 * blocker with a single Transition (`{ action, location, retry }`). Returning
 * true/false from the blocker is ignored — allowed transitions must
 * `unblock()` then `retry()`, then re-install the blocker when still dirty.
 */
function isReplaceAction(action: Action): boolean {
  return action === 'REPLACE';
}

export const useUnsavedChangesPrompt = ({
  hasUnsavedChanges,
  onSave,
  isSaveModalVisible = false,
  manualSaveOnUnsavedChanges = false,
}: UseUnsavedChangesPromptProps) => {
  const history = useHistory();
  const [showModal, setShowModal] = useState(false);

  const confirmNavigationRef = useRef<(() => void) | null>(null);
  const unblockRef = useRef<() => void>(() => {});
  const manualSaveRef = useRef(false); // Track if save was user-initiated (not via navigation)
  const hasUnsavedChangesRef = useRef(hasUnsavedChanges);
  hasUnsavedChangesRef.current = hasUnsavedChanges;

  // Stable installer so the Transition callback can re-block after allow+retry.
  const installBlockerRef = useRef<() => void>(() => {});

  const handleConfirmNavigation = useCallback(() => {
    setShowModal(false);
    confirmNavigationRef.current?.();
  }, []);

  const handleSaveAndCloseModal = useCallback(async () => {
    try {
      if (manualSaveOnUnsavedChanges) manualSaveRef.current = true;

      await onSave();
      setShowModal(false);
    } catch (err) {
      const clientError = await getClientErrorObject(err);
      throw new Error(
        clientError.message ||
          clientError.error ||
          t('Sorry, an error occurred'),
        { cause: err },
      );
    }
  }, [manualSaveOnUnsavedChanges, onSave]);

  const triggerManualSave = useCallback(() => {
    manualSaveRef.current = true;
    onSave();
  }, [onSave]);

  const onBlockTransition = useCallback((tx: Transition) => {
    const { action, retry } = tx;

    const allowAndRetry = () => {
      unblockRef.current?.();
      retry();
      if (hasUnsavedChangesRef.current) {
        installBlockerRef.current();
      }
    };

    // REPLACE actions are URL sync (e.g. updating form_data_key), not leave.
    if (isReplaceAction(action)) {
      allowAndRetry();
      return;
    }

    if (manualSaveRef.current) {
      manualSaveRef.current = false;
      allowAndRetry();
      return;
    }

    // Hold navigation until the user confirms discard (or save elsewhere).
    confirmNavigationRef.current = () => {
      unblockRef.current?.();
      retry();
      // Leaving the page typically clears dirty state; if still dirty, re-block.
      if (hasUnsavedChangesRef.current) {
        installBlockerRef.current();
      }
    };

    setShowModal(true);
  }, []);

  installBlockerRef.current = () => {
    unblockRef.current = history.block(onBlockTransition);
  };

  useEffect(() => {
    if (!hasUnsavedChanges) return undefined;

    installBlockerRef.current();
    return () => {
      unblockRef.current?.();
    };
  }, [hasUnsavedChanges, history, onBlockTransition]);

  useEffect(() => {
    if (!isSaveModalVisible && manualSaveRef.current) {
      setShowModal(false);
      manualSaveRef.current = false;
    }
  }, [isSaveModalVisible]);

  useBeforeUnload(hasUnsavedChanges);

  return {
    showModal,
    setShowModal,
    handleConfirmNavigation,
    handleSaveAndCloseModal,
    triggerManualSave,
  };
};
