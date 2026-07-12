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
import { isFeatureEnabled, FeatureFlag } from '@ax-bi/ui-core';
import { TableTab } from 'src/views/CRUD/types';
import { render, screen, userEvent } from 'spec/helpers/testing-library';
import { navigateTo } from 'src/utils/navigationUtils';
import EmptyState, { EmptyStateProps } from './EmptyState';
import { WelcomeTable } from './types';

jest.mock('@ax-bi/ui-core', () => ({
  ...jest.requireActual('@ax-bi/ui-core'),
  isFeatureEnabled: jest.fn(),
}));

jest.mock('src/utils/navigationUtils', () => ({
  navigateTo: jest.fn(),
}));

const mockIsFeatureEnabled = isFeatureEnabled as jest.MockedFunction<
  typeof isFeatureEnabled
>;

const uploadPermittedState = {
  user: { roles: { Alpha: [['can_upload', 'Database']] } },
};

beforeEach(() => {
  mockIsFeatureEnabled.mockReturnValue(false);
  (navigateTo as jest.Mock).mockClear();
});

// eslint-disable-next-line no-restricted-globals -- TODO: Migrate from describe blocks
describe('EmptyState', () => {
  const variants: Array<EmptyStateProps & { description: string }> = [
    {
      tab: TableTab.Favorite,
      tableName: WelcomeTable.Dashboards,
      description: 'Create a dashboard or generate one from uploaded data.',
    },
    {
      tab: TableTab.Mine,
      tableName: WelcomeTable.Dashboards,
      description: 'Create a dashboard or generate one from uploaded data.',
    },
    {
      tab: TableTab.Favorite,
      tableName: WelcomeTable.Charts,
      description: 'Upload data or create a chart to start visual analysis.',
    },
    {
      tab: TableTab.Mine,
      tableName: WelcomeTable.Charts,
      description: 'Upload data or create a chart to start visual analysis.',
    },
    {
      tab: TableTab.Favorite,
      tableName: WelcomeTable.SavedQueries,
      description: 'Your recent analytics activity will appear here.',
    },
    {
      tab: TableTab.Mine,
      tableName: WelcomeTable.SavedQueries,
      description: 'Your recent analytics activity will appear here.',
    },
  ];
  const recents: EmptyStateProps[] = [
    {
      tab: TableTab.Viewed,
      tableName: WelcomeTable.Recents,
    },
    {
      tab: TableTab.Edited,
      tableName: WelcomeTable.Recents,
    },
    {
      tab: TableTab.Created,
      tableName: WelcomeTable.Recents,
    },
  ];

  variants.forEach(variant => {
    test(`renders an ${variant.tab} ${variant.tableName} empty state`, () => {
      const { container } = render(<EmptyState {...variant} />, {
        useRedux: true,
      });

      // Select the first description node
      expect(
        container.querySelector('.ant-empty-description'),
      ).toHaveTextContent(variant.description);
      expect(screen.getAllByRole('button')).toHaveLength(1);
    });
  });

  recents.forEach(recent => {
    test(`renders a ${recent.tab} ${recent.tableName} empty state`, () => {
      const { container } = render(<EmptyState {...recent} />, {
        useRedux: true,
      });

      // Select the first description node
      // Check the correct text is displayed
      expect(
        container.querySelector('.ant-empty-description'),
      ).toHaveTextContent('Your recent analytics activity will appear here.');

      // Validate the image
      expect(
        container.querySelector('.ant-empty-image')?.children,
      ).toHaveLength(1);
    });
  });

  test('shows an Upload data CTA when upload is enabled and permitted', async () => {
    mockIsFeatureEnabled.mockImplementation(
      (flag: FeatureFlag) => flag === FeatureFlag.EnableLocalFileUpload,
    );
    render(<EmptyState tab={TableTab.Mine} tableName={WelcomeTable.Charts} />, {
      useRedux: true,
      initialState: uploadPermittedState,
    });

    const uploadButton = await screen.findByText('Upload data');
    expect(uploadButton).toBeInTheDocument();

    await userEvent.click(uploadButton);
    expect(navigateTo).toHaveBeenCalledWith('/upload/');
  });

  test('shows the Upload data CTA on the Dashboards empty state', async () => {
    mockIsFeatureEnabled.mockImplementation(
      (flag: FeatureFlag) => flag === FeatureFlag.EnableLocalFileUpload,
    );
    render(
      <EmptyState tab={TableTab.Mine} tableName={WelcomeTable.Dashboards} />,
      {
        useRedux: true,
        initialState: uploadPermittedState,
      },
    );

    expect(await screen.findByText('Upload data')).toBeInTheDocument();
  });

  test('hides the Upload data CTA without the upload permission', () => {
    mockIsFeatureEnabled.mockImplementation(
      (flag: FeatureFlag) => flag === FeatureFlag.EnableLocalFileUpload,
    );
    render(<EmptyState tab={TableTab.Mine} tableName={WelcomeTable.Charts} />, {
      useRedux: true,
      initialState: { user: { roles: { Gamma: [['can_read', 'Database']] } } },
    });

    expect(screen.queryByText('Upload data')).not.toBeInTheDocument();
  });

  test('hides the Upload data CTA when the feature flag is off', () => {
    mockIsFeatureEnabled.mockReturnValue(false);
    render(<EmptyState tab={TableTab.Mine} tableName={WelcomeTable.Charts} />, {
      useRedux: true,
      initialState: uploadPermittedState,
    });

    expect(screen.queryByText('Upload data')).not.toBeInTheDocument();
  });

  test('hides the Upload data CTA on the Favorite tab', () => {
    mockIsFeatureEnabled.mockImplementation(
      (flag: FeatureFlag) => flag === FeatureFlag.EnableLocalFileUpload,
    );
    render(
      <EmptyState tab={TableTab.Favorite} tableName={WelcomeTable.Charts} />,
      {
        useRedux: true,
        initialState: uploadPermittedState,
      },
    );

    expect(screen.queryByText('Upload data')).not.toBeInTheDocument();
  });

  test('hides the Upload data CTA on the Saved queries empty state', () => {
    mockIsFeatureEnabled.mockImplementation(
      (flag: FeatureFlag) => flag === FeatureFlag.EnableLocalFileUpload,
    );
    render(
      <EmptyState tab={TableTab.Mine} tableName={WelcomeTable.SavedQueries} />,
      {
        useRedux: true,
        initialState: uploadPermittedState,
      },
    );

    expect(screen.queryByText('Upload data')).not.toBeInTheDocument();
  });
});
