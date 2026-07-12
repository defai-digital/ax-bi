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
import { FC } from 'react';
import { t } from '@ax-bi/core/translation';
import { styled } from '@ax-bi/core/theme';
import { Select, Typography } from '@ax-bi/ui-core/components';
import { type TagType, TagsList } from 'src/components/TagsList';

export type UploadColumnMetadata = {
  name: string;
  source_dtype?: string;
  semantic_type?: string;
  suggested_type?: UploadTargetType;
  bi_role?: string;
  confidence?: number;
  null_count?: number;
  row_count_sampled?: number;
  n_unique_sampled?: number;
  sample_values?: (string | null)[];
  warnings?: string[];
};

export type UploadTargetType =
  | 'auto'
  | 'text'
  | 'integer'
  | 'decimal'
  | 'float'
  | 'boolean'
  | 'datetime'
  | 'date';

interface ColumnsPreviewProps {
  columns: string[];
  columnMetadata?: UploadColumnMetadata[];
  selectedTypes?: Record<string, UploadTargetType>;
  canOverrideTypes?: boolean;
  onTypeChange?: (column: string, type: UploadTargetType) => void;
  maxColumnsToShow?: number;
}

export const StyledDivContainer = styled.div`
  .field-review {
    border: 1px solid ${({ theme }) => theme.colorBorder};
    border-radius: ${({ theme }) => theme.borderRadius}px;
    max-height: 280px;
    overflow: auto;
  }

  table {
    border-collapse: collapse;
    min-width: 760px;
    width: 100%;
  }

  th,
  td {
    border-bottom: 1px solid ${({ theme }) => theme.colorBorderSecondary};
    padding: ${({ theme }) => theme.sizeUnit * 2}px;
    text-align: left;
    vertical-align: top;
    white-space: nowrap;
  }

  th {
    background: ${({ theme }) => theme.colorBgContainer};
    color: ${({ theme }) => theme.colorTextSecondary};
    font-weight: ${({ theme }) => theme.fontWeightStrong};
    position: sticky;
    top: 0;
    z-index: 1;
  }

  tr:last-child td {
    border-bottom: 0;
  }

  .column-name {
    font-family: ${({ theme }) => theme.fontFamilyCode};
    font-size: ${({ theme }) => theme.fontSizeSM}px;
  }

  .sample-values {
    color: ${({ theme }) => theme.colorTextSecondary};
    max-width: 220px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .warning {
    color: ${({ theme }) => theme.colorWarningText};
    max-width: 240px;
    white-space: normal;
  }
`;

const typeOptions = [
  { value: 'auto', label: t('Auto') },
  { value: 'text', label: t('Text') },
  { value: 'integer', label: t('Integer') },
  { value: 'decimal', label: t('Decimal') },
  { value: 'float', label: t('Float') },
  { value: 'boolean', label: t('Boolean') },
  { value: 'datetime', label: t('Datetime') },
  { value: 'date', label: t('Date') },
];

const ColumnsPreview: FC<ColumnsPreviewProps> = ({
  columns,
  columnMetadata = [],
  selectedTypes = {},
  canOverrideTypes = true,
  onTypeChange,
  maxColumnsToShow = 4,
}) => {
  const tags: TagType[] = columns.map(column => ({ name: column }));
  const hasRichMetadata = columnMetadata.length > 0;

  return (
    <StyledDivContainer>
      <Typography.Text type="secondary">{t('Field review')}:</Typography.Text>
      {columns.length === 0 ? (
        <p className="help-block">{t('Upload file to preview columns')}</p>
      ) : hasRichMetadata ? (
        <div className="field-review">
          <table>
            <thead>
              <tr>
                <th>{t('Column')}</th>
                <th>{t('Sample values')}</th>
                <th>{t('Detected')}</th>
                <th>{t('Import as')}</th>
                <th>{t('BI role')}</th>
                <th>{t('Warnings')}</th>
              </tr>
            </thead>
            <tbody>
              {columnMetadata.map(column => (
                <tr key={column.name}>
                  <td className="column-name">{column.name}</td>
                  <td className="sample-values">
                    {(column.sample_values || [])
                      .map(value => value ?? t('null'))
                      .join(', ')}
                  </td>
                  <td>
                    <div>{column.semantic_type || t('unknown')}</div>
                    <Typography.Text type="secondary">
                      {column.n_unique_sampled != null
                        ? t('%s unique', column.n_unique_sampled)
                        : column.source_dtype}
                    </Typography.Text>
                  </td>
                  <td>
                    <Select
                      ariaLabel={t('Import type for %s', column.name)}
                      disabled={!canOverrideTypes}
                      options={typeOptions}
                      value={
                        selectedTypes[column.name] ||
                        column.suggested_type ||
                        'auto'
                      }
                      onChange={(value: UploadTargetType) =>
                        onTypeChange?.(column.name, value)
                      }
                    />
                  </td>
                  <td>{column.bi_role || t('Dimension')}</td>
                  <td className="warning">
                    {(column.warnings || []).join(' ')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <TagsList tags={tags} maxTags={maxColumnsToShow} />
      )}
    </StyledDivContainer>
  );
};

export default ColumnsPreview;
