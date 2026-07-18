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

import { useState } from 'react';
import { Button } from '../Button';
import { SettingsDrawer } from '.';
import type { SettingsDrawerProps } from '.';

export default {
  title: 'Components/SettingsDrawer',
  component: SettingsDrawer,
  parameters: {
    docs: {
      description: {
        component:
          'Right-side drawer for non-destructive authoring settings. ' +
          'Supports section tabs, preset widths, a sticky footer for ' +
          'primary actions, and a dirty guard that confirms before ' +
          'discarding unsaved changes.',
      },
    },
  },
};

// Demo sections (kept separate from args to avoid parser issues)
const demoSections = [
  {
    key: 'general',
    label: 'General',
    content: <div>General settings content</div>,
  },
  {
    key: 'refresh',
    label: 'Refresh interval',
    content: <div>Refresh interval settings content</div>,
  },
  {
    key: 'advanced',
    label: 'Advanced',
    content: <div>Advanced settings content</div>,
  },
];

export const InteractiveSettingsDrawer = (args: SettingsDrawerProps) => (
  <SettingsDrawer {...args} sections={demoSections} />
);

InteractiveSettingsDrawer.args = {
  open: true,
  title: 'Dashboard settings',
  width: 'default',
  dirty: false,
};

InteractiveSettingsDrawer.argTypes = {
  open: {
    control: 'boolean',
    description: 'Whether the drawer is visible.',
  },
  title: {
    control: 'text',
    description: 'Title displayed in the drawer header.',
  },
  width: {
    control: 'select',
    options: ['default', 'wide', 480],
    description: "Preset width ('default' | 'wide') or explicit pixel width.",
  },
  dirty: {
    control: 'boolean',
    description:
      'When true, close requests show a discard-changes confirmation.',
  },
  onClose: { action: 'onClose' },
  onSectionChange: { action: 'onSectionChange' },
  onConfirmClose: { action: 'onConfirmClose' },
};

export const WithFooterAndDirtyGuard = () => {
  const [open, setOpen] = useState(false);
  const [dirty, setDirty] = useState(true);
  return (
    <>
      <Button
        onClick={() => {
          setDirty(true);
          setOpen(true);
        }}
      >
        Open settings drawer
      </Button>
      <SettingsDrawer
        open={open}
        onClose={() => setOpen(false)}
        onConfirmClose={() => {
          setDirty(false);
          setOpen(false);
        }}
        title="Dashboard settings"
        width="default"
        sections={demoSections}
        dirty={dirty}
        footer={
          <>
            <Button buttonStyle="secondary" onClick={() => setDirty(true)}>
              Edit
            </Button>
            <Button buttonStyle="primary" onClick={() => setDirty(false)}>
              Save
            </Button>
          </>
        }
      />
    </>
  );
};

WithFooterAndDirtyGuard.parameters = {
  docs: {
    description: {
      story:
        'Footer actions plus the dirty guard: while `dirty` is true, ' +
        'closing the drawer asks for confirmation. Save clears the dirty ' +
        'state so the drawer closes without confirming.',
    },
  },
};
