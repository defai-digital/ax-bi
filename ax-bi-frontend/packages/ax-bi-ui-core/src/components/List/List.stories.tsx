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

import { List } from '.';

export default {
  title: 'Components/List',
  component: List,
};

/** Object items avoid antd List `rowKey` / `keyof string` TS6 issues. */
type ListItem = { key: string; title: string };

const dataSource: ListItem[] = [
  { key: '1', title: 'Item 1' },
  { key: '2', title: 'Item 2' },
  { key: '3', title: 'Item 3' },
];

type StoryArgs = {
  bordered?: boolean;
  split?: boolean;
  size?: 'default' | 'small' | 'large';
  loading?: boolean;
};

export const InteractiveList = (args: StoryArgs) => (
  <List<ListItem>
    bordered={args.bordered}
    split={args.split}
    size={args.size}
    loading={args.loading}
    dataSource={dataSource}
    rowKey="key"
    renderItem={item => <List.Item>{item.title}</List.Item>}
  />
);

InteractiveList.args = {
  bordered: false,
  split: true,
  size: 'default',
  loading: false,
};

InteractiveList.argTypes = {
  bordered: {
    control: { type: 'boolean' },
    description: 'Whether to show a border around the list.',
  },
  split: {
    control: { type: 'boolean' },
    description: 'Whether to show a divider between items.',
  },
  loading: {
    control: { type: 'boolean' },
    description: 'Whether to show a loading indicator.',
  },
  size: {
    control: { type: 'select' },
    options: ['default', 'small', 'large'],
    description: 'Size of the list.',
  },
};

InteractiveList.parameters = {
  docs: {
    description: {
      story:
        'A list component for displaying rows of data. Requires dataSource array and renderItem function.',
    },
    staticProps: {
      dataSource: [
        { key: '1', title: 'Dashboard Analytics' },
        { key: '2', title: 'User Management' },
        { key: '3', title: 'Data Sources' },
      ],
    },
    liveExample: `function Demo() {
  const data = [
    { key: '1', title: 'Dashboard Analytics' },
    { key: '2', title: 'User Management' },
    { key: '3', title: 'Data Sources' },
  ];
  return (
    <List
      bordered
      dataSource={data}
      rowKey="key"
      renderItem={(item) => <List.Item>{item.title}</List.Item>}
    />
  );
}`,
  },
};

export const InteractiveListWithPagination = (args: StoryArgs) => (
  <List<ListItem>
    bordered={args.bordered}
    split={args.split}
    size={args.size}
    loading={args.loading}
    dataSource={dataSource}
    rowKey="key"
    renderItem={item => <List.Item>{item.title}</List.Item>}
    pagination={{ pageSize: 2 }}
  />
);

InteractiveListWithPagination.args = {
  ...InteractiveList.args,
};

InteractiveListWithPagination.argTypes = {
  ...InteractiveList.argTypes,
};
