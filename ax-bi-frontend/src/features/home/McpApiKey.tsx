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
import { useEffect, useRef, useState } from 'react';
import { t } from '@ax-bi/core/translation';
import { css, styled } from '@ax-bi/core/theme';
import { AxBIClient } from '@ax-bi/ui-core';
import { Button, Icons, Tooltip } from '@ax-bi/ui-core/components';
import { useToasts } from 'src/components/MessageToasts/withToasts';
import copyTextToClipboard from 'src/utils/copy';

const API_KEY_ENDPOINT = '/api/v1/security/api_keys/';
const MANAGED_MCP_KEY_NAME = 'AX BI MCP';
const MASK = '**********';

interface McpApiKeyRecord {
  uuid: string;
  name: string;
  key_prefix: string;
  active: boolean;
  created_on: string;
  expires_on: string | null;
  revoked_on: string | null;
}

interface CreatedMcpApiKey {
  uuid: string;
  name: string;
  key: string;
  key_prefix: string;
  created_on: string;
  expires_on: string | null;
}

interface McpApiKeyProps {
  username: string;
}

const StyledMcpKey = styled.div`
  ${({ theme }) => css`
    align-items: flex-start;
    border-left: 1px solid ${theme.colorBorderSecondary};
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    justify-content: center;
    margin-left: ${theme.sizeUnit * 2}px;
    min-width: ${theme.sizeUnit * 60}px;
    padding-left: ${theme.sizeUnit * 3}px;

    .mcp-username {
      color: ${theme.colorText};
      font-size: ${theme.fontSizeSM}px;
      font-weight: ${theme.fontWeightStrong};
      line-height: 1.2;
      max-width: ${theme.sizeUnit * 57}px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .mcp-key-row {
      align-items: center;
      color: ${theme.colorTextSecondary};
      display: flex;
      font-size: ${theme.fontSizeSM}px;
      line-height: 1.2;
      white-space: nowrap;
    }

    code {
      background: transparent;
      color: inherit;
      font-size: inherit;
      min-width: ${theme.sizeUnit * 45}px;
      padding: 0;
    }

    button {
      height: ${theme.sizeUnit * 5}px;
      margin-left: ${theme.sizeUnit}px;
      min-width: ${theme.sizeUnit * 5}px;
      padding: 0;
    }

    @media (max-width: 1127px) {
      display: none;
    }
  `}
`;

export function formatMcpApiKeyHint(value: string): string {
  const leading = value.slice(0, 4) || '----';
  const trailing = value.length >= 9 ? value.slice(-5) : '?????';
  return `${leading}-${MASK}-${trailing}`;
}

function isUsableManagedKey(key: McpApiKeyRecord): boolean {
  if (key.name !== MANAGED_MCP_KEY_NAME || !key.active || key.revoked_on) {
    return false;
  }
  return !key.expires_on || new Date(key.expires_on) > new Date();
}

async function listManagedKeys(): Promise<McpApiKeyRecord[]> {
  const response = await AxBIClient.get({ endpoint: API_KEY_ENDPOINT });
  return ((response.json?.result || []) as unknown as McpApiKeyRecord[])
    .filter(isUsableManagedKey)
    .sort(
      (left, right) =>
        new Date(right.created_on).getTime() -
        new Date(left.created_on).getTime(),
    );
}

async function createManagedKey(): Promise<CreatedMcpApiKey> {
  const response = await AxBIClient.post({
    endpoint: API_KEY_ENDPOINT,
    jsonPayload: { name: MANAGED_MCP_KEY_NAME },
  });
  const created = response.json?.result as unknown as CreatedMcpApiKey;
  if (!created?.uuid || !created.key || !created.key_prefix) {
    throw new Error('API response did not include the created MCP key');
  }
  return created;
}

function createdKeyMetadata(created: CreatedMcpApiKey): McpApiKeyRecord {
  return {
    uuid: created.uuid,
    name: created.name,
    key_prefix: created.key_prefix,
    active: true,
    created_on: created.created_on,
    expires_on: created.expires_on,
    revoked_on: null,
  };
}

async function revokeKey(uuid: string): Promise<void> {
  await AxBIClient.delete({ endpoint: `${API_KEY_ENDPOINT}${uuid}` });
}

export function McpApiKey({ username }: McpApiKeyProps) {
  const { addDangerToast, addSuccessToast } = useToasts();
  const initializedRef = useRef(false);
  const [currentKey, setCurrentKey] = useState<McpApiKeyRecord | null>(null);
  const [rotating, setRotating] = useState(false);

  useEffect(() => {
    if (initializedRef.current) {
      return undefined;
    }
    initializedRef.current = true;
    let active = true;

    const initializeKey = async () => {
      try {
        const [existingKey] = await listManagedKeys();
        const key = existingKey ?? createdKeyMetadata(await createManagedKey());
        if (active) {
          setCurrentKey(key);
        }
      } catch {
        if (active) {
          addDangerToast(t('Failed to prepare your MCP key'));
        }
      }
    };

    initializeKey();
    return () => {
      active = false;
    };
  }, [addDangerToast]);

  const rotateAndCopy = async () => {
    if (rotating) {
      return;
    }
    setRotating(true);

    try {
      const oldKeys = await listManagedKeys();
      const newKey = await createManagedKey();

      try {
        await copyTextToClipboard(() => Promise.resolve(newKey.key));
      } catch {
        await revokeKey(newKey.uuid).catch(() => undefined);
        throw new Error('Could not copy the new MCP key');
      }

      setCurrentKey(createdKeyMetadata(newKey));
      const revocations = await Promise.allSettled(
        oldKeys
          .filter(key => key.uuid !== newKey.uuid)
          .map(key => revokeKey(key.uuid)),
      );
      if (revocations.some(result => result.status === 'rejected')) {
        addDangerToast(
          t('New MCP key copied, but a previous key could not be revoked'),
        );
      } else {
        addSuccessToast(t('New MCP key copied; the previous key was revoked'));
      }
    } catch {
      addDangerToast(t('Failed to generate and copy a new MCP key'));
    } finally {
      setRotating(false);
    }
  };

  const actionLabel = t(
    'Generate and copy a new MCP key. The previous key will stop working.',
  );

  return (
    <StyledMcpKey data-test="mcp-api-key">
      <span className="mcp-username" title={username}>
        {username}
      </span>
      <span className="mcp-key-row">
        <code data-test="mcp-api-key-hint">
          {currentKey
            ? formatMcpApiKeyHint(currentKey.key_prefix)
            : t('MCP key…')}
        </code>
        <Tooltip title={actionLabel}>
          <Button
            aria-label={actionLabel}
            disabled={!currentKey}
            loading={rotating}
            onClick={rotateAndCopy}
            size="small"
            type="text"
            icon={<Icons.EyeOutlined iconSize="s" />}
          />
        </Tooltip>
      </span>
    </StyledMcpKey>
  );
}
