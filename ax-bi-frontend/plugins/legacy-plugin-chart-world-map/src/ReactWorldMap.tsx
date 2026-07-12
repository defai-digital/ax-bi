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
import { reactify } from '@ax-bi/ui-core';
import { styled, useTheme } from '@ax-bi/core/theme';
import WorldMap from './WorldMap';

// Type-erase the render function to allow flexible prop spreading in the wrapper.
// The WorldMap render function has typed props, but the wrapper passes props via spread
// which TypeScript cannot verify at compile time. Props are validated at runtime.
const ReactWorldMap = reactify(
  WorldMap as unknown as (
    container: HTMLDivElement,
    props: Record<string, unknown>,
  ) => void,
);

interface WorldMapComponentProps {
  className: string;
  [key: string]: unknown;
}

const WorldMapComponent = ({
  className,
  ...otherProps
}: WorldMapComponentProps) => {
  const theme = useTheme();
  return (
    <div className={className}>
      <ReactWorldMap {...otherProps} theme={theme} />
    </div>
  );
};

export default styled(WorldMapComponent)`
  .axbi-legacy-chart-world-map {
    position: relative;
    svg {
      background-color: ${({ theme }) => theme.colorBgLayout};
    }
    .world-map-inline-legend {
      position: absolute;
      left: ${({ theme }) => theme.sizeUnit * 3}px;
      bottom: ${({ theme }) => theme.sizeUnit * 3}px;
      z-index: 1;
      max-width: min(
        360px,
        calc(100% - ${({ theme }) => theme.sizeUnit * 6}px)
      );
      padding: ${({ theme }) => theme.sizeUnit * 2}px
        ${({ theme }) => theme.sizeUnit * 3}px;
      border: 1px solid;
      border-radius: ${({ theme }) => theme.borderRadius}px;
      box-shadow: ${({ theme }) => theme.boxShadowSecondary};
      font-size: ${({ theme }) => theme.fontSizeSM}px;
      line-height: 1.35;
      pointer-events: none;
    }
    .world-map-inline-legend-title {
      margin-bottom: ${({ theme }) => theme.sizeUnit}px;
      font-weight: ${({ theme }) => theme.fontWeightStrong};
    }
    .world-map-inline-legend-row {
      display: flex;
      align-items: center;
      gap: ${({ theme }) => theme.sizeUnit * 1.5}px;
      margin-top: ${({ theme }) => theme.sizeUnit}px;
      white-space: normal;
    }
    .world-map-inline-legend-gradient {
      display: inline-block;
      flex: 0 0 ${({ theme }) => theme.sizeUnit * 10}px;
      height: ${({ theme }) => theme.sizeUnit * 2}px;
      border-radius: ${({ theme }) => theme.borderRadius}px;
    }
    .world-map-inline-legend-bubble {
      display: inline-block;
      flex: 0 0 ${({ theme }) => theme.sizeUnit * 3}px;
      width: ${({ theme }) => theme.sizeUnit * 3}px;
      height: ${({ theme }) => theme.sizeUnit * 3}px;
      border: 2px solid;
      border-radius: 50%;
      opacity: 0.65;
    }
    .world-map-inline-legend-empty {
      display: inline-block;
      flex: 0 0 ${({ theme }) => theme.sizeUnit * 5}px;
      height: ${({ theme }) => theme.sizeUnit * 2}px;
      border-radius: ${({ theme }) => theme.borderRadius}px;
    }
  }
  .hoverinfo {
    background-color: ${({ theme }) => theme.colorBgElevated};
    color: ${({ theme }) => theme.colorTextSecondary};
  }
`;
