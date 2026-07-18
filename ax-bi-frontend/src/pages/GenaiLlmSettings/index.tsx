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
import { useCallback, useEffect, useMemo, useState } from 'react';
import { t } from '@ax-bi/core/translation';
import { getClientErrorObject } from '@ax-bi/ui-core';
import { Alert } from '@ax-bi/core/components';
import { css, styled, useTheme } from '@ax-bi/core/theme';
import {
  Button,
  Form,
  Input,
  InputNumber,
  Loading,
  Select,
  Space,
  Switch,
} from '@ax-bi/ui-core/components';
import SubMenu from 'src/features/home/SubMenu';
import { useToasts } from 'src/components/MessageToasts/withToasts';
import { isUserAdmin } from 'src/dashboard/util/permissionUtils';
import getBootstrapData from 'src/utils/getBootstrapData';
import {
  clearLlmProviderSettings,
  fetchLlmProviderSettings,
  saveLlmProviderSettings,
  testLlmProvider,
} from 'src/features/genai/api';
import {
  LlmProviderSettings,
  LlmProviderType,
  LlmProviderUpdatePayload,
} from 'src/features/genai/types';

const Page = styled.div`
  ${({ theme }) => css`
    max-width: ${theme.sizeUnit * 150}px;
    margin: 0 auto;
    padding: ${theme.sizeUnit * 4}px;
  `}
`;

const Card = styled.div`
  ${({ theme }) => css`
    background: ${theme.colorBgContainer};
    border-radius: ${theme.borderRadius}px;
    padding: ${theme.sizeUnit * 6}px;
    margin-top: ${theme.sizeUnit * 4}px;
  `}
`;

const Help = styled.p`
  ${({ theme }) => css`
    color: ${theme.colorTextSecondary};
    margin-bottom: ${theme.sizeUnit * 4}px;
  `}
`;

const PROVIDER_OPTIONS: { value: LlmProviderType; label: string }[] = [
  {
    value: 'openai_compatible',
    label: 'OpenAI-compatible (Ollama / LM Studio / vLLM)',
  },
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
];

type FormValues = {
  enabled: boolean;
  provider: LlmProviderType;
  base_url?: string;
  model: string;
  api_key?: string;
  timeout_seconds: number;
  verify_tls: boolean;
  allow_http: boolean;
  allow_private_network: boolean;
};

const defaultForm: FormValues = {
  enabled: false,
  provider: 'openai_compatible',
  base_url: '',
  model: '',
  api_key: '',
  timeout_seconds: 60,
  verify_tls: true,
  allow_http: false,
  allow_private_network: false,
};

function settingsToForm(settings: LlmProviderSettings): FormValues {
  return {
    enabled: settings.enabled,
    provider: (settings.provider as LlmProviderType) || 'openai_compatible',
    base_url: settings.base_url || '',
    model: settings.model || '',
    api_key: '',
    timeout_seconds: settings.timeout_seconds || 60,
    verify_tls: settings.verify_tls,
    allow_http: settings.allow_http,
    allow_private_network: settings.allow_private_network,
  };
}

function formToPayload(values: FormValues): LlmProviderUpdatePayload {
  const payload: LlmProviderUpdatePayload = {
    enabled: values.enabled,
    provider: values.provider,
    model: values.model.trim(),
    timeout_seconds: values.timeout_seconds,
    verify_tls: values.verify_tls,
    allow_http: values.allow_http,
    allow_private_network: values.allow_private_network,
  };
  if (values.base_url?.trim()) {
    payload.base_url = values.base_url.trim();
  } else {
    payload.base_url = null;
  }
  if (values.api_key?.trim()) {
    payload.api_key = values.api_key.trim();
  }
  return payload;
}

export default function GenaiLlmSettings() {
  const theme = useTheme();
  const { addDangerToast, addSuccessToast } = useToasts();
  const user = getBootstrapData()?.user;
  const admin = isUserAdmin(user);
  const [form] = Form.useForm<FormValues>();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [settings, setSettings] = useState<LlmProviderSettings | null>(null);
  const [provider, setProvider] = useState<LlmProviderType>(
    defaultForm.provider,
  );
  const [enabled, setEnabled] = useState(defaultForm.enabled);

  const needsBaseUrl =
    provider === 'openai_compatible' || provider === 'openai';

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchLlmProviderSettings();
      setSettings(result);
      const formValues = settingsToForm(result);
      form.setFieldsValue(formValues);
      setProvider(formValues.provider);
      setEnabled(formValues.enabled);
    } catch (error) {
      const clientError = await getClientErrorObject(error);
      addDangerToast(
        clientError.error ||
          t('Failed to load LLM provider settings. Admin access is required.'),
      );
    } finally {
      setLoading(false);
    }
  }, [addDangerToast, form]);

  useEffect(() => {
    if (admin) {
      load();
    } else {
      setLoading(false);
    }
  }, [admin, load]);

  const submenu = useMemo(
    () => ({
      name: t('GenAI LLM Provider'),
    }),
    [],
  );

  const onSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const { result, message } = await saveLlmProviderSettings(
        formToPayload(values),
      );
      setSettings(result);
      const formValues = settingsToForm(result);
      form.setFieldsValue(formValues);
      setProvider(formValues.provider);
      setEnabled(formValues.enabled);
      addSuccessToast(message || t('LLM provider settings saved'));
    } catch (error) {
      if (error && typeof error === 'object' && 'errorFields' in error) {
        return;
      }
      const clientError = await getClientErrorObject(error);
      addDangerToast(
        clientError.error || t('Failed to save LLM provider settings'),
      );
    } finally {
      setSaving(false);
    }
  };

  const onTest = async () => {
    try {
      const values = await form.validateFields();
      setTesting(true);
      const result = await testLlmProvider(formToPayload(values));
      if (result.ok) {
        addSuccessToast(
          t('Connection test succeeded (%(provider)s / %(model)s)', {
            provider: result.provider || values.provider,
            model: result.model || values.model,
          }),
        );
      } else {
        addDangerToast(t('Connection test did not return ok'));
      }
    } catch (error) {
      if (error && typeof error === 'object' && 'errorFields' in error) {
        return;
      }
      const clientError = await getClientErrorObject(error);
      addDangerToast(clientError.error || t('LLM connection test failed'));
    } finally {
      setTesting(false);
    }
  };

  const onClear = async () => {
    setSaving(true);
    try {
      const result = await clearLlmProviderSettings();
      setSettings(result);
      const formValues = settingsToForm(result);
      form.setFieldsValue(formValues);
      setProvider(formValues.provider);
      setEnabled(formValues.enabled);
      addSuccessToast(t('Runtime LLM provider configuration cleared'));
    } catch (error) {
      const clientError = await getClientErrorObject(error);
      addDangerToast(
        clientError.error || t('Failed to clear LLM provider settings'),
      );
    } finally {
      setSaving(false);
    }
  };

  if (!admin) {
    return (
      <>
        <SubMenu {...submenu} />
        <Page>
          <Alert
            type="warning"
            showIcon
            message={t('Administrators only')}
            description={t(
              'Only Admin users can configure the server-side LLM inference URL and auth token. Core AX BI works without an LLM.',
            )}
          />
        </Page>
      </>
    );
  }

  return (
    <>
      <SubMenu {...submenu} />
      <Page>
        <Help>
          {t(
            'Optional server-side LLM used for semantic assistance and GenAI authoring. Only Administrators may set the inference URL and token. Leave disabled to use original AX BI capabilities only. AX Studio local models are separate and must not be pasted here by end users.',
          )}
        </Help>
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: theme.sizeUnit * 4 }}
          message={t('Production tip')}
          description={t(
            'For multi-worker deployments, prefer GENAI_LLM_* environment variables / secret managers. Saving here updates this process runtime config.',
          )}
        />
        {loading ? (
          <Loading />
        ) : (
          <Card>
            {settings?.api_key_set && (
              <Alert
                type="success"
                showIcon
                style={{ marginBottom: theme.sizeUnit * 4 }}
                message={t(
                  'An API key is already configured (value is hidden).',
                )}
                description={t(
                  'Leave the API key field blank to keep the existing secret.',
                )}
              />
            )}
            <Form
              form={form}
              layout="vertical"
              initialValues={defaultForm}
              requiredMark
            >
              <Form.Item
                name="enabled"
                label={t('Enable server LLM')}
                valuePropName="checked"
              >
                <Switch onChange={checked => setEnabled(checked)} />
              </Form.Item>
              <Form.Item
                name="provider"
                label={t('Provider')}
                rules={
                  enabled
                    ? [{ required: true, message: t('Provider is required') }]
                    : undefined
                }
              >
                <Select
                  options={PROVIDER_OPTIONS}
                  aria-label={t('Provider')}
                  onChange={value => setProvider(value as LlmProviderType)}
                />
              </Form.Item>
              {needsBaseUrl && (
                <Form.Item
                  name="base_url"
                  label={t('Base URL')}
                  extra={t(
                    'Example: http://ollama-host:11434/v1 or https://api.openai.com/v1',
                  )}
                  rules={
                    enabled && provider === 'openai_compatible'
                      ? [
                          {
                            required: true,
                            message: t(
                              'Base URL is required for OpenAI-compatible providers',
                            ),
                          },
                        ]
                      : undefined
                  }
                >
                  <Input
                    placeholder="http://localhost:11434/v1"
                    autoComplete="off"
                  />
                </Form.Item>
              )}
              <Form.Item
                name="model"
                label={t('Model')}
                rules={
                  enabled
                    ? [{ required: true, message: t('Model is required') }]
                    : undefined
                }
              >
                <Input placeholder="llama3.1" autoComplete="off" />
              </Form.Item>
              <Form.Item
                name="api_key"
                label={t('API key / auth token')}
                extra={t(
                  'Write-only. Optional for local Ollama; required for most cloud APIs.',
                )}
              >
                <Input.Password
                  placeholder={
                    settings?.api_key_set
                      ? t('(unchanged)')
                      : t('Paste token (Admin only)')
                  }
                  autoComplete="new-password"
                />
              </Form.Item>
              <Form.Item name="timeout_seconds" label={t('Timeout (seconds)')}>
                <InputNumber min={1} max={300} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item
                name="verify_tls"
                label={t('Verify TLS')}
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
              <Form.Item
                name="allow_http"
                label={t('Allow HTTP (non-TLS)')}
                valuePropName="checked"
                extra={t('Needed for many local Ollama / LM Studio gateways.')}
              >
                <Switch />
              </Form.Item>
              <Form.Item
                name="allow_private_network"
                label={t('Allow private / loopback network')}
                valuePropName="checked"
                extra={t(
                  'Required for on-prem private IPs. Cloud metadata addresses remain blocked.',
                )}
              >
                <Switch />
              </Form.Item>
              <Space wrap>
                <Button
                  buttonStyle="primary"
                  onClick={onSave}
                  loading={saving}
                  disabled={loading}
                >
                  {t('Save')}
                </Button>
                <Button
                  onClick={onTest}
                  loading={testing}
                  disabled={loading || !enabled}
                >
                  {t('Test connection')}
                </Button>
                <Button
                  buttonStyle="danger"
                  onClick={onClear}
                  disabled={loading || saving}
                >
                  {t('Clear runtime config')}
                </Button>
              </Space>
            </Form>
          </Card>
        )}
      </Page>
    </>
  );
}
