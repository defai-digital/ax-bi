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

import fetchMock from 'fetch-mock';
import { render, screen } from 'spec/helpers/testing-library';
import UploadData from '.';

// Mock the auto_upload endpoint
fetchMock.post('glob:*api/v1/database/auto_upload/', {
  database_id: 1,
  dataset_id: 1,
  table_name: 'upload_test_abc123',
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
    expect(
      screen.getByText('Click or drag files to upload'),
    ).toBeVisible();

    // Check that supported formats are listed with multi-file note
    expect(
      screen.getByText(
        'Supported formats: CSV, TSV, XLS, XLSX, Parquet. Multiple files supported.',
      ),
    ).toBeVisible();
  });
});
