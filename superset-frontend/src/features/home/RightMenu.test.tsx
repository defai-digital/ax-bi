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
import {
  createStore,
  render,
  screen,
  userEvent,
  waitFor,
} from 'spec/helpers/testing-library';
import { isFeatureEnabled, FeatureFlag, CACHE_KEY } from '@superset-ui/core';
import { isEmbedded } from 'src/dashboard/util/isEmbedded';
import RightMenu from './RightMenu';
import { RightMenuProps } from './types';

jest.mock('@superset-ui/core', () => ({
  ...jest.requireActual('@superset-ui/core'),
  isFeatureEnabled: jest.fn(),
}));

const mockIsFeatureEnabled = isFeatureEnabled as jest.MockedFunction<
  typeof isFeatureEnabled
>;

jest.mock('src/dashboard/util/isEmbedded', () => ({
  isEmbedded: jest.fn(() => false),
}));

const mockIsEmbedded = isEmbedded as jest.MockedFunction<typeof isEmbedded>;

const createProps = (): RightMenuProps => ({
  align: 'flex-end',
  navbarRight: {
    show_watermark: false,
    bug_report_url: undefined,
    documentation_url: undefined,
    languages: {
      en: {
        flag: 'us',
        name: 'English',
        url: '/lang/en',
      },
      it: {
        flag: 'it',
        name: 'Italian',
        url: '/lang/it',
      },
    },
    show_language_picker: false,
    user_is_anonymous: false,
    user_info_url: '/users/userinfo/',
    user_logout_url: '/logout/',
    user_login_url: '/login/',
    locale: 'en',
    version_string: '1.0.0',
    version_sha: 'randomSha',
    build_number: 'randomBuildNumber',
  },
  settings: [],
  isFrontendRoute: () => true,
  environmentTag: {
    color: 'error.base',
    text: 'Development2',
  },
});

beforeEach(() => {
  mockIsFeatureEnabled.mockReturnValue(false);
  mockIsEmbedded.mockReturnValue(false);
});

test('renders', async () => {
  const mockedProps = createProps();
  const { container } = render(<RightMenu {...mockedProps} />, {
    useRedux: true,
    useRouter: true,
    useTheme: true,
  });
  await waitFor(() => expect(container).toBeInTheDocument());
});

test('Logs out and clears local storage item redux', async () => {
  const mockedProps = createProps();
  render(<RightMenu {...mockedProps} />, {
    useRedux: true,
    useRouter: true,
    useTheme: true,
  });

  localStorage.setItem('redux', JSON.stringify({ test: 'test' }));
  sessionStorage.setItem('login_attempted', 'true');
  expect(localStorage.getItem('redux')).not.toBeNull();
  expect(sessionStorage.getItem('login_attempted')).not.toBeNull();

  const cacheGlobal = global as unknown as { caches?: CacheStorage };
  const priorCaches = cacheGlobal.caches;
  const deleteMock = jest.fn().mockResolvedValue(true);
  cacheGlobal.caches = { delete: deleteMock } as unknown as CacheStorage;

  try {
    await userEvent.hover(await screen.findByText(/Settings/i));

    const logoutButton = await screen.findByText('Logout');
    await userEvent.click(logoutButton);

    await waitFor(() => {
      expect(localStorage.getItem('redux')).toBeNull();
      expect(sessionStorage.getItem('login_attempted')).toBeNull();
    });
    expect(deleteMock).toHaveBeenCalledWith(CACHE_KEY);
  } finally {
    if (priorCaches === undefined) {
      delete cacheGlobal.caches;
    } else {
      cacheGlobal.caches = priorCaches;
    }
  }
});

test('shows logout button when not embedded', async () => {
  mockIsEmbedded.mockReturnValue(false);
  mockIsFeatureEnabled.mockReturnValue(false);
  render(<RightMenu {...createProps()} />, {
    useRedux: true,
    useRouter: true,
    useTheme: true,
  });

  userEvent.hover(await screen.findByText(/Settings/i));
  expect(await screen.findByText('Logout')).toBeInTheDocument();
});

test('shows logout button when embedded but flag is disabled', async () => {
  mockIsEmbedded.mockReturnValue(true);
  mockIsFeatureEnabled.mockReturnValue(false);
  render(<RightMenu {...createProps()} />, {
    useRedux: true,
    useRouter: true,
    useTheme: true,
  });

  userEvent.hover(await screen.findByText(/Settings/i));
  expect(await screen.findByText('Logout')).toBeInTheDocument();
});

test('shows logout button when not embedded even if flag is enabled', async () => {
  mockIsEmbedded.mockReturnValue(false);
  mockIsFeatureEnabled.mockImplementation(
    (flag: FeatureFlag) => flag === FeatureFlag.DisableEmbeddedSupersetLogout,
  );
  render(<RightMenu {...createProps()} />, {
    useRedux: true,
    useRouter: true,
    useTheme: true,
  });

  userEvent.hover(await screen.findByText(/Settings/i));
  expect(await screen.findByText('Logout')).toBeInTheDocument();
});

test('hides logout button when embedded and flag is enabled', async () => {
  mockIsEmbedded.mockReturnValue(true);
  mockIsFeatureEnabled.mockImplementation(
    (flag: FeatureFlag) => flag === FeatureFlag.DisableEmbeddedSupersetLogout,
  );
  render(<RightMenu {...createProps()} />, {
    useRedux: true,
    useRouter: true,
    useTheme: true,
  });

  userEvent.hover(await screen.findByText(/Settings/i));
  expect(screen.queryByText('Logout')).not.toBeInTheDocument();
});

test('shows upload data menu item when local upload is enabled and permitted', async () => {
  mockIsFeatureEnabled.mockImplementation(
    (flag: FeatureFlag) => flag === FeatureFlag.EnableLocalFileUpload,
  );
  render(<RightMenu {...createProps()} />, {
    useRedux: true,
    useRouter: true,
    useTheme: true,
    initialState: {
      user: {
        roles: {
          Alpha: [['can_upload', 'Database']],
        },
      },
    },
  });

  userEvent.hover(await screen.findByText(/Settings/i));
  expect(await screen.findByText('Upload data')).toBeInTheDocument();
});

test('dashboard create menu item uses backend navigation', async () => {
  render(<RightMenu {...createProps()} />, {
    useRedux: true,
    useRouter: true,
    useTheme: true,
  });

  userEvent.hover(await screen.findByText(/Settings/i));

  const dashboardLink = (await screen.findByText('Dashboard')).closest('a');
  expect(dashboardLink).toHaveAttribute('href', '/dashboard/new/');
});

test('hides upload data menu item without local upload permission', async () => {
  mockIsFeatureEnabled.mockImplementation(
    (flag: FeatureFlag) => flag === FeatureFlag.EnableLocalFileUpload,
  );
  render(<RightMenu {...createProps()} />, {
    useRedux: true,
    useRouter: true,
    useTheme: true,
    initialState: {
      user: {
        roles: {
          Gamma: [['can_read', 'Database']],
        },
      },
    },
  });

  userEvent.hover(await screen.findByText(/Settings/i));
  await waitFor(() => {
    expect(screen.queryByText('Upload data')).not.toBeInTheDocument();
  });
});

test('hides upload data menu item when local upload is disabled', async () => {
  mockIsFeatureEnabled.mockReturnValue(false);
  render(<RightMenu {...createProps()} />, {
    useRedux: true,
    useRouter: true,
    useTheme: true,
    initialState: {
      user: {
        roles: {
          Alpha: [['can_upload', 'Database']],
        },
      },
    },
  });

  userEvent.hover(await screen.findByText(/Settings/i));
  await waitFor(() => {
    expect(screen.queryByText('Upload data')).not.toBeInTheDocument();
  });
});

test('updates upload data menu item when upload permission changes', async () => {
  mockIsFeatureEnabled.mockImplementation(
    (flag: FeatureFlag) => flag === FeatureFlag.EnableLocalFileUpload,
  );

  const store = createStore(
    {},
    {
      user: (
        state = { roles: { Gamma: [['can_read', 'Database']] } },
        action: { type: string },
      ) =>
        action.type === 'grant-upload'
          ? { roles: { Alpha: [['can_upload', 'Database']] } }
          : state,
    },
  );

  render(<RightMenu {...createProps()} />, {
    store,
    useRouter: true,
    useTheme: true,
  });

  userEvent.hover(await screen.findByText(/Settings/i));
  await waitFor(() => {
    expect(screen.queryByText('Upload data')).not.toBeInTheDocument();
  });

  store.dispatch({ type: 'grant-upload' });

  expect(await screen.findByText('Upload data')).toBeInTheDocument();
});
