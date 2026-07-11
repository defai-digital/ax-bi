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
import { useMemo, useState } from 'react';
import { t } from '@apache-superset/core/translation';
import { styled } from '@apache-superset/core/theme';
import { Button } from '@superset-ui/core/components';
import { Icons } from '@superset-ui/core/components/Icons';
import { navigateTo } from 'src/utils/navigationUtils';
import {
  AXBIEmptyCallout,
  AXBIEmptyCalloutText,
  AXBIEmptyCalloutTitle,
  AXBIActionRow,
} from 'src/components/AXBIWorkspace';

const STORAGE_KEY = 'home__onboarding_checklist_dismissed';

const List = styled.ol`
  margin: ${({ theme }) => theme.sizeUnit * 3}px 0 0;
  padding-left: ${({ theme }) => theme.sizeUnit * 5}px;
  color: ${({ theme }) => theme.colorText};
  line-height: 1.6;
`;

const Item = styled.li`
  margin-bottom: ${({ theme }) => theme.sizeUnit * 2}px;

  button {
    appearance: none;
    border: none;
    background: none;
    padding: 0;
    color: ${({ theme }) => theme.colorPrimary};
    font-weight: ${({ theme }) => theme.fontWeightStrong};
    cursor: pointer;
    text-decoration: underline;
  }
`;

const Done = styled.span`
  color: ${({ theme }) => theme.colorSuccess};
  margin-right: ${({ theme }) => theme.sizeUnit}px;
`;

export interface OnboardingChecklistProps {
  canUploadData: boolean;
  hasChart: boolean;
  hasDashboard: boolean;
  onOpenSearch?: () => void;
}

function isDismissed(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === '1';
  } catch {
    return false;
  }
}

function dismiss(): void {
  try {
    localStorage.setItem(STORAGE_KEY, '1');
  } catch {
    // ignore quota / private mode
  }
}

/**
 * First-15-minutes checklist. Hidden once dismissed or when all steps done.
 */
export default function OnboardingChecklist({
  canUploadData,
  hasChart,
  hasDashboard,
  onOpenSearch,
}: OnboardingChecklistProps) {
  const [hidden, setHidden] = useState(isDismissed);

  const steps = useMemo(
    () => [
      {
        id: 'data',
        done: hasChart || hasDashboard,
        label: canUploadData
          ? t('Upload a file or pick a dataset')
          : t('Open a dataset and explore it'),
        action: () =>
          navigateTo(canUploadData ? '/upload/' : '/tablemodelview/list/'),
      },
      {
        id: 'chart',
        done: hasChart,
        label: t('Create your first chart'),
        action: () => navigateTo('/chart/add'),
      },
      {
        id: 'dashboard',
        done: hasDashboard,
        label: t('Save a dashboard'),
        action: () => navigateTo('/dashboard/new/', { assign: true }),
      },
      {
        id: 'search',
        done: false,
        label: t('Try search (⌘K / Ctrl+K)'),
        action: () => onOpenSearch?.(),
      },
    ],
    [canUploadData, hasChart, hasDashboard, onOpenSearch],
  );

  const allCoreDone = hasChart && hasDashboard;

  if (hidden || allCoreDone) {
    return null;
  }

  return (
    <AXBIEmptyCallout data-test="home-onboarding-checklist">
      <AXBIEmptyCalloutTitle>{t('Get started')}</AXBIEmptyCalloutTitle>
      <AXBIEmptyCalloutText>
        {t('A short path from data to a shareable dashboard.')}
      </AXBIEmptyCalloutText>
      <List>
        {steps.map(step => (
          <Item key={step.id}>
            {step.done ? <Done aria-hidden>✓</Done> : null}
            <button type="button" onClick={step.action}>
              {step.label}
            </button>
          </Item>
        ))}
      </List>
      <AXBIActionRow style={{ marginTop: 12 }}>
        <Button
          buttonStyle="link"
          icon={<Icons.CloseOutlined />}
          onClick={() => {
            dismiss();
            setHidden(true);
          }}
          data-test="onboarding-dismiss"
        >
          {t('Dismiss')}
        </Button>
      </AXBIActionRow>
    </AXBIEmptyCallout>
  );
}
