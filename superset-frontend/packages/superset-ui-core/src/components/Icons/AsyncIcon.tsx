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

import { FC, SVGProps, forwardRef, useEffect, useState } from 'react';
import TransparentIcon from './svgs/transparent.svg';
import { IconType } from './types';
import { BaseIconComponent } from './BaseIcon';

type SvgModule = { default: FC<SVGProps<SVGSVGElement>> };

const iconLoaders: Record<string, () => Promise<SvgModule>> = {
  ballot: () => import('!!@svgr/webpack!src/assets/images/icons/ballot.svg'),
  big_number_chart_tile: () =>
    import('!!@svgr/webpack!src/assets/images/icons/big_number_chart_tile.svg'),
  binoculars: () =>
    import('!!@svgr/webpack!src/assets/images/icons/binoculars.svg'),
  category: () =>
    import('!!@svgr/webpack!src/assets/images/icons/category.svg'),
  certified: () =>
    import('!!@svgr/webpack!src/assets/images/icons/certified.svg'),
  checkbox_half: () =>
    import('!!@svgr/webpack!src/assets/images/icons/checkbox_half.svg'),
  checkbox_off: () =>
    import('!!@svgr/webpack!src/assets/images/icons/checkbox_off.svg'),
  checkbox_on: () =>
    import('!!@svgr/webpack!src/assets/images/icons/checkbox_on.svg'),
  circle_solid: () =>
    import('!!@svgr/webpack!src/assets/images/icons/circle_solid.svg'),
  drag: () => import('!!@svgr/webpack!src/assets/images/icons/drag.svg'),
  error_solid_small_red: () =>
    import('!!@svgr/webpack!src/assets/images/icons/error_solid_small_red.svg'),
  full: () => import('!!@svgr/webpack!src/assets/images/icons/full.svg'),
  layers: () => import('!!@svgr/webpack!src/assets/images/icons/layers.svg'),
  move: () => import('!!@svgr/webpack!src/assets/images/icons/move.svg'),
  multiple: () =>
    import('!!@svgr/webpack!src/assets/images/icons/multiple.svg'),
  queued: () => import('!!@svgr/webpack!src/assets/images/icons/queued.svg'),
  redo: () => import('!!@svgr/webpack!src/assets/images/icons/redo.svg'),
  running: () => import('!!@svgr/webpack!src/assets/images/icons/running.svg'),
  sigma: () => import('!!@svgr/webpack!src/assets/images/icons/sigma.svg'),
  square: () => import('!!@svgr/webpack!src/assets/images/icons/square.svg'),
  sort_asc: () =>
    import('!!@svgr/webpack!src/assets/images/icons/sort_asc.svg'),
  sort_desc: () =>
    import('!!@svgr/webpack!src/assets/images/icons/sort_desc.svg'),
  sort: () => import('!!@svgr/webpack!src/assets/images/icons/sort.svg'),
  triangle_down: () =>
    import('!!@svgr/webpack!src/assets/images/icons/triangle_down.svg'),
  undo: () => import('!!@svgr/webpack!src/assets/images/icons/undo.svg'),
};

const AsyncIcon = forwardRef<HTMLSpanElement, IconType>((props, ref) => {
  const [ImportedSVG, setImportedSVG] = useState<FC<SVGProps<SVGSVGElement>>>();
  const { fileName, customIcons, iconSize, iconColor, viewBox, ...restProps } =
    props;

  useEffect(() => {
    let cancelled = false;
    async function importIcon(): Promise<void> {
      const loader = fileName ? iconLoaders[fileName] : undefined;
      try {
        const Component = loader ? (await loader()).default : undefined;
        if (!cancelled) {
          setImportedSVG(() => Component);
        }
      } catch {
        if (!cancelled) {
          setImportedSVG(undefined);
        }
      }
    }
    importIcon();
    return () => {
      cancelled = true;
    };
  }, [fileName]);

  return (
    <BaseIconComponent
      ref={ref}
      component={ImportedSVG || TransparentIcon}
      fileName={fileName}
      customIcons={customIcons}
      iconSize={iconSize}
      iconColor={iconColor}
      viewBox={viewBox}
      {...restProps}
    />
  );
});

export default AsyncIcon;
