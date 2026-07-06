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
import { render, screen } from 'spec/helpers/testing-library';
import userEvent from '@testing-library/user-event';
import NumericalRangeFilter from './NumericalRange';

jest.mock('@superset-ui/core/components/Input', () => ({
  ...jest.requireActual('@superset-ui/core/components/Input'),
  InputNumber: ({
    value,
    onChange,
    min,
    max,
    ...props
  }: {
    value: number | null;
    onChange: (value: number | null) => void;
    min?: number;
    max?: number;
    [key: string]: unknown;
  }) => (
    <input
      {...props}
      type="number"
      value={value ?? ''}
      min={min}
      max={max}
      onChange={event =>
        onChange(event.target.value === '' ? null : Number(event.target.value))
      }
    />
  ),
}));

test('forwards accessible names and configured bounds to numeric inputs', async () => {
  const onSubmit = jest.fn();

  render(
    <NumericalRangeFilter
      Header="Age range"
      name="age_range"
      initialValue={[null, null]}
      min={18}
      max={99}
      onSubmit={onSubmit}
    />,
  );

  const minInput = screen.getByRole('spinbutton', {
    name: /age range minimum/i,
  });
  const maxInput = screen.getByRole('spinbutton', {
    name: /age range maximum/i,
  });

  expect(minInput).toHaveAttribute('min', '18');
  expect(minInput).toHaveAttribute('max', '99');
  expect(maxInput).toHaveAttribute('min', '18');
  expect(maxInput).toHaveAttribute('max', '99');

  await userEvent.type(minInput, '21');
  expect(onSubmit).toHaveBeenLastCalledWith([21, null]);
});
