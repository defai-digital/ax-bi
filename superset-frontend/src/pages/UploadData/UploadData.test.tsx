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
import { Router } from 'react-router-dom';
import { createMemoryHistory } from 'history';
import {
  render,
  screen,
  fireEvent,
  waitFor,
} from 'spec/helpers/testing-library';
import { SupersetClient, getClientErrorObject } from '@superset-ui/core';
import { URL_PARAMS } from 'src/constants';
import UploadData from '.';

type ToastInjectedProps = {
  addDangerToast: (msg: string) => void;
  addSuccessToast: (msg: string) => void;
};

const mockAddDangerToast = jest.fn();
const mockAddSuccessToast = jest.fn();

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

jest.mock('@superset-ui/core', () => ({
  ...jest.requireActual('@superset-ui/core'),
  SupersetClient: {
    ...jest.requireActual('@superset-ui/core').SupersetClient,
    post: jest.fn(),
  },
  getClientErrorObject: jest.fn(),
}));

const mockedPost = SupersetClient.post as jest.Mock;
const mockedGetClientErrorObject = getClientErrorObject as jest.Mock;

beforeEach(() => {
  mockAddDangerToast.mockReset();
  mockAddSuccessToast.mockReset();
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
      useRouter: true,
    });

    // Check that the page title is rendered
    expect(screen.getByText('Upload Data')).toBeVisible();

    // Check that the subtitle is rendered (multi-file)
    expect(
      screen.getByText('Drop one or more files to start exploring your data'),
    ).toBeVisible();

    // Check that the drop zone text is rendered (multi-file)
    expect(screen.getByText('Click or drag files to upload')).toBeVisible();

    // Check that supported formats are listed with multi-file note
    expect(
      screen.getByText(
        'Supported formats: CSV, TSV, XLS, XLSX, Parquet. Multiple files supported.',
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
    const history = createMemoryHistory();
    const pushSpy = jest.spyOn(history, 'push');

    render(
      <Router history={history}>
        <UploadData />
      </Router>,
      {
        useRedux: true,
      },
    );

    fireEvent.change(screen.getByTestId('upload-data-dropzone'), {
      target: {
        files: [new File(['a,b\n1,2'], 'orders.csv', { type: 'text/csv' })],
      },
    });

    await screen.findByText('Uploaded');

    await waitFor(
      () =>
        expect(pushSpy).toHaveBeenCalledWith(
          `/explore/?${URL_PARAMS.datasourceType.name}=table&${URL_PARAMS.datasourceId.name}=1`,
        ),
      { timeout: 3000 },
    );
  });
});
