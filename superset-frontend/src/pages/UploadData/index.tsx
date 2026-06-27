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

const { Dragger } = Upload;

const ACCEPTED_EXTENSIONS = '.csv,.tsv,.txt,.xls,.xlsx,.parquet';

const PageWrapper = styled.div`
  max-width: 680px;
  margin: 60px auto;
  padding: 0 24px;
  text-align: center;
`;

const Title = styled.h1`
  font-size: 28px;
  font-weight: ${({ theme }) => theme.fontWeightBold};
  margin-bottom: 8px;
`;

const Subtitle = styled.p`
  font-size: 16px;
  color: ${({ theme }) => theme.colorTextSecondary};
  margin-bottom: 40px;
`;

const DropZoneWrapper = styled.div`
  margin-bottom: 32px;

  .ant-upload-drag {
    border: 2px dashed ${({ theme }) => theme.colorBorder};
    border-radius: ${({ theme }) => theme.borderRadius}px;
    background: ${({ theme }) => theme.colorBgContainer};
    transition: border-color 0.3s;

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
  color: ${({ theme }) => theme.colorTextTertiary};
  margin-bottom: 16px;
`;

const HelpText = styled.p`
  font-size: 14px;
  color: ${({ theme }) => theme.colorTextSecondary};
  margin-top: 8px;
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

      processingRef.current = false;
      setBatchComplete(true);

      // Redirect to the first successfully uploaded dataset
      const firstSuccess = results.find(r => r.status === 'success');
      if (firstSuccess?.datasetId) {
        setTimeout(() => {
          history.push(
            `/explore/?dataset_type=table&dataset_id=${firstSuccess.datasetId}`,
          );
        }, 1500);
      }
    },
    [history, uploadSingleFile, updateFile],
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
    <PageWrapper>
      <Title>{t('Upload Data')}</Title>
      <Subtitle>
        {t('Drop one or more files to start exploring your data')}
      </Subtitle>

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
          <p style={{ fontSize: 16, fontWeight: 500 }}>
            {t('Click or drag files to upload')}
          </p>
          <HelpText>
            {t(
              'Supported formats: CSV, TSV, XLS, XLSX, Parquet. Multiple files supported.',
            )}
          </HelpText>
        </Dragger>
      </DropZoneWrapper>

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
    </PageWrapper>
  );
};

export default withToasts(UploadData);
