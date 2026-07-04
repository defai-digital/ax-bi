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
import MockResizeObserver, {
  triggerResizeObserver,
} from 'resize-observer-polyfill';
import { WithLegend } from '@superset-ui/core';
import { act, render, waitFor } from '@testing-library/react';

let renderChart = jest.fn();
let renderLegend = jest.fn();

describe('WithLegend', () => {
  let originalResizeObserver: typeof window.ResizeObserver | undefined;

  beforeAll(() => {
    originalResizeObserver = window.ResizeObserver;
    window.ResizeObserver =
      MockResizeObserver as unknown as typeof window.ResizeObserver;
  });

  afterAll(() => {
    if (originalResizeObserver === undefined) {
      delete (window as Partial<typeof window>).ResizeObserver;
    } else {
      window.ResizeObserver = originalResizeObserver;
    }
  });

  beforeEach(() => {
    renderChart = jest.fn(() => <div className="chart" />);
    renderLegend = jest.fn(() => <div className="legend" />);
    triggerResizeObserver([]);
  });

  function triggerLegendResize(width = 300, height = 300) {
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
  }

  async function expectChartRendered(
    container: HTMLElement,
    expectedWidth = 300,
    expectedHeight = 300,
  ) {
    await waitFor(() => {
      expect(renderChart).toHaveBeenCalledWith(
        expect.objectContaining({
          width: expectedWidth,
          height: expectedHeight,
        }),
      );
      expect(container.querySelectorAll('div.chart')).toHaveLength(1);
    });
  }

  test('sets className', async () => {
    const { container } = render(
      <WithLegend
        className="test-class"
        renderChart={renderChart}
        renderLegend={renderLegend}
      />,
    );

    expect(container.querySelectorAll('.test-class')).toHaveLength(1);
    triggerLegendResize();
    await expectChartRendered(container);
  });

  test('renders when renderLegend is not set', async () => {
    const { container } = render(
      <WithLegend
        debounceTime={1}
        width={500}
        height={500}
        renderChart={renderChart}
      />,
    );

    triggerLegendResize();
    await expectChartRendered(container);
    expect(container.querySelectorAll('div.legend')).toHaveLength(0);
  });

  test('renders', async () => {
    const { container } = render(
      <WithLegend
        debounceTime={1}
        width={500}
        height={500}
        renderChart={renderChart}
        renderLegend={renderLegend}
      />,
    );

    triggerLegendResize();
    await expectChartRendered(container);
    expect(renderLegend).toHaveBeenCalledWith({ direction: 'row' });
    expect(container.querySelectorAll('div.legend')).toHaveLength(1);
  });

  test('renders without width or height', async () => {
    const { container } = render(
      <WithLegend
        debounceTime={1}
        renderChart={renderChart}
        renderLegend={renderLegend}
      />,
    );

    triggerLegendResize();
    await expectChartRendered(container);
    expect(renderLegend).toHaveBeenCalledWith({ direction: 'row' });
    expect(container.querySelectorAll('div.legend')).toHaveLength(1);
  });

  test('renders legend on the left', async () => {
    const { container } = render(
      <WithLegend
        debounceTime={1}
        position="left"
        renderChart={renderChart}
        renderLegend={renderLegend}
      />,
    );

    triggerLegendResize();
    await expectChartRendered(container);
    expect(renderLegend).toHaveBeenCalledWith({ direction: 'column' });
    expect(container.querySelector('.with-legend')).toHaveStyle({
      flexDirection: 'row',
    });
  });

  test('renders legend on the right', async () => {
    const { container } = render(
      <WithLegend
        debounceTime={1}
        position="right"
        renderChart={renderChart}
        renderLegend={renderLegend}
      />,
    );

    triggerLegendResize();
    await expectChartRendered(container);
    expect(renderLegend).toHaveBeenCalledWith({ direction: 'column' });
    expect(container.querySelector('.with-legend')).toHaveStyle({
      flexDirection: 'row-reverse',
    });
  });

  test('renders legend on the top', async () => {
    const { container } = render(
      <WithLegend
        debounceTime={1}
        position="top"
        renderChart={renderChart}
        renderLegend={renderLegend}
      />,
    );

    triggerLegendResize();
    await expectChartRendered(container);
    expect(renderLegend).toHaveBeenCalledWith({ direction: 'row' });
    expect(container.querySelector('.with-legend')).toHaveStyle({
      flexDirection: 'column',
    });
  });

  test('renders legend on the bottom', async () => {
    const { container } = render(
      <WithLegend
        debounceTime={1}
        position="bottom"
        renderChart={renderChart}
        renderLegend={renderLegend}
      />,
    );

    triggerLegendResize();
    await expectChartRendered(container);
    expect(renderLegend).toHaveBeenCalledWith({ direction: 'row' });
    expect(container.querySelector('.with-legend')).toHaveStyle({
      flexDirection: 'column-reverse',
    });
  });

  test('renders legend with justifyContent set', async () => {
    const { container } = render(
      <WithLegend
        debounceTime={1}
        position="right"
        legendJustifyContent="flex-start"
        renderChart={renderChart}
        renderLegend={renderLegend}
      />,
    );

    triggerLegendResize();
    await expectChartRendered(container);
    expect(container.querySelector('.legend-container')).toHaveStyle({
      justifyContent: 'flex-start',
    });
  });
});
