<!--
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
-->

# Upload QA Fixtures

This folder contains small real files used by `qa/test_upload_file_formats.py`
to verify upload reader behavior across the supported file formats:

- CSV, TSV, and delimited TXT
- XLS and XLSX workbooks
- Parquet
- JSON, JSONL, and NDJSON
- XML
- SQL table export dumps
- SQLite database files

The samples intentionally include a leading-zero `customer_id` so QA can verify
that metadata suggests preserving identifier-like values as text.

The `customers.xls` fixture uses workbook content that pandas can sniff as an
Excel file while exercising AX BI's accepted `.xls` extension path. The local QA
environment does not include an `xlwt` writer for generating legacy BIFF `.xls`
files.
