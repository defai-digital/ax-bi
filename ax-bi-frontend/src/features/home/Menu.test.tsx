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
import { render, screen, userEvent } from 'spec/helpers/testing-library';
import setupCodeOverrides from 'src/setup/setupCodeOverrides';
import { getExtensionsRegistry } from '@ax-bi/ui-core';
import * as CoreTheme from '@ax-bi/core/theme';
import { Menu } from './Menu';
import * as getBootstrapData from 'src/utils/getBootstrapData';

jest.mock('@ax-bi/core/theme', () => ({
  ...jest.requireActual('@ax-bi/core/theme'),
  useTheme: jest.fn(),
}));

jest.mock('antd', () => ({
  ...jest.requireActual('antd'),
  Grid: {
    ...jest.requireActual('antd').Grid,
    useBreakpoint: () => ({ md: true }),
  },
}));

const user = {
  createdOn: '2021-04-27T18:12:38.952304',
  email: 'admin',
  firstName: 'admin',
  isActive: true,
  lastName: 'admin',
  permissions: {},
  roles: {
    Admin: [
      ['can_sqllab', 'AxBI'],
      ['can_write', 'Dashboard'],
      ['can_write', 'Chart'],
    ],
  },
  userId: 1,
  username: 'admin',
};

const mockedProps = {
  user,
  data: {
    menu: [
      {
        name: 'Home',
        icon: '',
        label: 'Home',
        url: '/ax-bi/welcome',
        index: 1,
      },
      {
        name: 'Sources',
        icon: 'fa-table',
        label: 'Sources',
        index: 2,
        childs: [
          {
            name: 'Datasets',
            icon: 'fa-table',
            label: 'Datasets',
            url: '/tablemodelview/list/',
            index: 1,
          },
          '-',
          {
            name: 'Databases',
            icon: 'fa-database',
            label: 'Databases',
            url: '/databaseview/list/',
            index: 2,
          },
        ],
      },
      {
        name: 'Charts',
        icon: 'fa-bar-chart',
        label: 'Charts',
        url: '/chart/list/',
        index: 3,
      },
      {
        name: 'Dashboards',
        icon: 'fa-dashboard',
        label: 'Dashboards',
        url: '/dashboard/list/',
        index: 4,
      },
      {
        name: 'Data',
        icon: 'fa-database',
        label: 'Data',
        childs: [
          {
            name: 'Databases',
            icon: 'fa-database',
            label: 'Databases',
            url: '/databaseview/list/',
          },
          {
            name: 'Datasets',
            icon: 'fa-table',
            label: 'Datasets',
            url: '/tablemodelview/list/',
          },
          '-',
        ],
      },
    ],
    brand: {
      path: '/ax-bi/welcome/',
      icon: '/static/assets/images/ax-bi-logo-horiz.png',
      alt: 'AX BI',
      width: '126',
      tooltip: '',
      text: '',
    },
    environment_tag: {
      text: 'Production',
      color: '#000',
    },
    navbar_right: {
      show_watermark: false,
      bug_report_url: '/report/',
      documentation_url: '/docs/',
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
      show_language_picker: true,
      user_is_anonymous: true,
      user_info_url: '/users/userinfo/',
      user_logout_url: '/logout/',
      user_login_url: '/login/',
      locale: 'en',
      version_string: '1.0.0',
      version_sha: 'randomSHA',
      build_number: 'randomBuildNumber',
    },
    settings: [
      {
        name: 'Security',
        icon: 'fa-cogs',
        label: 'Security',
        index: 1,
        childs: [
          {
            name: 'List Users',
            icon: 'fa-user',
            label: 'List Users',
            url: '/users/list/',
            index: 1,
          },
        ],
      },
    ],
  },
};

const notanonProps = {
  ...mockedProps,
  data: {
    ...mockedProps.data,
    navbar_right: {
      ...mockedProps.data.navbar_right,
      user_is_anonymous: false,
    },
  },
};

const staticAssetsPrefixMock = jest.spyOn(
  getBootstrapData,
  'staticAssetsPrefix',
);
const applicationRootMock = jest.spyOn(getBootstrapData, 'applicationRoot');
const useThemeMock = CoreTheme.useTheme as jest.Mock;

// Seed Redux user state instead of spying on react-redux hooks.
// react-redux v9 exports are non-configurable, so jest.spyOn(useSelector) fails.
const menuRenderOptions = {
  useRedux: true as const,
  useQueryParams: true as const,
  useRouter: true as const,
  useTheme: true as const,
  initialState: { user },
};

fetchMock.get(
  'glob:*api/v1/database/?q=(filters:!((col:allow_file_upload,opr:upload_is_enabled,value:!t)))',
  {},
);

beforeEach(() => {
  // By default use empty static assets prefix and default app root
  staticAssetsPrefixMock.mockReturnValue('');
  applicationRootMock.mockReturnValue('');
  // By default useTheme returns the real default theme (brandLogoUrl is falsy)
  useThemeMock.mockReturnValue(CoreTheme.axbiTheme);
});

test('should render', async () => {
  const { container } = render(<Menu {...mockedProps} />, menuRenderOptions);
  expect(await screen.findByText(/sources/i)).toBeInTheDocument();
  expect(container).toBeInTheDocument();
});

test('should render the navigation', async () => {
  render(<Menu {...mockedProps} />, menuRenderOptions);
  expect(await screen.findByRole('navigation')).toBeInTheDocument();
});

test.each(['', '/myapp'])(
  'should render the brand, including app_root "%s"',
  async app_root => {
    staticAssetsPrefixMock.mockReturnValue(app_root);
    const {
      data: {
        brand: { alt, icon },
      },
    } = mockedProps;
    render(<Menu {...mockedProps} />, menuRenderOptions);
    expect(await screen.findByAltText(alt)).toBeInTheDocument();
    const image = screen.getByAltText(alt);
    expect(image).toHaveAttribute('src', `${app_root}${icon}`);
  },
);

test('should render the environment tag inside Settings dropdown', async () => {
  const {
    data: { environment_tag },
  } = mockedProps;
  render(<Menu {...mockedProps} />, menuRenderOptions);
  // The environment tag is now inside the Settings dropdown
  userEvent.hover(screen.getByText('Settings'));
  expect(await screen.findByText(environment_tag.text)).toBeInTheDocument();
});

test('should render all the top navbar menu items', async () => {
  const {
    data: { menu },
  } = mockedProps;
  render(<Menu {...mockedProps} />, menuRenderOptions);
  expect(await screen.findByText(menu[0].label)).toBeInTheDocument();
  menu.forEach(item => {
    expect(screen.getByText(item.label)).toBeInTheDocument();
  });
});

test('should render the top navbar child menu items', async () => {
  const {
    data: { menu },
  } = mockedProps;
  render(<Menu {...mockedProps} />, menuRenderOptions);
  const sources = await screen.findByText('Sources');
  userEvent.hover(sources);

  const datasets = await screen.findByText('Datasets');
  const databases = await screen.findByText('Databases');
  const dataset = menu[1].childs![0] as { url: string };
  const database = menu[1].childs![2] as { url: string };

  expect(datasets).toHaveAttribute('href', dataset.url);
  expect(databases).toHaveAttribute('href', database.url);
});

test('should render the Settings', async () => {
  render(<Menu {...mockedProps} />, menuRenderOptions);
  const settings = await screen.findByText('Settings');
  expect(settings).toBeInTheDocument();
});

test('should render the Settings menu item', async () => {
  render(<Menu {...mockedProps} />, menuRenderOptions);
  userEvent.hover(screen.getByText('Settings'));
  const label = await screen.findByText('Security');
  expect(label).toBeInTheDocument();
});

test('should render the Settings dropdown child menu items', async () => {
  const {
    data: { settings },
  } = mockedProps;
  render(<Menu {...mockedProps} />, menuRenderOptions);
  userEvent.hover(screen.getByText('Settings'));
  const listUsers = await screen.findByText('List Users');
  expect(listUsers).toHaveAttribute('href', settings[0].childs[0].url);
});

test('should NOT render the plus menu (+) when user is anonymous', async () => {
  render(<Menu {...mockedProps} />, menuRenderOptions);
  expect(await screen.findByText(/sources/i)).toBeInTheDocument();
  expect(screen.queryByTestId('new-dropdown')).not.toBeInTheDocument();
});

test('should render the user actions when user is not anonymous', async () => {
  const {
    data: {
      navbar_right: { user_info_url, user_logout_url },
    },
  } = mockedProps;

  render(<Menu {...notanonProps} />, menuRenderOptions);
  userEvent.hover(screen.getByText('Settings'));
  const user = await screen.findByText('User');
  expect(user).toBeInTheDocument();

  const info = await screen.findByText('Info');
  const logout = await screen.findByText('Logout');

  expect(info).toHaveAttribute('href', user_info_url);
  expect(logout).toHaveAttribute('href', user_logout_url);
});

test('should NOT render the user actions when user is anonymous', async () => {
  render(<Menu {...mockedProps} />, menuRenderOptions);
  expect(await screen.findByText(/sources/i)).toBeInTheDocument();
  expect(screen.queryByText('User')).not.toBeInTheDocument();
});

test('should render the About section and version_string, sha or build_number when available', async () => {
  const {
    data: {
      navbar_right: { version_sha, version_string, build_number },
    },
  } = mockedProps;

  render(<Menu {...mockedProps} />, menuRenderOptions);
  userEvent.hover(screen.getByText('Settings'));
  const about = await screen.findByText('About');

  // The version information is rendered as combined text in a single element
  // Use getAllByText to get all matching elements and check the first one
  const versionTexts = await screen.findAllByText(
    (_, element) =>
      element?.textContent?.includes(`Version: ${version_string}`) ?? false,
  );
  const shaTexts = await screen.findAllByText(
    (_, element) =>
      element?.textContent?.includes(`SHA: ${version_sha}`) ?? false,
  );
  const buildTexts = await screen.findAllByText(
    (_, element) =>
      element?.textContent?.includes(`Build: ${build_number}`) ?? false,
  );

  expect(about).toBeInTheDocument();
  expect(versionTexts[0]).toBeInTheDocument();
  expect(shaTexts[0]).toBeInTheDocument();
  expect(buildTexts[0]).toBeInTheDocument();
});

test('should render the Documentation link inside Settings when available', async () => {
  const {
    data: {
      navbar_right: { documentation_url },
    },
  } = mockedProps;
  render(<Menu {...mockedProps} />, menuRenderOptions);
  // Documentation link is now inside the Settings dropdown Help group
  userEvent.hover(screen.getByText('Settings'));
  const doc = await screen.findByText('Documentation');
  expect(doc.closest('a')).toHaveAttribute('href', documentation_url);
});

test('should render the Bug Report link inside Settings when available', async () => {
  const {
    data: {
      navbar_right: { bug_report_url },
    },
  } = mockedProps;

  render(<Menu {...mockedProps} />, menuRenderOptions);
  // Bug report link is now inside the Settings dropdown Help group
  userEvent.hover(screen.getByText('Settings'));
  const bugReport = await screen.findByText('Report a bug');
  expect(bugReport.closest('a')).toHaveAttribute('href', bug_report_url);
});

test('should render the Language Picker', async () => {
  render(<Menu {...mockedProps} />, menuRenderOptions);
  expect(await screen.findByLabelText('Languages')).toBeInTheDocument();
});

test('should hide create button without proper roles', async () => {
  render(<Menu {...mockedProps} />, menuRenderOptions);
  expect(await screen.findByText(/sources/i)).toBeInTheDocument();
  expect(screen.queryByTestId('new-dropdown')).not.toBeInTheDocument();
});

test('should render without QueryParamProvider', async () => {
  render(<Menu {...mockedProps} />, menuRenderOptions);
  expect(await screen.findByText(/sources/i)).toBeInTheDocument();
  expect(screen.queryByTestId('new-dropdown')).not.toBeInTheDocument();
});

test('should render an extension component if one is supplied', async () => {
  const extensionsRegistry = getExtensionsRegistry();

  extensionsRegistry.set('navbar.right', () => (
    <>navbar.right extension component</>
  ));

  setupCodeOverrides();

  render(<Menu {...mockedProps} />, menuRenderOptions);

  const extension = await screen.findAllByText(
    'navbar.right extension component',
  );

  expect(extension[0]).toBeInTheDocument();
});

test('should render the brand text if available', async () => {
  const modifiedProps = {
    ...mockedProps,
    data: {
      ...mockedProps.data,
      brand: {
        ...mockedProps.data.brand,
        text: 'Welcome to AxBI',
      },
    },
  };

  render(<Menu {...modifiedProps} />, menuRenderOptions);

  const brandText = await screen.findByText('Welcome to AxBI');
  expect(brandText).toBeInTheDocument();
});

test('should not render the brand text if not available', async () => {
  const text = 'Welcome to AxBI';
  render(<Menu {...mockedProps} />, menuRenderOptions);

  const brandText = screen.queryByText(text);
  expect(brandText).not.toBeInTheDocument();
});

test('brand logo href should not be prefixed with app root when brandLogoHref is an absolute URL', async () => {
  applicationRootMock.mockReturnValue('/ax-bi');
  useThemeMock.mockReturnValue({
    ...CoreTheme.axbiTheme,
    brandLogoUrl: '/static/assets/images/custom-logo.png',
    brandLogoHref: 'https://external.example.com',
    brandLogoAlt: 'Brand Home',
  });

  render(<Menu {...mockedProps} />, menuRenderOptions);

  const brandLink = await screen.findByRole('link', {
    name: /brand home/i,
  });
  expect(brandLink).toHaveAttribute('href', 'https://external.example.com');
});

test('brand logo href should not be prefixed with app root when brandLogoHref is protocol-relative', async () => {
  applicationRootMock.mockReturnValue('/ax-bi');
  useThemeMock.mockReturnValue({
    ...CoreTheme.axbiTheme,
    brandLogoUrl: '/static/assets/images/custom-logo.png',
    brandLogoHref: '//external.example.com',
    brandLogoAlt: 'Brand Home',
  });

  render(<Menu {...mockedProps} />, menuRenderOptions);

  const brandLink = await screen.findByRole('link', {
    name: /brand home/i,
  });
  expect(brandLink).toHaveAttribute('href', '//external.example.com');
});

test('brand path should be prefixed with app root in subdirectory deployment', async () => {
  applicationRootMock.mockReturnValue('/ax-bi');

  const propsWithSimplePath = {
    ...mockedProps,
    data: {
      ...mockedProps.data,
      brand: {
        ...mockedProps.data.brand,
        path: '/welcome/',
      },
    },
  };

  render(<Menu {...propsWithSimplePath} />, menuRenderOptions);

  const brandLink = await screen.findByRole('link', {
    name: new RegExp(propsWithSimplePath.data.brand.alt, 'i'),
  });
  // ensureAppRoot prefixes the configured application root.
  expect(brandLink).toHaveAttribute('href', '/ax-bi/welcome/');
});

test('brand link falls back to brand.path when theme brandLogoUrl is absent', async () => {
  // useThemeMock default returns axbiTheme with brandLogoUrl undefined (falsy)
  applicationRootMock.mockReturnValue('/ax-bi');

  const propsWithFallbackPath = {
    ...mockedProps,
    data: {
      ...mockedProps.data,
      brand: {
        ...mockedProps.data.brand,
        path: '/welcome/',
      },
    },
  };

  render(<Menu {...propsWithFallbackPath} />, menuRenderOptions);

  const brandLink = await screen.findByRole('link', {
    name: new RegExp(propsWithFallbackPath.data.brand.alt, 'i'),
  });
  // ensureAppRoot prefixes the configured application root: /welcome/ → /ax-bi/welcome/
  expect(brandLink).toHaveAttribute('href', '/ax-bi/welcome/');
});
