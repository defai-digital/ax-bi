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
import { useCallback, useRef, useState } from 'react';
import { useHistory } from 'react-router-dom';
import { t } from '@apache-superset/core/translation';
import { styled } from '@apache-superset/core/theme';
import { SupersetClient, getClientErrorObject } from '@superset-ui/core';
import { Upload, Progress } from '@superset-ui/core/components';
import { Alert } from '@apache-superset/core/components';
import { Icons } from '@superset-ui/core/components/Icons';
import withToasts from 'src/components/MessageToasts/withToasts';
import { URL_PARAMS } from 'src/constants';
import {
  AXBIEyebrow,
  AXBIHero,
  AXBIHeroText,
  AXBIHeroTitle,
  AXBIPageNarrow,
  AXBISectionDescription,
} from 'src/components/AXBIWorkspace';

const { Dragger } = Upload;

const ACCEPTED_EXTENSIONS =
  '.csv,.tsv,.txt,.csv.gz,.tsv.gz,.txt.gz,.xls,.xlsx,.ods,.parquet,.zip,.orc,.feather,.arrow,.ipc,.json,.jsonl,.ndjson,.jsonl.gz,.ndjson.gz,.xml,.sql,.dump,.sqlite,.sqlite3,.db,.avro,.geojson,.gpkg,.shp.zip,.fwf,.dat,.asc,.dta,.sav,.sas7bdat,.xpt,.html,.htm,.croissant.json,.npy,.npz,.lance,.lance.zip,.faiss,.index,.hnsw,.ann,.tar,.tar.gz,.tgz,.mlflow.zip,.mlruns.zip,.safetensors,.onnx,.gguf,.yaml,.yml,.yolo.zip';

/** Build the Explore destination while retaining an originating dashboard. */
function buildExploreUrl(
  datasetId: number,
  dashboardId: string | null,
): string {
  const params = new URLSearchParams({
    [URL_PARAMS.datasourceType.name]: 'table',
    [URL_PARAMS.datasourceId.name]: String(datasetId),
  });
  if (dashboardId) {
    params.set(URL_PARAMS.dashboardId.name, dashboardId);
  }
  return `/explore/?${params.toString()}`;
}

const SupportNote = styled(AXBISectionDescription)`
  margin-top: ${({ theme }) => theme.sizeUnit * 3}px;
  max-width: 620px;
`;

const UploadHero = styled(AXBIHero)`
  ${({ theme }) => `
    grid-template-columns: minmax(0, 1fr) minmax(360px, 440px);
    gap: ${theme.sizeUnit * 8}px;
    align-items: center;
    padding: ${theme.sizeUnit * 8}px;

    @media (max-width: 900px) {
      grid-template-columns: 1fr;
      padding: ${theme.sizeUnit * 5}px;
    }
  `}
`;

const WorkflowGrid = styled.div`
  ${({ theme }) => `
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: ${theme.sizeUnit * 4}px;
    margin-top: ${theme.sizeUnit * 6}px;

    @media (max-width: 900px) {
      grid-template-columns: 1fr;
    }
  `}
`;

const StepCard = styled.div`
  ${({ theme }) => `
    padding: ${theme.sizeUnit * 4}px;
    border: 1px solid ${theme.colorBorderSecondary};
    border-radius: ${theme.borderRadius}px;
    background: ${theme.colorBgContainer};
  `}
`;

const StepBadge = styled.div`
  ${({ theme }) => `
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: ${theme.sizeUnit * 7}px;
    height: ${theme.sizeUnit * 7}px;
    border-radius: 50%;
    color: ${theme.colorPrimary};
    background: ${theme.colorPrimaryBg};
    font-weight: ${theme.fontWeightStrong};
    margin-bottom: ${theme.sizeUnit * 3}px;
  `}
`;

const StepTitle = styled.div`
  ${({ theme }) => `
    font-weight: ${theme.fontWeightStrong};
    color: ${theme.colorText};
    margin-bottom: ${theme.sizeUnit}px;
  `}
`;

const StepText = styled.div`
  ${({ theme }) => `
    color: ${theme.colorTextSecondary};
    line-height: 1.5;
  `}
`;

const DropZoneWrapper = styled.div`
  .ant-upload-drag {
    border: 2px dashed ${({ theme }) => theme.colorBorder};
    border-radius: ${({ theme }) => theme.borderRadius}px;
    background: ${({ theme }) => theme.colorBgContainer};
    transition: border-color 0.3s;
    min-height: 260px;
    display: flex;
    align-items: center;

    &:hover {
      border-color: ${({ theme }) => theme.colorPrimary};
    }
  }

  .ant-upload-drag-hover {
    border-color: ${({ theme }) => theme.colorPrimary};
    background: ${({ theme }) => theme.colorPrimaryBg};
  }
`;

const IconWrapper = styled.div`
  font-size: 48px;
  color: ${({ theme }) => theme.colorPrimary};
  margin-bottom: 16px;
  text-align: center;
`;

const HelpText = styled.p`
  font-size: 14px;
  color: ${({ theme }) => theme.colorTextSecondary};
  margin-top: 8px;
  max-width: 320px;
  margin-left: auto;
  margin-right: auto;
  line-height: 1.5;
`;

const StatusWrapper = styled.div`
  margin-top: 24px;
  text-align: left;
`;

const FileListWrapper = styled.ul`
  list-style: none;
  padding: 0;
  margin: 16px 0 0;
`;

const FileItem = styled.li<{ $fileStatus: FileStatusType }>`
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-radius: ${({ theme }) => theme.borderRadius}px;
  background: ${({ theme, $fileStatus }) =>
    $fileStatus === 'error'
      ? theme.colorErrorBg
      : $fileStatus === 'success'
        ? theme.colorSuccessBg
        : theme.colorBgContainer};
  border: 1px solid
    ${({ theme, $fileStatus }) =>
      $fileStatus === 'error'
        ? theme.colorErrorBorder
        : $fileStatus === 'success'
          ? theme.colorSuccessBorder
          : theme.colorBorder};
  margin-bottom: 8px;
`;

const FileName = styled.span`
  flex: 1;
  font-size: 14px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const FileStatusBadge = styled.span<{ $fileStatus: FileStatusType }>`
  font-size: 12px;
  color: ${({ theme, $fileStatus }) =>
    $fileStatus === 'error'
      ? theme.colorError
      : $fileStatus === 'success'
        ? theme.colorSuccess
        : $fileStatus === 'uploading'
          ? theme.colorPrimary
          : theme.colorTextSecondary};
`;

interface UploadDataProps {
  addDangerToast: (msg: string) => void;
  addSuccessToast: (msg: string) => void;
}

type FileStatusType = 'pending' | 'uploading' | 'success' | 'error';

interface FileEntry {
  id: string;
  file: File;
  status: FileStatusType;
  progress: number;
  datasetId?: number;
  error?: string;
}

const UploadData = ({ addDangerToast, addSuccessToast }: UploadDataProps) => {
  const history = useHistory();
  const dashboardId = new URLSearchParams(history.location.search).get(
    URL_PARAMS.dashboardId.name,
  );
  const [files, setFiles] = useState<FileEntry[]>([]);
  const [batchComplete, setBatchComplete] = useState(false);
  const processingRef = useRef(false);

  const uploadSingleFile = useCallback(
    async (file: File): Promise<{ datasetId?: number; error?: string }> => {
      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await SupersetClient.post({
          endpoint: '/api/v1/database/auto_upload/',
          body: formData,
          headers: { Accept: 'application/json' },
        });

        const data = response.json as {
          database_id: number;
          dataset_id: number;
          table_name: string;
        };

        addSuccessToast(
          t('File "%(name)s" uploaded successfully!', { name: file.name }),
        );

        return { datasetId: data.dataset_id };
      } catch (error) {
        const clientError = await getClientErrorObject(error);
        const msg =
          clientError.message ||
          clientError.error ||
          t('Upload failed. Please try again.');
        addDangerToast(msg);
        return { error: msg };
      }
    },
    [addSuccessToast, addDangerToast],
  );

  const updateFile = useCallback((id: string, updates: Partial<FileEntry>) => {
    setFiles(prev => prev.map(f => (f.id === id ? { ...f, ...updates } : f)));
  }, []);

  const processFiles = useCallback(
    async (fileList: File[]) => {
      if (processingRef.current) return;
      processingRef.current = true;

      // Initialize file entries
      const entries: FileEntry[] = fileList.map((file, idx) => ({
        id: `${Date.now()}-${idx}`,
        file,
        status: 'pending' as FileStatusType,
        progress: 0,
      }));
      setFiles(entries);
      setBatchComplete(false);

      try {
        const results: FileEntry[] = [];

        // Process sequentially
        for (const entry of entries) {
          updateFile(entry.id, { status: 'uploading', progress: 30 });

          const result = await uploadSingleFile(entry.file);
          const finalEntry: FileEntry = {
            ...entry,
            status: result.error ? 'error' : 'success',
            progress: 100,
            datasetId: result.datasetId,
            error: result.error,
          };
          results.push(finalEntry);
          updateFile(entry.id, {
            status: finalEntry.status,
            progress: 100,
            datasetId: finalEntry.datasetId,
            error: finalEntry.error,
          });
        }

        setBatchComplete(true);

        // Redirect to the first successfully uploaded dataset
        const firstDatasetId = results.find(
          r => r.status === 'success',
        )?.datasetId;
        if (firstDatasetId) {
          setTimeout(() => {
            history.push(buildExploreUrl(firstDatasetId, dashboardId));
          }, 1500);
        }
      } finally {
        processingRef.current = false;
      }
    },
    [dashboardId, history, uploadSingleFile, updateFile],
  );

  const handleBeforeUpload = useCallback(
    (file: File, fileList: File[]) => {
      // Only trigger batch processing on the first file call
      // (antd calls beforeUpload once per file in multi-select)
      const isFirst = fileList.indexOf(file) === 0;
      if (isFirst) {
        processFiles(fileList);
      }
      // Return false to prevent default upload behavior
      return false;
    },
    [processFiles],
  );

  const handleReset = () => {
    setFiles([]);
    setBatchComplete(false);
    processingRef.current = false;
  };

  const successCount = files.filter(f => f.status === 'success').length;
  const errorCount = files.filter(f => f.status === 'error').length;
  const isUploading = files.some(f => f.status === 'uploading');

  return (
    <AXBIPageNarrow>
      <UploadHero>
        <div>
          <AXBIEyebrow>{t('Start with a file')}</AXBIEyebrow>
          <AXBIHeroTitle>
            {t('Upload data and build charts faster')}
          </AXBIHeroTitle>
          <AXBIHeroText>
            {t(
              'Supported formats include CSV/TSV, compressed exports, Excel/ODS, Parquet/ORC/Arrow, JSON/XML, SQL text dumps, SQLite, fixed-width, HTML/statistical files, geospatial files, embeddings, and AI artifact metadata. Multiple files supported.',
            )}
          </AXBIHeroText>
          <SupportNote>
            {t(
              'PowerPoint files with tables should be sent from AX-Studio so MCP can extract structured data first.',
            )}
          </SupportNote>
        </div>

        <DropZoneWrapper>
          <Dragger
            accept={ACCEPTED_EXTENSIONS}
            beforeUpload={handleBeforeUpload}
            data-test="upload-data-dropzone"
            showUploadList={false}
            disabled={isUploading}
            multiple
          >
            <IconWrapper>
              <Icons.UploadOutlined iconSize="xxl" />
            </IconWrapper>
            <p style={{ fontSize: 18, fontWeight: 600, textAlign: 'center' }}>
              {t('Click or drag files here')}
            </p>
            <HelpText>
              {t(
                'Tabular files become datasets. Model, vector-index, archive, and AI manifest files are imported as metadata datasets.',
              )}
            </HelpText>
          </Dragger>
        </DropZoneWrapper>
      </UploadHero>

      <WorkflowGrid>
        <StepCard>
          <StepBadge>1</StepBadge>
          <StepTitle>{t('Upload your data')}</StepTitle>
          <StepText>
            {t(
              'Use local data, analytics, geospatial, or AI artifact files as datasets.',
            )}
          </StepText>
        </StepCard>
        <StepCard>
          <StepBadge>2</StepBadge>
          <StepTitle>{t('AX BI prepares the dataset')}</StepTitle>
          <StepText>
            {t('Columns and types are detected so the data is ready to chart.')}
          </StepText>
        </StepCard>
        <StepCard>
          <StepBadge>3</StepBadge>
          <StepTitle>{t('Create charts')}</StepTitle>
          <StepText>
            {t(
              'Open the chart builder, visualize the data, and save to dashboards.',
            )}
          </StepText>
        </StepCard>
      </WorkflowGrid>

      {files.length > 0 && (
        <StatusWrapper>
          <FileListWrapper>
            {files.map(entry => (
              <FileItem key={entry.id} $fileStatus={entry.status}>
                <FileName title={entry.file.name}>{entry.file.name}</FileName>
                {entry.status === 'uploading' && (
                  <Progress
                    percent={entry.progress}
                    size="small"
                    style={{ width: 80 }}
                  />
                )}
                {entry.status === 'success' && (
                  <FileStatusBadge $fileStatus="success">
                    {t('Uploaded')}
                  </FileStatusBadge>
                )}
                {entry.status === 'error' && (
                  <FileStatusBadge $fileStatus="error" title={entry.error}>
                    {t('Failed')}
                  </FileStatusBadge>
                )}
                {entry.status === 'pending' && (
                  <FileStatusBadge $fileStatus="pending">
                    {t('Waiting...')}
                  </FileStatusBadge>
                )}
              </FileItem>
            ))}
          </FileListWrapper>

          {batchComplete && (
            <div style={{ marginTop: 16 }}>
              {errorCount === 0 && (
                <Alert
                  type="success"
                  message={t(
                    'All %(count)d file(s) uploaded! Redirecting to chart builder...',
                    { count: successCount },
                  )}
                  showIcon
                />
              )}
              {errorCount > 0 && successCount > 0 && (
                <Alert
                  type="warning"
                  message={t(
                    '%(success)d succeeded, %(error)d failed. Redirecting to first successful dataset...',
                    { success: successCount, error: errorCount },
                  )}
                  showIcon
                />
              )}
              {errorCount > 0 && successCount === 0 && (
                <Alert
                  type="error"
                  message={t('All uploads failed.')}
                  showIcon
                  action={
                    <button
                      type="button"
                      onClick={handleReset}
                      style={{
                        background: 'none',
                        border: 'none',
                        textDecoration: 'underline',
                        cursor: 'pointer',
                        color: 'inherit',
                      }}
                    >
                      {t('Try again')}
                    </button>
                  }
                />
              )}
            </div>
          )}
        </StatusWrapper>
      )}
    </AXBIPageNarrow>
  );
};

export default withToasts(UploadData);
