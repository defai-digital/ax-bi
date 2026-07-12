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

import '@testing-library/jest-dom';
import { render, fireEvent, waitFor } from '@testing-library/react';
import ReactCountryMap from '../src/ReactCountryMap';

const mockMapData = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { ISO: 'CAN', NAME_1: 'Canada' },
      geometry: {},
    },
  ],
};

type Projection = ((...args: unknown[]) => void) & {
  scale: () => Projection;
  center: () => Projection;
  translate: () => Projection;
};

const mockJson = jest.fn(() => Promise.resolve(mockMapData));

jest.mock('d3-fetch', () => ({
  json: (...args: unknown[]) => mockJson(...args),
}));

jest.mock('d3-selection', () => {
  const actual = jest.requireActual('d3-selection');
  return {
    ...actual,
    pointer: jest.fn(() => [100, 50]),
  };
});

jest.mock('d3-geo', () => {
  const proj = (() => {}) as Projection;
  proj.scale = () => proj;
  proj.center = () => proj;
  proj.translate = () => proj;

  const pathFn = Object.assign(
    jest.fn(() => 'M10 10 L20 20'),
    {
      projection: jest.fn(),
      bounds: jest.fn(() => [
        [0, 0],
        [100, 100],
      ]),
      centroid: jest.fn(() => [50, 50]),
    },
  );

  return {
    geoPath: jest.fn(() => pathFn),
    geoMercator: jest.fn(() => proj),
    geoCentroid: jest.fn(() => [0, 0]),
  };
});

jest.mock('d3-zoom', () => {
  // d3.selection.call(zoomBehavior) requires zoom() to return a function
  const zoomFn = jest.fn();
  zoomFn.scaleExtent = jest.fn().mockReturnValue(zoomFn);
  zoomFn.on = jest.fn().mockReturnValue(zoomFn);
  zoomFn.transform = jest.fn();
  return {
    zoom: jest.fn(() => zoomFn),
    zoomIdentity: {
      translate: (x = 0, y = 0) => ({
        scale: (k = 1) => ({
          toString: () => `translate(${x},${y}) scale(${k})`,
          x,
          y,
          k,
        }),
      }),
    },
  };
});

jest.mock('d3-color', () => {
  const actual = jest.requireActual('d3-color');
  return {
    ...actual,
    rgb: jest.fn((c: string) => {
      try {
        return actual.rgb(c);
      } catch {
        return {
          darker: () => ({ toString: () => c }),
          toString: () => c,
        };
      }
    }),
  };
});

describe('CountryMap (d3 v7)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockJson.mockImplementation(() => Promise.resolve(mockMapData));
  });

  test('renders a map after d3.json loads data', async () => {
    render(
      <ReactCountryMap
        width={500}
        height={300}
        data={[{ country_id: 'CAN', metric: 100 }]}
        country="canada"
        linearColorScheme="bnbColors"
        colorScheme=""
        numberFormat=".2f"
        formatter={jest.fn().mockReturnValue('100')}
      />,
    );

    await waitFor(() => {
      expect(mockJson).toHaveBeenCalledTimes(1);
      expect(document.querySelector('path.region')).not.toBeNull();
    });
  });

  test('shows tooltip on mouseenter/mousemove/mouseout', async () => {
    render(
      <ReactCountryMap
        width={500}
        height={300}
        data={[{ country_id: 'CAN', metric: 100 }]}
        country="canada"
        linearColorScheme="bnbColors"
        colorScheme=""
        formatter={jest.fn().mockReturnValue('100')}
      />,
    );

    await waitFor(() => {
      expect(document.querySelector('path.region')).not.toBeNull();
    });

    const region = document.querySelector('path.region');
    const popup = document.querySelector('.hover-popup');
    expect(popup).not.toBeNull();

    fireEvent.mouseEnter(region!);
    expect(popup!).toHaveStyle({ display: 'block' });

    fireEvent.mouseOut(region!);
    expect(popup!).toHaveStyle({ display: 'none' });
  });

  test('emits a cross-filter data mask when a region is clicked', async () => {
    const setDataMask = jest.fn();

    render(
      <ReactCountryMap
        width={500}
        height={300}
        data={[{ country_id: 'CAN', metric: 100 }]}
        country="canada"
        linearColorScheme="bnbColors"
        colorScheme=""
        formatter={jest.fn().mockReturnValue('100')}
        entity="country_code"
        emitCrossFilters
        setDataMask={setDataMask}
        filterState={{ selectedValues: [] }}
      />,
    );

    await waitFor(() => {
      expect(document.querySelector('path.region')).not.toBeNull();
    });

    const region = document.querySelector('path.region');
    fireEvent.mouseDown(region!);
    fireEvent.click(region!);

    expect(setDataMask).toHaveBeenCalledTimes(1);
    expect(setDataMask).toHaveBeenCalledWith(
      expect.objectContaining({
        extraFormData: {
          filters: [{ col: 'country_code', op: 'IN', val: ['CAN'] }],
        },
        filterState: expect.objectContaining({ value: ['CAN'] }),
      }),
    );
  });

  test('does not emit a cross-filter when emitCrossFilters is disabled', async () => {
    const setDataMask = jest.fn();

    render(
      <ReactCountryMap
        width={500}
        height={300}
        data={[{ country_id: 'CAN', metric: 100 }]}
        country="canada"
        linearColorScheme="bnbColors"
        colorScheme=""
        formatter={jest.fn().mockReturnValue('100')}
        entity="country_code"
        emitCrossFilters={false}
        setDataMask={setDataMask}
        filterState={{ selectedValues: [] }}
      />,
    );

    await waitFor(() => {
      expect(document.querySelector('path.region')).not.toBeNull();
    });

    const region = document.querySelector('path.region');
    fireEvent.mouseDown(region!);
    fireEvent.click(region!);

    expect(setDataMask).not.toHaveBeenCalled();
  });

  test('opens the context menu with drill-by keyed on the entity control', async () => {
    const onContextMenu = jest.fn();

    render(
      <ReactCountryMap
        width={500}
        height={300}
        data={[{ country_id: 'CAN', metric: 100 }]}
        country="canada"
        linearColorScheme="bnbColors"
        colorScheme=""
        formatter={jest.fn().mockReturnValue('100')}
        entity="country_code"
        onContextMenu={onContextMenu}
        filterState={{ selectedValues: [] }}
      />,
    );

    await waitFor(() => {
      expect(document.querySelector('path.region')).not.toBeNull();
    });

    const region = document.querySelector('path.region');
    fireEvent.contextMenu(region!, { clientX: 123, clientY: 45 });

    expect(onContextMenu).toHaveBeenCalledTimes(1);
    const [[clientX, clientY, payload]] = onContextMenu.mock.calls;
    expect(clientX).toBe(123);
    expect(clientY).toBe(45);
    expect(payload.drillToDetail).toEqual([
      { col: 'country_code', op: '==', val: 'CAN', formattedVal: 'CAN' },
    ]);
    expect(payload.drillBy).toEqual({
      filters: [{ col: 'country_code', op: '==', val: 'CAN' }],
      groupbyFieldName: 'entity',
    });
  });
});
