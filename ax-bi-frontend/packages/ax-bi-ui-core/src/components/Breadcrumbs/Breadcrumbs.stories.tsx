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

import { Breadcrumbs } from '.';
import type { BreadcrumbsProps } from '.';

export default {
  title: 'Components/Breadcrumbs',
  component: Breadcrumbs,
  parameters: {
    docs: {
      description: {
        component:
          'Subtle navigation trail rendered above page headers. The last ' +
          'item is the current page and is never linked. Pass `onNavigate` ' +
          'to route clicks through the SPA history instead of full page ' +
          'loads; modifier clicks keep the native anchor behavior.',
      },
    },
  },
};

const demoItems = [
  { label: 'Dashboards', href: '/dashboard/list/' },
  { label: 'Sales dashboard' },
];

export const InteractiveBreadcrumbs = (args: BreadcrumbsProps) => (
  <Breadcrumbs {...args} />
);

InteractiveBreadcrumbs.args = {
  items: demoItems,
  separator: '/',
};

InteractiveBreadcrumbs.argTypes = {
  items: {
    control: false,
    description:
      'Ordered crumbs ({ label, href? }); the last item is the current page.',
  },
  separator: {
    control: 'text',
    description: 'Separator between crumbs.',
  },
  onNavigate: { action: 'onNavigate' },
};

export const ThreeLevels = () => (
  <Breadcrumbs
    items={[
      { label: 'Charts', href: '/chart/list/' },
      { label: 'Age distribution of respondents' },
    ]}
  />
);

ThreeLevels.parameters = {
  docs: {
    description: {
      story:
        'Typical usage above an editor header: section link plus the ' +
        'current resource name.',
    },
  },
};
