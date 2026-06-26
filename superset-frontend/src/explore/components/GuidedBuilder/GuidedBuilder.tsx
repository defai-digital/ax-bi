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
import { JsonObject } from '@superset-ui/core';
import { styled, css } from '@apache-superset/core/theme';
import { t } from '@apache-superset/core/translation';
import { Button, Input, Select } from '@superset-ui/core/components';
import { Icons } from '@superset-ui/core/components/Icons';
import {
  DISABLE_INPUT_OPERATORS,
  OPERATOR_ENUM_TO_OPERATOR_TYPE,
  Operators,
} from 'src/explore/constants';
import { GuidedFilter, GuidedIntent } from './types';
import { getVizDescriptor, VIZ_DESCRIPTORS } from './vizDescriptors';
import { compileIntent } from './compileIntent';
import { intentFromFormData } from './intentFromFormData';

/** Minimal shape of the columns/metrics the guided builder reads from the
 * explore datasource. Kept local to avoid coupling to the full Dataset type. */
interface DatasourceColumn {
  column_name: string;
  verbose_name?: string | null;
}
interface DatasourceMetric {
  metric_name: string;
  verbose_name?: string | null;
}
interface GuidedDatasource {
  columns?: DatasourceColumn[];
  metrics?: DatasourceMetric[];
}

export interface GuidedBuilderProps {
  formData: JsonObject;
  datasource?: GuidedDatasource;
  actions: {
    setControlValue: (controlName: string, value: unknown) => void;
  };
  onQuery: () => void;
  onSwitchToAdvanced: () => void;
  isLoading?: boolean;
}

/** Operators offered in the guided filter builder — the common subset; the
 * advanced filter popover exposes the full set. */
const GUIDED_OPERATORS: Operators[] = [
  Operators.Equals,
  Operators.NotEquals,
  Operators.In,
  Operators.NotIn,
  Operators.GreaterThan,
  Operators.LessThan,
  Operators.GreaterThanOrEqual,
  Operators.LessThanOrEqual,
  Operators.Like,
  Operators.IsNull,
  Operators.IsNotNull,
];

const ROW_LIMIT_OPTIONS = [10, 50, 100, 250, 500, 1000, 5000, 10000];

const Section = styled.div`
  ${({ theme }) => css`
    margin-bottom: ${theme.sizeUnit * 4}px;
    display: flex;
    flex-direction: column;
    gap: ${theme.sizeUnit}px;
  `}
`;

const SectionLabel = styled.div`
  ${({ theme }) => css`
    font-weight: ${theme.fontWeightStrong};
    color: ${theme.colorText};
  `}
`;

const FilterRow = styled.div`
  ${({ theme }) => css`
    display: flex;
    gap: ${theme.sizeUnit}px;
    align-items: center;
    margin-bottom: ${theme.sizeUnit}px;
  `}
`;

const Container = styled.div`
  ${({ theme }) => css`
    padding: ${theme.sizeUnit * 4}px;
    height: 100%;
    overflow: auto;
  `}
`;

const Footer = styled.div`
  ${({ theme }) => css`
    display: flex;
    gap: ${theme.sizeUnit * 2}px;
    align-items: center;
    margin-top: ${theme.sizeUnit * 2}px;
  `}
`;

export default function GuidedBuilder({
  formData,
  datasource,
  actions,
  onQuery,
  onSwitchToAdvanced,
  isLoading,
}: GuidedBuilderProps) {
  // Initialise from current form_data so an existing chart (or one round-tripped
  // through the advanced panel) opens with its selections intact.
  const [intent, setIntent] = useState<GuidedIntent>(() =>
    intentFromFormData(formData),
  );

  const descriptor = getVizDescriptor(intent.vizType);

  const metricOptions = useMemo(
    () =>
      (datasource?.metrics ?? []).map(m => ({
        label: m.verbose_name || m.metric_name,
        value: m.metric_name,
      })),
    [datasource?.metrics],
  );
  const columnOptions = useMemo(
    () =>
      (datasource?.columns ?? []).map(c => ({
        label: c.verbose_name || c.column_name,
        value: c.column_name,
      })),
    [datasource?.columns],
  );
  const vizOptions = useMemo(
    () => VIZ_DESCRIPTORS.map(d => ({ label: d.label, value: d.key })),
    [],
  );
  const operatorOptions = useMemo(
    () =>
      GUIDED_OPERATORS.map(op => ({
        label: OPERATOR_ENUM_TO_OPERATOR_TYPE[op].display,
        value: op,
      })),
    [],
  );

  // Apply an updated intent: sync local state and push every compiled control
  // value into Redux so the advanced panel, save flow and query all see the
  // same form_data. viz_type is set first so dependent controls recompute.
  const apply = (next: GuidedIntent) => {
    setIntent(next);
    const compiled = compileIntent(next);
    actions.setControlValue('viz_type', compiled.viz_type);
    Object.entries(compiled).forEach(([key, value]) => {
      if (key !== 'viz_type') {
        actions.setControlValue(key, value);
      }
    });
  };

  const updateFilter = (index: number, patch: Partial<GuidedFilter>) =>
    apply({
      ...intent,
      filters: intent.filters.map((f, i) =>
        i === index ? { ...f, ...patch } : f,
      ),
    });

  const addFilter = () => {
    const firstColumn = columnOptions[0]?.value ?? '';
    apply({
      ...intent,
      filters: [
        ...intent.filters,
        { column: firstColumn, operatorId: Operators.Equals, value: '' },
      ],
    });
  };

  const removeFilter = (index: number) =>
    apply({
      ...intent,
      filters: intent.filters.filter((_, i) => i !== index),
    });

  const showMeasures = descriptor && descriptor.measures !== 'none';
  const measuresMulti = descriptor?.measures === 'multi';
  const showDimensions = descriptor && descriptor.dimensions !== 'none';

  return (
    <Container data-test="guided-builder">
      <Section>
        <SectionLabel>{t('Visualization')}</SectionLabel>
        <Select
          ariaLabel={t('Visualization type')}
          options={vizOptions}
          value={intent.vizType}
          onChange={value => apply({ ...intent, vizType: value as string })}
        />
      </Section>

      {showMeasures && (
        <Section>
          <SectionLabel>{t('Measure')}</SectionLabel>
          <Select
            ariaLabel={t('Measures')}
            mode={measuresMulti ? 'multiple' : 'single'}
            allowClear
            options={metricOptions}
            placeholder={t('Add a measure')}
            value={measuresMulti ? intent.measures : intent.measures[0]}
            onChange={value =>
              apply({
                ...intent,
                measures: measuresMulti
                  ? ((value as string[]) ?? [])
                  : value
                    ? [value as string]
                    : [],
              })
            }
          />
        </Section>
      )}

      {showDimensions && (
        <Section>
          <SectionLabel>
            {descriptor?.hasXAxis ? t('X-axis & breakdown') : t('Group by')}
          </SectionLabel>
          <Select
            ariaLabel={t('Group by')}
            mode="multiple"
            allowClear
            options={columnOptions}
            placeholder={t('Add a dimension')}
            value={intent.dimensions}
            onChange={value =>
              apply({ ...intent, dimensions: (value as string[]) ?? [] })
            }
          />
        </Section>
      )}

      <Section>
        <SectionLabel>{t('Filters')}</SectionLabel>
        {intent.filters.map((filter, index) => {
          const valueless = DISABLE_INPUT_OPERATORS.includes(filter.operatorId);
          return (
            // eslint-disable-next-line react/no-array-index-key
            <FilterRow key={index}>
              <Select
                ariaLabel={t('Filter column')}
                options={columnOptions}
                value={filter.column}
                css={css`
                  flex: 2;
                `}
                onChange={value =>
                  updateFilter(index, { column: value as string })
                }
              />
              <Select
                ariaLabel={t('Filter operator')}
                options={operatorOptions}
                value={filter.operatorId}
                css={css`
                  flex: 2;
                `}
                onChange={value =>
                  updateFilter(index, { operatorId: value as Operators })
                }
              />
              {!valueless && (
                <Input
                  aria-label={t('Filter value')}
                  placeholder={t('value')}
                  value={filter.value ?? ''}
                  css={css`
                    flex: 2;
                  `}
                  onChange={e => updateFilter(index, { value: e.target.value })}
                />
              )}
              <Button
                buttonStyle="link"
                buttonSize="small"
                onClick={() => removeFilter(index)}
                aria-label={t('Remove filter')}
              >
                <Icons.DeleteOutlined />
              </Button>
            </FilterRow>
          );
        })}
        <Button
          buttonStyle="link"
          buttonSize="small"
          onClick={addFilter}
          disabled={!columnOptions.length}
        >
          <Icons.PlusOutlined /> {t('Add filter')}
        </Button>
      </Section>

      <Section>
        <SectionLabel>{t('Row limit')}</SectionLabel>
        <Select
          ariaLabel={t('Row limit')}
          allowClear
          options={ROW_LIMIT_OPTIONS.map(n => ({
            label: String(n),
            value: n,
          }))}
          value={intent.rowLimit}
          placeholder={t('Default')}
          onChange={value =>
            apply({ ...intent, rowLimit: value as number | undefined })
          }
        />
      </Section>

      <Footer>
        <Button
          buttonStyle="primary"
          onClick={onQuery}
          loading={isLoading}
          data-test="guided-update-chart"
        >
          {t('Update chart')}
        </Button>
        <Button buttonStyle="link" onClick={onSwitchToAdvanced}>
          {t('Switch to advanced')}
        </Button>
      </Footer>
    </Container>
  );
}
