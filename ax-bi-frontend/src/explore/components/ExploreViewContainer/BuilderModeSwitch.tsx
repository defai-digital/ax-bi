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
import { styled, css } from '@ax-bi/core/theme';
import { t } from '@ax-bi/core/translation';
import { Radio, Tooltip } from '@ax-bi/ui-core/components';
import { Icons } from '@ax-bi/ui-core/components/Icons';

export type BuilderMode = 'guided' | 'advanced';

export interface BuilderModeSwitchProps {
  mode: BuilderMode;
  onChange: (mode: BuilderMode) => void;
  /** Whether the active viz type has guided builder support. */
  guidedAvailable: boolean;
}

const UnavailableChip = styled.span`
  ${({ theme }) => css`
    display: inline-flex;
    align-items: center;
    gap: ${theme.sizeUnit}px;
    color: ${theme.colorTextSecondary};
    font-size: ${theme.fontSizeSM}px;
    white-space: nowrap;
  `}
`;

/** Explicit Guided ⇄ Advanced switch for the Explore builder. Chart types
 * without guided support get a subtle info chip instead of the switch. */
export default function BuilderModeSwitch({
  mode,
  onChange,
  guidedAvailable,
}: BuilderModeSwitchProps) {
  if (!guidedAvailable) {
    return (
      <Tooltip title={t('Guided builder is not available for this chart type')}>
        <UnavailableChip data-test="guided-builder-unavailable">
          <Icons.InfoCircleOutlined iconSize="s" />
          {t('Guided unavailable')}
        </UnavailableChip>
      </Tooltip>
    );
  }
  return (
    <Radio.Group
      data-test="builder-mode-switch"
      size="small"
      value={mode}
      onChange={event => onChange(event.target.value as BuilderMode)}
    >
      <Radio.Button value="guided">{t('Guided')}</Radio.Button>
      <Radio.Button value="advanced">{t('Advanced')}</Radio.Button>
    </Radio.Group>
  );
}
