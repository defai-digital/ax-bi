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

import { ComponentType } from 'react';
import {
  render,
  screen,
  fireEvent,
  waitFor,
} from 'spec/helpers/testing-library';
import { AxBIClient, getClientErrorObject } from '@ax-bi/ui-core';
import { URL_PARAMS } from 'src/constants';
import UploadData from '.';

type ToastInjectedProps = {
  addDangerToast: (msg: string) => void;
  addSuccessToast: (msg: string) => void;
};

const mockAddDangerToast = jest.fn();
const mockAddSuccessToast = jest.fn();
const mockHistoryPush = jest.fn();
const mockLocationSearch = { current: '' };

jest.mock('src/hooks/useAppHistory', () => ({
  useHistory: () => ({
    push: mockHistoryPush,
    location: { search: mockLocationSearch.current },
  }),
  useAppHistory: () => ({
    push: mockHistoryPush,
    location: { search: mockLocationSearch.current },
  }),
}));

jest.mock('src/components/MessageToasts/withToasts', () => ({
  __esModule: true,
  default: (Component: ComponentType<ToastInjectedProps>) =>
    function MockedWithToasts(props: Record<string, unknown>) {
      return (
        <Component
          {...props}
          addDangerToast={mockAddDangerToast}
          addSuccessToast={mockAddSuccessToast}
        />
      );
    },
}));

jest.mock('@ax-bi/ui-core', () => ({
  ...jest.requireActual('@ax-bi/ui-core'),
  AxBIClient: {
    ...jest.requireActual('@ax-bi/ui-core').AxBIClient,
    post: jest.fn(),
  },
  getClientErrorObject: jest.fn(),
}));

const mockedPost = AxBIClient.post as jest.Mock;
const mockedGetClientErrorObject = getClientErrorObject as jest.Mock;

beforeEach(() => {
  mockAddDangerToast.mockReset();
  mockAddSuccessToast.mockReset();
  mockHistoryPush.mockReset();
  mockLocationSearch.current = '';
  mockedPost.mockReset();
  mockedGetClientErrorObject.mockReset();
  mockedPost.mockResolvedValue({
    json: {
      database_id: 1,
      dataset_id: 1,
      table_name: 'upload_test_abc123',
    },
  });
  mockedGetClientErrorObject.mockResolvedValue({ error: '' });
});

// eslint-disable-next-line no-restricted-globals -- TODO: Migrate from describe blocks
describe('UploadData', () => {
  test('renders the upload page with title and drop zone', () => {
    render(<UploadData />, {
      useRedux: true,
      reducers: {},
      useRouter: true,
    });

    expect(
      screen.getByText('Upload data and build charts faster'),
    ).toBeVisible();
    expect(screen.getByText('Start with a file')).toBeVisible();
    expect(screen.getByText('Click or drag files here')).toBeVisible();
    expect(
      screen.getByText(
        'Supported formats include CSV/TSV, compressed exports, Excel/ODS, Parquet/ORC/Arrow, JSON/XML, SQL text dumps, SQLite, fixed-width, HTML/statistical files, geospatial files, embeddings, and AI artifact metadata. Multiple files supported.',
      ),
    ).toBeVisible();
  });

  test('shows structured API error messages for failed uploads', async () => {
    const apiError = new Error('Forbidden');
    mockedPost.mockRejectedValue(apiError);
    mockedGetClientErrorObject.mockResolvedValue({
      message: 'Local file upload is disabled',
    });

    render(<UploadData />, {
      useRedux: true,
      reducers: {},
      useRouter: true,
    });

    const input = screen.getByTestId('upload-data-dropzone');
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute('type', 'file');

    fireEvent.change(input as HTMLInputElement, {
      target: {
        files: [new File(['a,b\n1,2'], 'orders.csv', { type: 'text/csv' })],
      },
    });

    await waitFor(() => {
      expect(mockedGetClientErrorObject).toHaveBeenCalledWith(apiError);
      expect(mockAddDangerToast).toHaveBeenCalledWith(
        'Local file upload is disabled',
      );
    });
    expect(await screen.findByText('Failed')).toBeVisible();
  });

  test('redirects successful uploads to explore with datasource params', async () => {
    render(<UploadData />, {
      useRedux: true,
      reducers: {},
      useRouter: true,
    });

    fireEvent.change(screen.getByTestId('upload-data-dropzone'), {
      target: {
        files: [new File(['a,b\n1,2'], 'orders.csv', { type: 'text/csv' })],
      },
    });

    await screen.findByText('Uploaded');

    await waitFor(
      () =>
        expect(mockHistoryPush).toHaveBeenCalledWith(
          `/explore/?${URL_PARAMS.datasourceType.name}=table&${URL_PARAMS.datasourceId.name}=1`,
        ),
      { timeout: 3000 },
    );
  });

  test('preserves dashboard context when redirecting to explore', async () => {
    mockLocationSearch.current = '?dashboard_id=42';

    render(<UploadData />, {
      useRedux: true,
      reducers: {},
      useRouter: true,
    });

    fireEvent.change(screen.getByTestId('upload-data-dropzone'), {
      target: {
        files: [new File(['a,b\n1,2'], 'orders.csv', { type: 'text/csv' })],
      },
    });

    await screen.findByText('Uploaded');
    await waitFor(
      () =>
        expect(mockHistoryPush).toHaveBeenCalledWith(
          `/explore/?${URL_PARAMS.datasourceType.name}=table&${URL_PARAMS.datasourceId.name}=1&${URL_PARAMS.dashboardId.name}=42`,
        ),
      { timeout: 3000 },
    );
  });

  test('uploads multiple selected files as a batch and redirects to the first dataset', async () => {
    mockedPost
      .mockResolvedValueOnce({
        json: {
          database_id: 1,
          dataset_id: 101,
          table_name: 'upload_orders_abc123',
        },
      })
      .mockResolvedValueOnce({
        json: {
          database_id: 1,
          dataset_id: 202,
          table_name: 'upload_customers_def456',
        },
      });

    render(<UploadData />, {
      useRedux: true,
      reducers: {},
      useRouter: true,
    });

    fireEvent.change(screen.getByTestId('upload-data-dropzone'), {
      target: {
        files: [
          new File(['a,b\n1,2'], 'orders.csv', { type: 'text/csv' }),
          new File(['{"a":1}\n'], 'customers.jsonl', {
            type: 'application/x-ndjson',
          }),
        ],
      },
    });

    expect((await screen.findAllByText('Uploaded')).length).toBe(2);
    expect(mockedPost).toHaveBeenCalledTimes(2);
    expect(mockAddSuccessToast).toHaveBeenCalledWith(
      'File "orders.csv" uploaded successfully!',
    );
    expect(mockAddSuccessToast).toHaveBeenCalledWith(
      'File "customers.jsonl" uploaded successfully!',
    );

    await waitFor(
      () =>
        expect(mockHistoryPush).toHaveBeenCalledWith(
          `/explore/?${URL_PARAMS.datasourceType.name}=table&${URL_PARAMS.datasourceId.name}=101`,
        ),
      { timeout: 3000 },
    );
  });
});
