/*
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

import '@testing-library/jest-dom';
import { act, render, screen, waitFor } from '@ax-bi/ui-core/spec';
import MockResizeObserver, {
  triggerResizeObserver,
} from 'resize-observer-polyfill';
import { ErrorBoundary } from 'react-error-boundary';

import { promiseTimeout, SuperChart } from '@ax-bi/ui-core';
import { axbiTheme } from '@ax-bi/core/theme';
import { WrapperProps } from '../../../src/chart/components/SuperChart';

import {
  ChartKeys,
  DiligentChartPlugin,
  BuggyChartPlugin,
} from './MockChartPlugins';

import { isMatrixifyEnabled } from '../../../src/chart/types/matrixify';
import MatrixifyGridRenderer from '../../../src/chart/components/Matrixify/MatrixifyGridRenderer';

// Mock Matrixify imports
jest.mock('../../../src/chart/types/matrixify', () => ({
  isMatrixifyEnabled: jest.fn(() => false),
  getMatrixifyConfig: jest.fn(() => null),
}));

jest.mock(
  '../../../src/chart/components/Matrixify/MatrixifyGridRenderer',
  () => ({
    __esModule: true,
    default: jest.fn(() => null),
  }),
);

const DEFAULT_QUERY_DATA = { data: ['foo', 'bar'] };
const DEFAULT_QUERIES_DATA = [
  { data: ['foo', 'bar'] },
  { data: ['foo2', 'bar2'] },
];

// Fix for expect outside test block - move expectDimension into a test utility
// Replace expectDimension function with a non-expect version
function getDimensionText(container: HTMLElement) {
  const dimensionEl = container.querySelector('.dimension');
  return dimensionEl?.textContent || '';
}

describe('SuperChart', () => {
  jest.setTimeout(5000);
  let originalResizeObserver: typeof window.ResizeObserver | undefined;

  const plugins = [
    new DiligentChartPlugin().configure({ key: ChartKeys.DILIGENT }),
    new BuggyChartPlugin().configure({ key: ChartKeys.BUGGY }),
  ];

  beforeAll(() => {
    originalResizeObserver = window.ResizeObserver;
    window.ResizeObserver =
      MockResizeObserver as unknown as typeof window.ResizeObserver;
    plugins.forEach(p => {
      p.unregister().register();
    });
  });

  afterAll(() => {
    if (originalResizeObserver === undefined) {
      delete (window as Partial<typeof window>).ResizeObserver;
    } else {
      window.ResizeObserver = originalResizeObserver;
    }
  });

  beforeEach(() => {
    triggerResizeObserver([]); // Reset any pending resize observers
  });

  describe('includes ErrorBoundary', () => {
    let expectedErrors = 0;
    let actualErrors = 0;
    function onError(e: Event) {
      e.preventDefault();
      actualErrors += 1;
    }

    beforeEach(() => {
      expectedErrors = 0;
      actualErrors = 0;
      window.addEventListener('error', onError);
    });

    afterEach(() => {
      window.removeEventListener('error', onError);
    });

    test('should have correct number of errors', () => {
      expect(actualErrors).toBe(expectedErrors);
      expectedErrors = 0;
    });

    test('renders default FallbackComponent', async () => {
      expectedErrors = 1;
      render(
        <SuperChart
          chartType={ChartKeys.BUGGY}
          queriesData={[DEFAULT_QUERY_DATA]}
          width="200"
          height="200"
          theme={axbiTheme}
        />,
      );

      expect(
        await screen.findByText('Oops! An error occurred!'),
      ).toBeInTheDocument();
    });

    test('renders custom FallbackComponent', async () => {
      expectedErrors = 1;
      const CustomFallbackComponent = jest.fn(() => (
        <div>Custom Fallback!</div>
      ));

      render(
        <SuperChart
          chartType={ChartKeys.BUGGY}
          queriesData={[DEFAULT_QUERY_DATA]}
          width="200"
          height="200"
          theme={axbiTheme}
          FallbackComponent={CustomFallbackComponent}
        />,
      );

      expect(await screen.findByText('Custom Fallback!')).toBeInTheDocument();
      expect(CustomFallbackComponent).toHaveBeenCalled();
    });
    test('call onErrorBoundary', async () => {
      expectedErrors = 1;
      const handleError = jest.fn();
      render(
        <SuperChart
          chartType={ChartKeys.BUGGY}
          queriesData={[DEFAULT_QUERY_DATA]}
          width="200"
          height="200"
          theme={axbiTheme}
          onErrorBoundary={handleError}
        />,
      );

      await screen.findByText('Oops! An error occurred!');
      expect(handleError).toHaveBeenCalledTimes(1);
    });

    // Update the test cases
    test('does not include ErrorBoundary if told so', async () => {
      expectedErrors = 1;
      const inactiveErrorHandler = jest.fn();
      const activeErrorHandler = jest.fn();
      render(
        <ErrorBoundary
          fallbackRender={() => <div>Error!</div>}
          onError={activeErrorHandler}
        >
          <SuperChart
            disableErrorBoundary
            chartType={ChartKeys.BUGGY}
            queriesData={[DEFAULT_QUERY_DATA]}
            width="200"
            height="200"
            theme={axbiTheme}
            onErrorBoundary={inactiveErrorHandler}
          />
        </ErrorBoundary>,
      );

      await screen.findByText('Error!');
      expect(activeErrorHandler).toHaveBeenCalledTimes(1);
      expect(inactiveErrorHandler).not.toHaveBeenCalled();
    });
  });

  // Helper function to find elements by class name
  const findByClassName = (container: HTMLElement, className: string) =>
    container.querySelector(`.${className}`);

  // Update test cases
  // Update timeout for all async tests
  jest.setTimeout(10000);

  // Update the props test to wait for component to render
  test('passes the props to renderer correctly', async () => {
    const { container } = render(
      <SuperChart
        chartType={ChartKeys.DILIGENT}
        queriesData={[DEFAULT_QUERY_DATA]}
        width={101}
        height={118}
        theme={axbiTheme}
        formData={{ abc: 1 }}
      />,
    );

    await promiseTimeout(() => {
      const testComponent = findByClassName(container, 'test-component');
      expect(testComponent).not.toBeNull();
      expect(testComponent).toBeInTheDocument();
      expect(getDimensionText(container)).toBe('101x118');
    });
  });

  // Helper function to create a sized wrapper
  const createSizedWrapper = () => {
    const wrapper = document.createElement('div');
    wrapper.style.width = '300px';
    wrapper.style.height = '300px';
    wrapper.style.position = 'relative';
    wrapper.style.display = 'block';
    return wrapper;
  };

  jest.setTimeout(20000);

  const waitForDimensions = async (
    container: HTMLElement,
    expectedWidth: number,
    expectedHeight: number,
  ) =>
    waitFor(() => {
      const testComponent = container.querySelector('.test-component');
      const dimensionEl = container.querySelector('.dimension');

      expect(testComponent).toBeInTheDocument();
      expect(dimensionEl).toHaveTextContent(
        `${expectedWidth}x${expectedHeight}`,
      );
    });

  const triggerSuperChartResize = (width: number, height: number) => {
    act(() => {
      triggerResizeObserver([
        {
          contentRect: {
            width,
            height,
            top: 0,
            left: 0,
            right: width,
            bottom: height,
            x: 0,
            y: 0,
            toJSON() {
              return {
                width: this.width,
                height: this.height,
                top: this.top,
                left: this.left,
                right: this.right,
                bottom: this.bottom,
                x: this.x,
                y: this.y,
              };
            },
          },
          borderBoxSize: [{ blockSize: height, inlineSize: width }],
          contentBoxSize: [{ blockSize: height, inlineSize: width }],
          devicePixelContentBoxSize: [{ blockSize: height, inlineSize: width }],
          target: document.createElement('div'),
        },
      ]);
    });
  };

  test('works when width and height are percent', async () => {
    expect.hasAssertions();

    const { container } = render(
      <SuperChart
        chartType={ChartKeys.DILIGENT}
        queriesData={[DEFAULT_QUERY_DATA]}
        debounceTime={1}
        width="100%"
        height="100%"
        theme={axbiTheme}
      />,
    );

    triggerSuperChartResize(300, 300);

    await waitForDimensions(container, 300, 300);
  });

  test('passes the props with multiple queries to renderer correctly', async () => {
    const { container } = render(
      <SuperChart
        chartType={ChartKeys.DILIGENT}
        queriesData={DEFAULT_QUERIES_DATA}
        width={101}
        height={118}
        theme={axbiTheme}
        formData={{ abc: 1 }}
      />,
    );

    await promiseTimeout(() => {
      const testComponent = container.querySelector('.test-component');
      expect(testComponent).not.toBeNull();
      expect(testComponent).toBeInTheDocument();
      expect(getDimensionText(container)).toBe('101x118');
    });
  });

  describe('supports NoResultsComponent', () => {
    test('renders NoResultsComponent when queriesData is missing', () => {
      render(
        <SuperChart
          chartType={ChartKeys.DILIGENT}
          width="200"
          height="200"
          theme={axbiTheme}
        />,
      );

      expect(screen.getByText('No Results')).toBeInTheDocument();
    });

    test('renders NoResultsComponent when queriesData data is null', () => {
      render(
        <SuperChart
          chartType={ChartKeys.DILIGENT}
          queriesData={[{ data: null }]}
          width="200"
          height="200"
          theme={axbiTheme}
        />,
      );

      expect(screen.getByText('No Results')).toBeInTheDocument();
    });
  });

  describe('supports dynamic width and/or height', () => {
    // Add MyWrapper component definition
    function MyWrapper({ width, height, children }: WrapperProps) {
      return (
        <div>
          <div className="wrapper-insert">
            {width}x{height}
          </div>
          {children}
        </div>
      );
    }

    test('works with width and height that are numbers', async () => {
      const { container } = render(
        <SuperChart
          chartType={ChartKeys.DILIGENT}
          queriesData={[DEFAULT_QUERY_DATA]}
          width={100}
          height={100}
          theme={axbiTheme}
        />,
      );

      await promiseTimeout(() => {
        const testComponent = container.querySelector('.test-component');
        expect(testComponent).not.toBeNull();
        expect(testComponent).toBeInTheDocument();
        expect(getDimensionText(container)).toBe('100x100');
      });
    });

    test('works when width and height are percent', async () => {
      expect.hasAssertions();

      const wrapper = createSizedWrapper();
      document.body.appendChild(wrapper);

      const { container } = render(
        <div style={{ width: '100%', height: '100%', position: 'absolute' }}>
          <SuperChart
            chartType={ChartKeys.DILIGENT}
            queriesData={[DEFAULT_QUERY_DATA]}
            debounceTime={1}
            width="100%"
            height="100%"
            theme={axbiTheme}
            Wrapper={MyWrapper}
          />
        </div>,
      );

      wrapper.appendChild(container);

      triggerSuperChartResize(300, 300);

      await waitFor(() => {
        expect(container.querySelector('.wrapper-insert')).toHaveTextContent(
          '300x300',
        );
      });

      await waitForDimensions(container, 300, 300);

      document.body.removeChild(wrapper);
    }, 30000);
  });

  test('should render MatrixifyGridRenderer when matrixify is enabled with empty data', () => {
    const mockIsMatrixifyEnabled = isMatrixifyEnabled as jest.MockedFunction<
      typeof isMatrixifyEnabled
    >;
    const mockMatrixifyGridRenderer =
      MatrixifyGridRenderer as jest.MockedFunction<
        typeof MatrixifyGridRenderer
      >;

    mockIsMatrixifyEnabled.mockReturnValue(true);

    render(
      <SuperChart
        chartType={ChartKeys.DILIGENT}
        width="200"
        height="200"
        theme={axbiTheme}
        queriesData={[{ data: [] }]}
        enableNoResults
      />,
    );

    expect(mockMatrixifyGridRenderer).toHaveBeenCalled();
    expect(screen.queryByText('No Results')).not.toBeInTheDocument();
  });

  test('should render MatrixifyGridRenderer when matrixify is enabled with null data', () => {
    const mockIsMatrixifyEnabled = isMatrixifyEnabled as jest.MockedFunction<
      typeof isMatrixifyEnabled
    >;
    const mockMatrixifyGridRenderer =
      MatrixifyGridRenderer as jest.MockedFunction<
        typeof MatrixifyGridRenderer
      >;

    mockIsMatrixifyEnabled.mockReturnValue(true);

    render(
      <SuperChart
        chartType={ChartKeys.DILIGENT}
        width="200"
        height="200"
        theme={axbiTheme}
        queriesData={[{ data: null }]}
        enableNoResults
      />,
    );

    expect(mockMatrixifyGridRenderer).toHaveBeenCalled();
    expect(screen.queryByText('No Results')).not.toBeInTheDocument();
  });

  test('should ignore custom noResults component when matrixify is enabled', () => {
    const mockIsMatrixifyEnabled = isMatrixifyEnabled as jest.MockedFunction<
      typeof isMatrixifyEnabled
    >;
    const mockMatrixifyGridRenderer =
      MatrixifyGridRenderer as jest.MockedFunction<
        typeof MatrixifyGridRenderer
      >;

    mockIsMatrixifyEnabled.mockReturnValue(true);

    const CustomNoResults = () => <div>Custom No Data Message</div>;

    render(
      <SuperChart
        chartType={ChartKeys.DILIGENT}
        width="200"
        height="200"
        theme={axbiTheme}
        queriesData={[{ data: [] }]}
        enableNoResults
        noResults={<CustomNoResults />}
      />,
    );

    expect(mockMatrixifyGridRenderer).toHaveBeenCalled();
    expect(
      screen.queryByText('Custom No Data Message'),
    ).not.toBeInTheDocument();
  });

  test('should apply error boundary to matrixify grid renderer', () => {
    const mockIsMatrixifyEnabled = isMatrixifyEnabled as jest.MockedFunction<
      typeof isMatrixifyEnabled
    >;
    const mockMatrixifyGridRenderer =
      MatrixifyGridRenderer as jest.MockedFunction<
        typeof MatrixifyGridRenderer
      >;

    mockIsMatrixifyEnabled.mockReturnValue(true);
    const onErrorBoundary = jest.fn();

    render(
      <SuperChart
        chartType={ChartKeys.DILIGENT}
        width="200"
        height="200"
        theme={axbiTheme}
        queriesData={[{ data: [] }]}
        enableNoResults
        onErrorBoundary={onErrorBoundary}
      />,
    );

    expect(mockMatrixifyGridRenderer).toHaveBeenCalled();
    expect(onErrorBoundary).not.toHaveBeenCalled();
  });
});
