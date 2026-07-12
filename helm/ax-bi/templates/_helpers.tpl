{{/*

 Licensed to the Apache Software Foundation (ASF) under one or more
 contributor license agreements.  See the NOTICE file distributed with
 this work for additional information regarding copyright ownership.
 The ASF licenses this file to You under the Apache License, Version 2.0
 (the "License"); you may not use this file except in compliance with
 the License.  You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.

*/}}

{{/* vim: set filetype=mustache: */}}
{{/*
Expand the name of the chart.
*/}}
{{- define "axbi.name" -}}
  {{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "axbi.fullname" -}}
  {{- if .Values.fullnameOverride -}}
    {{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
  {{- else -}}
    {{- $name := default .Chart.Name .Values.nameOverride -}}
    {{- if contains $name .Release.Name -}}
      {{- .Release.Name | trunc 63 | trimSuffix "-" -}}
    {{- else -}}
      {{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
    {{- end -}}
  {{- end -}}
{{- end -}}

{{/*
Create the name of the service account to use
*/}}
{{- define "axbi.serviceAccountName" -}}
  {{- if .Values.serviceAccount.create -}}
    {{- default (include "axbi.fullname" .) .Values.serviceAccountName -}}
  {{- else -}}
    {{- default "default" .Values.serviceAccountName -}}
  {{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "axbi.chart" -}}
  {{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}


{{- define "axbi-config" }}
import os
from flask_caching.backends.rediscache import RedisCache

def env(key, default=None):
    return os.getenv(key, default)

# Redis Base URL
{{- if .Values.axbiNode.connections.redis_password }}
REDIS_BASE_URL=f"{env('REDIS_PROTO')}://{env('REDIS_USER', '')}:{env('REDIS_PASSWORD')}@{env('REDIS_HOST')}:{env('REDIS_PORT')}"
{{- else }}
REDIS_BASE_URL=f"{env('REDIS_PROTO')}://{env('REDIS_HOST')}:{env('REDIS_PORT')}"
{{- end }}

# Redis URL Params
{{- if .Values.axbiNode.connections.redis_ssl.enabled }}
REDIS_URL_PARAMS = f"?ssl_cert_reqs={env('REDIS_SSL_CERT_REQS')}"
{{- else }}
REDIS_URL_PARAMS = ""
{{- end}}

# Build Redis URLs
CACHE_REDIS_URL = f"{REDIS_BASE_URL}/{env('REDIS_DB', 1)}{REDIS_URL_PARAMS}"
CELERY_REDIS_URL = f"{REDIS_BASE_URL}/{env('REDIS_CELERY_DB', 0)}{REDIS_URL_PARAMS}"

MAPBOX_API_KEY = env('MAPBOX_API_KEY', '')
CACHE_CONFIG = {
      'CACHE_TYPE': 'RedisCache',
      'CACHE_DEFAULT_TIMEOUT': 300,
      'CACHE_KEY_PREFIX': 'axbi_',
      'CACHE_REDIS_URL': CACHE_REDIS_URL,
}
DATA_CACHE_CONFIG = CACHE_CONFIG


if os.getenv("SQLALCHEMY_DATABASE_URI"):
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")
else:
    {{- if eq .Values.axbiNode.connections.db_type "postgresql" }}
    SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    {{- else if eq .Values.axbiNode.connections.db_type "mysql" }}
    SQLALCHEMY_DATABASE_URI = f"mysql+mysqldb://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    {{- else }}
    {{ fail (printf "Unsupported database type: %s. Please use 'postgresql' or 'mysql'." .Values.axbiNode.connections.db_type) }}
    {{- end }}

class CeleryConfig:
  imports  = ("axbi.sql_lab", )
  broker_url = CELERY_REDIS_URL
  result_backend = CELERY_REDIS_URL

CELERY_CONFIG = CeleryConfig
RESULTS_BACKEND = RedisCache(
      host=env('REDIS_HOST'),
      {{- if .Values.axbiNode.connections.redis_password }}
      password=env('REDIS_PASSWORD'),
      {{- end }}
      port=env('REDIS_PORT'),
      key_prefix='axbi_results',
      {{- if .Values.axbiNode.connections.redis_ssl.enabled }}
      ssl=True,
      ssl_cert_reqs=env('REDIS_SSL_CERT_REQS'),
      {{- end }}
)

{{ if .Values.configOverrides }}
# Overrides
{{- range $key, $value := .Values.configOverrides }}
# {{ $key }}
{{ tpl $value $ }}
{{- end }}
{{- end }}

{{ if .Values.configOverridesFiles }}
# Overrides from files
{{- $files := .Files }}
{{- range $key, $value := .Values.configOverridesFiles }}
# {{ $key }}
{{ $files.Get $value }}
{{- end }}
{{- end }}

{{- end }}

{{- define "axbiCeleryBeat.selectorLabels" -}}
app: {{ include "axbi.name" . }}-celerybeat
release: {{ .Release.Name }}
{{- end }}

{{- define "axbiCeleryFlower.selectorLabels" -}}
app: {{ include "axbi.name" . }}-flower
release: {{ .Release.Name }}
{{- end }}

{{- define "axbiNode.selectorLabels" -}}
app: {{ include "axbi.name" . }}
release: {{ .Release.Name }}
{{- end }}

{{- define "axbiWebsockets.selectorLabels" -}}
app: {{ include "axbi.name" . }}-ws
release: {{ .Release.Name }}
{{- end }}

{{- define "axbiWorker.selectorLabels" -}}
app: {{ include "axbi.name" . }}-worker
release: {{ .Release.Name }}
{{- end }}

{{- define "axbiMcp.selectorLabels" -}}
app: {{ include "axbi.name" . }}-mcp
release: {{ .Release.Name }}
{{- end }}

{{- define "axbiServices.selectorLabels" -}}
app: {{ include "axbi.name" . }}-services
release: {{ .Release.Name }}
{{- end }}
