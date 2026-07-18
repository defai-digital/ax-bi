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
import { createRef } from 'react';
import { act, render, screen, userEvent } from '@ax-bi/ui-core/spec';
import { ModalTrigger, ModalTriggerRef } from '.';

const mockedProps = {
  triggerNode: <span>Trigger</span>,
};

test('should render', () => {
  const { container } = render(<ModalTrigger {...mockedProps} />);
  expect(container).toBeInTheDocument();
});

test('should render a button', () => {
  render(<ModalTrigger {...mockedProps} />);
  expect(screen.getByRole('button')).toBeInTheDocument();
});

test('should render a span element by default', () => {
  render(<ModalTrigger {...mockedProps} />);
  expect(screen.getByTestId('span-modal-trigger')).toBeInTheDocument();
});

test('should render a button element when specified', () => {
  const btnProps = {
    ...mockedProps,
    isButton: true,
  };
  render(<ModalTrigger {...btnProps} />);
  expect(screen.getByTestId('btn-modal-trigger')).toBeInTheDocument();
});

test('should render triggerNode', () => {
  render(<ModalTrigger {...mockedProps} />);
  expect(screen.getByText('Trigger')).toBeInTheDocument();
});

test('should render a tooltip on hover', async () => {
  const tooltipProps = {
    ...mockedProps,
    isButton: true,
    tooltip: 'I am a tooltip',
  };
  render(<ModalTrigger {...tooltipProps} />);

  await userEvent.hover(screen.getByRole('button'));
  expect(await screen.findByRole('tooltip')).toBeInTheDocument();
});

test('should not render a modal before click', () => {
  render(<ModalTrigger {...mockedProps} />);
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});

test('should render a modal after click', async () => {
  render(<ModalTrigger {...mockedProps} />);
  await userEvent.click(screen.getByRole('button'));
  expect(screen.getByRole('dialog')).toBeInTheDocument();
});

test('exposes open/close/showModal via ref without mutating during render', async () => {
  const ref = createRef<ModalTriggerRef['current']>();
  render(
    <ModalTrigger
      {...mockedProps}
      ref={ref}
      modalBody={<div>Modal body content</div>}
    />,
  );

  expect(ref.current).not.toBeNull();
  expect(ref.current?.showModal).toBe(false);
  expect(typeof ref.current?.open).toBe('function');
  expect(typeof ref.current?.close).toBe('function');

  // Imperative open must work without a DOM MouseEvent
  act(() => {
    ref.current?.open();
  });
  expect(await screen.findByRole('dialog')).toBeInTheDocument();
  expect(ref.current?.showModal).toBe(true);
  expect(screen.getByText('Modal body content')).toBeInTheDocument();

  act(() => {
    ref.current?.close();
  });
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(ref.current?.showModal).toBe(false);
});
