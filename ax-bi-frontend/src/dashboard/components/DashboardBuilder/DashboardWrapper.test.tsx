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
import { render } from 'spec/helpers/testing-library';

import DashboardWrapper from './DashboardWrapper';
import { DashboardGridLayoutContext } from './gridLayoutMode';

beforeAll(() => {
  jest.useFakeTimers();
});

afterAll(() => {
  jest.useRealTimers();
});

test('should render children', () => {
  const { getByTestId } = render(
    <DashboardWrapper>
      <div data-test="mock-children" />
    </DashboardWrapper>,
    { useRedux: true, useDnd: true },
  );
  expect(getByTestId('mock-children')).toBeInTheDocument();
});

test('should apply the dashboard--stack class in stack layout mode', () => {
  const { getByTestId } = render(
    <DashboardGridLayoutContext.Provider value="stack">
      <DashboardWrapper>
        <div data-test="mock-children" />
      </DashboardWrapper>
    </DashboardGridLayoutContext.Provider>,
    { useRedux: true, useDnd: true },
  );
  expect(getByTestId('dashboard-wrapper')).toHaveClass('dashboard--stack');
});

test('should apply the dashboard--compact class in compact layout mode', () => {
  const { getByTestId } = render(
    <DashboardGridLayoutContext.Provider value="compact">
      <DashboardWrapper>
        <div data-test="mock-children" />
      </DashboardWrapper>
    </DashboardGridLayoutContext.Provider>,
    { useRedux: true, useDnd: true },
  );
  const wrapper = getByTestId('dashboard-wrapper');
  expect(wrapper).toHaveClass('dashboard--compact');
  expect(wrapper).not.toHaveClass('dashboard--stack');
});

test('should expose its viewport offset for dashboard scrolling', () => {
  const getBoundingClientRect = jest
    .spyOn(HTMLElement.prototype, 'getBoundingClientRect')
    .mockReturnValue({
      top: 64,
      bottom: 864,
      left: 0,
      right: 1200,
      width: 1200,
      height: 800,
      x: 0,
      y: 64,
      toJSON: () => {},
    });

  const { getByTestId } = render(
    <DashboardWrapper>
      <div data-test="mock-children" />
    </DashboardWrapper>,
    { useRedux: true, useDnd: true },
  );

  expect(getByTestId('dashboard-wrapper')).toHaveStyle({
    '--dashboard-top-offset': '64px',
  });

  getBoundingClientRect.mockRestore();
});

test('should refresh its viewport offset after dashboard layout shifts', () => {
  let topOffset = 64;
  const getBoundingClientRect = jest
    .spyOn(HTMLElement.prototype, 'getBoundingClientRect')
    .mockImplementation(
      () =>
        ({
          top: topOffset,
          bottom: topOffset + 800,
          left: 0,
          right: 1200,
          width: 1200,
          height: 800,
          x: 0,
          y: topOffset,
          toJSON: () => {},
        }) as DOMRect,
    );

  const { getByTestId, rerender } = render(
    <DashboardWrapper>
      <div data-test="mock-children">before</div>
    </DashboardWrapper>,
    { useRedux: true, useDnd: true },
  );

  expect(getByTestId('dashboard-wrapper')).toHaveStyle({
    '--dashboard-top-offset': '64px',
  });

  topOffset = 112;
  rerender(
    <DashboardWrapper>
      <div data-test="mock-children">after</div>
    </DashboardWrapper>,
  );

  expect(getByTestId('dashboard-wrapper')).toHaveStyle({
    '--dashboard-top-offset': '112px',
  });

  getBoundingClientRect.mockRestore();
});

// Note: Drag-and-drop test removed - DashboardWrapper uses react-dnd but
// OptionControlLabel uses @dnd-kit, causing cross-library compatibility issues.
// This test requires proper @dnd-kit testing utilities.
