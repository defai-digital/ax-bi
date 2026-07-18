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
import { render, screen, userEvent, waitFor } from '@ax-bi/ui-core/spec';
import { SettingsDrawer } from '.';

const defaultProps = {
  open: true,
  onClose: jest.fn(),
  title: 'Dashboard settings',
};

const defaultSections = [
  {
    key: 'general',
    label: 'General',
    content: <div>General section content</div>,
  },
  {
    key: 'refresh',
    label: 'Refresh interval',
    content: <div>Refresh section content</div>,
  },
];

test('renders title and children when open', () => {
  render(
    <SettingsDrawer {...defaultProps}>
      <div>Plain drawer body</div>
    </SettingsDrawer>,
  );

  expect(screen.getByText('Dashboard settings')).toBeInTheDocument();
  expect(screen.getByText('Plain drawer body')).toBeInTheDocument();
});

test('does not render content when closed', () => {
  render(
    <SettingsDrawer {...defaultProps} open={false}>
      <div>Plain drawer body</div>
    </SettingsDrawer>,
  );

  expect(screen.queryByText('Dashboard settings')).not.toBeInTheDocument();
  expect(screen.queryByText('Plain drawer body')).not.toBeInTheDocument();
});

test('renders sections as tabs with the first section active by default', () => {
  render(<SettingsDrawer {...defaultProps} sections={defaultSections} />);

  expect(screen.getByRole('tab', { name: 'General' })).toBeInTheDocument();
  expect(
    screen.getByRole('tab', { name: 'Refresh interval' }),
  ).toBeInTheDocument();
  expect(screen.getByText('General section content')).toBeInTheDocument();
  expect(screen.queryByText('Refresh section content')).not.toBeInTheDocument();
});

test('switches sections and notifies onSectionChange', () => {
  const onSectionChange = jest.fn();
  render(
    <SettingsDrawer
      {...defaultProps}
      sections={defaultSections}
      onSectionChange={onSectionChange}
    />,
  );

  userEvent.click(screen.getByRole('tab', { name: 'Refresh interval' }));

  expect(onSectionChange).toHaveBeenCalledWith('refresh');
  expect(screen.getByText('Refresh section content')).toBeInTheDocument();
});

test('respects controlled activeSection', () => {
  const onSectionChange = jest.fn();
  render(
    <SettingsDrawer
      {...defaultProps}
      sections={defaultSections}
      activeSection="refresh"
      onSectionChange={onSectionChange}
    />,
  );

  expect(screen.getByText('Refresh section content')).toBeInTheDocument();

  // Controlled: clicking another tab notifies but does not switch
  userEvent.click(screen.getByRole('tab', { name: 'General' }));
  expect(onSectionChange).toHaveBeenCalledWith('general');
  expect(screen.getByText('Refresh section content')).toBeInTheDocument();
});

test('calls onClose on close button click when not dirty', () => {
  const onClose = jest.fn();
  render(
    <SettingsDrawer {...defaultProps} onClose={onClose}>
      <div>Plain drawer body</div>
    </SettingsDrawer>,
  );

  userEvent.click(screen.getByRole('button', { name: 'Close' }));

  expect(onClose).toHaveBeenCalledTimes(1);
});

test('dirty guard shows confirm instead of closing', () => {
  const onClose = jest.fn();
  render(
    <SettingsDrawer {...defaultProps} onClose={onClose} dirty>
      <div>Plain drawer body</div>
    </SettingsDrawer>,
  );

  userEvent.click(screen.getByRole('button', { name: 'Close' }));

  expect(onClose).not.toHaveBeenCalled();
  expect(screen.getByText('Unsaved changes')).toBeInTheDocument();
  // Drawer stays open behind the confirm
  expect(screen.getByText('Plain drawer body')).toBeInTheDocument();
});

test('dirty guard confirm calls onConfirmClose when provided', () => {
  const onClose = jest.fn();
  const onConfirmClose = jest.fn();
  render(
    <SettingsDrawer
      {...defaultProps}
      onClose={onClose}
      onConfirmClose={onConfirmClose}
      dirty
    >
      <div>Plain drawer body</div>
    </SettingsDrawer>,
  );

  userEvent.click(screen.getByRole('button', { name: 'Close' }));
  userEvent.click(screen.getByRole('button', { name: 'Discard' }));

  expect(onConfirmClose).toHaveBeenCalledTimes(1);
  expect(onClose).not.toHaveBeenCalled();
});

test('dirty guard confirm falls back to onClose without onConfirmClose', () => {
  const onClose = jest.fn();
  render(
    <SettingsDrawer {...defaultProps} onClose={onClose} dirty>
      <div>Plain drawer body</div>
    </SettingsDrawer>,
  );

  userEvent.click(screen.getByRole('button', { name: 'Close' }));
  userEvent.click(screen.getByRole('button', { name: 'Discard' }));

  expect(onClose).toHaveBeenCalledTimes(1);
});

test('dirty guard cancel keeps the drawer open', async () => {
  const onClose = jest.fn();
  render(
    <SettingsDrawer {...defaultProps} onClose={onClose} dirty>
      <div>Plain drawer body</div>
    </SettingsDrawer>,
  );

  userEvent.click(screen.getByRole('button', { name: 'Close' }));
  userEvent.click(screen.getByRole('button', { name: 'Keep editing' }));

  expect(onClose).not.toHaveBeenCalled();
  await waitFor(() =>
    expect(screen.queryByText('Unsaved changes')).not.toBeVisible(),
  );
  expect(screen.getByText('Plain drawer body')).toBeInTheDocument();
});

test('renders footer actions', () => {
  render(
    <SettingsDrawer
      {...defaultProps}
      footer={<button type="button">Apply</button>}
    >
      <div>Plain drawer body</div>
    </SettingsDrawer>,
  );

  expect(screen.getByRole('button', { name: 'Apply' })).toBeInTheDocument();
});

test('applies explicit pixel width', () => {
  render(
    <SettingsDrawer {...defaultProps} width={320}>
      <div>Plain drawer body</div>
    </SettingsDrawer>,
  );

  const wrapper = document.querySelector(
    '.ant-drawer-content-wrapper',
  ) as HTMLElement;
  expect(wrapper).toHaveStyle('width: 320px');
});
