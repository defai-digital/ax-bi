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
import { render, screen, waitFor } from '@superset-ui/core/spec';
import AsyncIcon from './AsyncIcon';

jest.unmock('@superset-ui/core/components/Icons/AsyncIcon');

jest.mock(
  '!!@svgr/webpack!src/assets/images/icons/drag.svg',
  () => ({
    __esModule: true,
    default: function MockDragIcon(props: React.SVGProps<SVGSVGElement>) {
      return <svg data-test="mock-drag-icon" {...props} />;
    },
  }),
  { virtual: true },
);

jest.mock(
  '!!@svgr/webpack!src/assets/images/icons/full.svg',
  () => ({
    __esModule: true,
    default: function MockFullIcon(props: React.SVGProps<SVGSVGElement>) {
      return <svg data-test="mock-full-icon" {...props} />;
    },
  }),
  { virtual: true },
);

test('loads custom icons asynchronously', async () => {
  render(<AsyncIcon customIcons fileName="drag" />);

  await waitFor(() =>
    expect(screen.getByTestId('mock-drag-icon')).toBeInTheDocument(),
  );
});

test('updates the displayed custom icon when the icon name changes', async () => {
  const { rerender } = render(<AsyncIcon customIcons fileName="drag" />);

  await waitFor(() =>
    expect(screen.getByTestId('mock-drag-icon')).toBeInTheDocument(),
  );

  rerender(<AsyncIcon customIcons fileName="full" />);

  await waitFor(() =>
    expect(screen.getByTestId('mock-full-icon')).toBeInTheDocument(),
  );
  expect(screen.queryByTestId('mock-drag-icon')).not.toBeInTheDocument();
});

test('falls back safely when a custom icon asset does not exist', async () => {
  render(<AsyncIcon customIcons fileName="error" />);

  await waitFor(() =>
    expect(screen.getByRole('img', { name: 'error' })).toBeInTheDocument(),
  );
});
