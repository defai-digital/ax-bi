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
import { render, screen, userEvent, waitFor } from '@superset-ui/core/spec';
import TooltipParagraph from '.';

// antd v6 Typography detects truncation with real layout APIs
// (getClientRects/canvas measurement) that jsdom cannot emulate, so the
// onEllipsis callback never fires on its own. Stub the Paragraph to drive
// the callback deterministically; the behavior under test is
// TooltipParagraph's own (truncated -> tooltip title).
let mockIsTruncated = false;
jest.mock('@superset-ui/core/components/Typography', () => {
  const actual = jest.requireActual(
    '@superset-ui/core/components/Typography',
  );
  const { useEffect } = jest.requireActual('react');
  const MockParagraph = ({ children, ellipsis, ...rest }: any) => {
    useEffect(() => {
      ellipsis?.onEllipsis?.(mockIsTruncated);
    }, [ellipsis]);
    return <div {...rest}>{children}</div>;
  };
  return {
    ...actual,
    Typography: {
      ...actual.Typography,
      Paragraph: MockParagraph,
    },
  };
});

beforeEach(() => {
  mockIsTruncated = false;
});

test('starts hidden with default props', () => {
  render(<TooltipParagraph>This is tooltip description.</TooltipParagraph>);
  expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
});

test('not render on hover when not truncated', async () => {
  render(
    <div style={{ width: '200px' }}>
      <TooltipParagraph>
        <span data-test="test-text">This is short</span>
      </TooltipParagraph>
    </div>,
  );

  await userEvent.hover(screen.getByTestId('test-text'));

  // Wait a moment for any potential tooltip to appear
  await new Promise(resolve => {
    setTimeout(resolve, 100);
  });

  // Check that no tooltip is visible in the document
  expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
});

test('render on hover when truncated', async () => {
  mockIsTruncated = true;
  render(
    <div style={{ width: '200px' }}>
      <TooltipParagraph>
        <span data-test="test-text">This is too long and should truncate.</span>
      </TooltipParagraph>
    </div>,
  );

  // Hover over the text (the tooltip body re-renders the children, so use
  // the first match — the trigger)
  await userEvent.hover(screen.getAllByTestId('test-text')[0]);

  // The trigger is described by the visible tooltip once truncated
  await waitFor(() => {
    const element = screen
      .getAllByTestId('test-text')[0]
      .closest('[aria-describedby]');
    expect(element).toHaveAttribute('aria-describedby');
  });
});
