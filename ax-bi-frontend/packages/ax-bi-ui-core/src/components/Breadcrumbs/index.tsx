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
import type { MouseEvent } from 'react';
import { styled } from '@ax-bi/core/theme';
import { Breadcrumb } from 'antd';
import type { BreadcrumbsItem, BreadcrumbsProps } from './types';

const StyledBreadcrumb = styled(Breadcrumb)`
  ${({ theme }) => `
    font-size: ${theme.fontSizeSM}px;
  `}
`;

const isUnmodifiedLeftClick = (event: MouseEvent<HTMLAnchorElement>) =>
  event.button === 0 &&
  !event.metaKey &&
  !event.ctrlKey &&
  !event.shiftKey &&
  !event.altKey;

export const Breadcrumbs = ({
  items,
  onNavigate,
  separator = '/',
  'data-test': dataTest,
}: BreadcrumbsProps) => (
  <StyledBreadcrumb
    data-test={dataTest}
    separator={separator}
    items={items.map((item: BreadcrumbsItem, index: number) => {
      const isCurrentPage = index === items.length - 1;
      if (isCurrentPage || !item.href) {
        return { title: item.label };
      }
      const { href } = item;
      return {
        title: (
          <a
            href={href}
            onClick={
              onNavigate
                ? (event: MouseEvent<HTMLAnchorElement>) => {
                    if (isUnmodifiedLeftClick(event)) {
                      event.preventDefault();
                      onNavigate(href);
                    }
                  }
                : undefined
            }
          >
            {item.label}
          </a>
        ),
      };
    })}
  />
);

export type { BreadcrumbsItem, BreadcrumbsProps } from './types';
