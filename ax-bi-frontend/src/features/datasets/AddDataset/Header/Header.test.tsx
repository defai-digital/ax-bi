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
import { render, screen, waitFor } from 'spec/helpers/testing-library';
import Header, { DEFAULT_TITLE } from 'src/features/datasets/AddDataset/Header';

// eslint-disable-next-line no-restricted-globals -- TODO: Migrate from describe blocks
describe('Header', () => {
  const mockSetDataset = jest.fn();

  const waitForRender = (props?: any) =>
    waitFor(() => render(<Header setDataset={mockSetDataset} {...props} />));

  test('renders a blank state Header', async () => {
    await waitForRender();

    // Title bar and breadcrumb current-page crumb both show the title
    const datasetNames = screen.getAllByText(/new dataset/i);

    expect(datasetNames[0]).toBeVisible();
  });

  test('displays "New dataset" when a table is not selected', async () => {
    await waitForRender();

    const datasetNames = screen.getAllByText(/new dataset/i);
    expect(datasetNames[0].innerHTML).toBe(DEFAULT_TITLE);
  });

  test('displays table name when a table is selected', async () => {
    // The schema and table name are passed in through props once selected
    await waitForRender({ schema: 'testSchema', title: 'testTable' });

    const datasetNames = screen.getAllByText(/testtable/i);

    expect(datasetNames[0].innerHTML).toBe('testTable');
  });

  test('renders breadcrumbs linking to the datasets list', async () => {
    await waitForRender({ title: 'testTable' });

    expect(screen.getByRole('link', { name: 'Datasets' })).toHaveAttribute(
      'href',
      '/datasets',
    );
    // The current page crumb is not a link
    expect(
      screen.queryByRole('link', { name: 'testTable' }),
    ).not.toBeInTheDocument();
  });
});
