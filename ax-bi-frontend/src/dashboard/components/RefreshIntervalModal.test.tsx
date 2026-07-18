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
import { render, screen, userEvent } from 'spec/helpers/testing-library';
import RefreshIntervalModal from './RefreshIntervalModal';

const defaultProps = {
  show: true,
  onHide: jest.fn(),
  refreshFrequency: 0,
  onChange: jest.fn(),
  editMode: false,
  addSuccessToast: jest.fn(),
  pauseOnInactiveTab: false,
  onPauseOnInactiveTabChange: jest.fn(),
};

const initialState = {
  dashboardInfo: {
    common: {
      conf: {},
    },
  },
};

const setup = (props: Partial<typeof defaultProps> = {}) =>
  render(<RefreshIntervalModal {...defaultProps} {...props} />, {
    useRedux: true,
    initialState,
  });

beforeEach(() => {
  jest.clearAllMocks();
  window.featureFlags = {};
});

test('renders as a modal when SETTINGS_DRAWER is disabled', () => {
  setup();

  expect(screen.getByText('Refresh interval')).toBeInTheDocument();
  expect(screen.getByRole('dialog')).toBeInTheDocument();
  expect(
    document.querySelector('.ant-drawer-content-wrapper'),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole('button', { name: 'Save for this session' }),
  ).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
});

test('saves from the modal footer when SETTINGS_DRAWER is disabled', () => {
  setup();

  userEvent.click(
    screen.getByRole('button', { name: 'Save for this session' }),
  );

  expect(defaultProps.onChange).toHaveBeenCalledWith(0, false);
  expect(defaultProps.onPauseOnInactiveTabChange).toHaveBeenCalledWith(false);
  expect(defaultProps.onHide).toHaveBeenCalledTimes(1);
  expect(defaultProps.addSuccessToast).toHaveBeenCalledWith(
    'Refresh interval set for this session',
  );
});

test('renders as a drawer when SETTINGS_DRAWER is enabled', () => {
  window.featureFlags = { SETTINGS_DRAWER: true };
  setup();

  expect(screen.getByText('Refresh interval')).toBeInTheDocument();
  expect(
    document.querySelector('.ant-drawer-content-wrapper'),
  ).toBeInTheDocument();
  expect(document.querySelector('.ant-modal')).not.toBeInTheDocument();
  expect(
    screen.getByRole('button', { name: 'Save for this session' }),
  ).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
});

test('saves from the drawer footer when SETTINGS_DRAWER is enabled', () => {
  window.featureFlags = { SETTINGS_DRAWER: true };
  setup({ refreshFrequency: 10 });

  userEvent.click(screen.getByText('30 seconds'));
  userEvent.click(
    screen.getByRole('button', { name: 'Save for this session' }),
  );

  expect(defaultProps.onChange).toHaveBeenCalledWith(30, false);
  expect(defaultProps.onPauseOnInactiveTabChange).toHaveBeenCalledWith(false);
  expect(defaultProps.onHide).toHaveBeenCalledTimes(1);
  expect(defaultProps.addSuccessToast).toHaveBeenCalledWith(
    'Refresh interval set for this session',
  );
});

test('cancels from the drawer footer when SETTINGS_DRAWER is enabled', () => {
  window.featureFlags = { SETTINGS_DRAWER: true };
  setup();

  userEvent.click(screen.getByRole('button', { name: 'Cancel' }));

  expect(defaultProps.onHide).toHaveBeenCalledTimes(1);
  expect(defaultProps.onChange).not.toHaveBeenCalled();
  expect(defaultProps.addSuccessToast).not.toHaveBeenCalled();
});

test('closes via the drawer close button when SETTINGS_DRAWER is enabled', () => {
  window.featureFlags = { SETTINGS_DRAWER: true };
  setup();

  userEvent.click(screen.getByRole('button', { name: 'Close' }));

  expect(defaultProps.onHide).toHaveBeenCalledTimes(1);
  expect(defaultProps.onChange).not.toHaveBeenCalled();
});

test('uses the edit mode save label in the drawer', () => {
  window.featureFlags = { SETTINGS_DRAWER: true };
  setup({ editMode: true });

  expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument();
});
