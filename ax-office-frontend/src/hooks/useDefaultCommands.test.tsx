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
import { useEffect } from 'react';
import { FeatureFlag } from '@superset-ui/core';
import { render, waitFor } from 'spec/helpers/testing-library';
import {
  Command,
  CommandPaletteProvider,
  useCommandPalette,
} from 'src/components/CommandPalette';
import { useDefaultCommands } from './useDefaultCommands';

interface CommandProbeProps {
  onCommands: (commands: Command[]) => void;
}

const CommandProbe = ({ onCommands }: CommandProbeProps) => {
  useDefaultCommands();
  const { getCommands } = useCommandPalette();

  useEffect(() => {
    onCommands(getCommands());
  }, [getCommands, onCommands]);

  return null;
};

const renderCommandProbe = (canUploadData: boolean) => {
  const onCommands = jest.fn();

  render(
    <CommandPaletteProvider>
      <CommandProbe onCommands={onCommands} />
    </CommandPaletteProvider>,
    {
      useRedux: true,
      useRouter: true,
      initialState: {
        user: {
          roles: canUploadData
            ? { Alpha: [['can_upload', 'Database']] }
            : { Gamma: [['can_read', 'Database']] },
        },
      },
    },
  );

  return onCommands;
};

const getLatestCommandIds = (onCommands: jest.Mock) => {
  const calls = onCommands.mock.calls as [Command[]][];
  return calls.at(-1)?.[0].map(command => command.id) ?? [];
};

beforeEach(() => {
  window.featureFlags = {};
});

test('registers upload data command when local upload is enabled and permitted', async () => {
  window.featureFlags = { [FeatureFlag.EnableLocalFileUpload]: true };
  const onCommands = renderCommandProbe(true);

  await waitFor(() => {
    expect(getLatestCommandIds(onCommands)).toContain('action-upload-data');
  });
});

test('does not register upload data command without local upload permission', async () => {
  window.featureFlags = { [FeatureFlag.EnableLocalFileUpload]: true };
  const onCommands = renderCommandProbe(false);

  await waitFor(() => {
    expect(getLatestCommandIds(onCommands)).toContain('action-new-dashboard');
  });
  expect(getLatestCommandIds(onCommands)).not.toContain('action-upload-data');
});

test('does not register upload data command when local upload is disabled', async () => {
  const onCommands = renderCommandProbe(true);

  await waitFor(() => {
    expect(getLatestCommandIds(onCommands)).toContain('action-new-dashboard');
  });
  expect(getLatestCommandIds(onCommands)).not.toContain('action-upload-data');
});
