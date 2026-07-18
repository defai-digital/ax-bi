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
import type { ReactNode } from 'react';

export interface BreadcrumbsItem {
  /** Crumb content (text or node). */
  label: ReactNode;
  /**
   * Link target for the crumb. Ignored on the last item, which is always
   * rendered as the current page without a link.
   */
  href?: string;
}

export interface BreadcrumbsProps {
  /** Ordered crumbs; the last item is treated as the current page. */
  items: BreadcrumbsItem[];
  /**
   * Optional SPA navigation handler. When provided, unmodified left clicks
   * on linked crumbs are intercepted (default prevented) and routed through
   * this callback; modifier clicks keep the native anchor behavior.
   */
  onNavigate?: (href: string) => void;
  /** Separator between crumbs. Defaults to '/'. */
  separator?: ReactNode;
  /** Test id forwarded to the breadcrumb nav element. */
  'data-test'?: string;
}
