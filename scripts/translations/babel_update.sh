#!/bin/bash
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

set -e

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  echo "Usage: ./scripts/translations/babel_update.sh"
  echo
  echo "Extract and update AxBI translation catalogs."
  exit 0
fi

CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="${AXBI_TRANSLATIONS_ROOT_DIR:-$( cd "$( dirname "${BASH_SOURCE[0]}" )" && cd ../.. && pwd )}"
LICENSE_TMP=$(mktemp)
cat <<'EOF'> "$LICENSE_TMP"
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

EOF

cd "$ROOT_DIR"
pybabel extract \
  -F axbi/translations/babel.cfg \
  -o axbi/translations/messages.pot \
  --no-location \
  --sort-output \
  --copyright-holder=AxBI \
  --project=AxBI \
  -k _ -k __ -k t -k tn:1,2 -k tct .

# Normalize .pot file
msgcat --sort-output --no-wrap --no-location axbi/translations/messages.pot -o axbi/translations/messages.pot

cat "$LICENSE_TMP" axbi/translations/messages.pot > messages.pot.tmp \
  && mv messages.pot.tmp axbi/translations/messages.pot

# --no-fuzzy-matching: when a *new* source string is added, Babel's fuzzy
# matcher otherwise guesses a "close" existing translation and marks it
# `#, fuzzy` in every language catalog. Those guesses are (a) usually wrong
# (e.g. a new "valuename" string mapped onto an unrelated "table name"
# translation) and (b) counted by check_translation_regression.py as a
# regression, so every PR that merely adds a translatable string failed the
# babel-extract check. Disabling fuzzy matching means new strings land as
# cleanly untranslated (empty msgstr) instead — accurate, and no spurious
# regression. Renames likewise drop the stale translation rather than
# stranding a wrong guess; the string is re-translated by the community.
pybabel update \
  -i axbi/translations/messages.pot \
  -d axbi/translations \
  --ignore-obsolete \
  --no-fuzzy-matching

# Chop off last blankline from po/pot files, see https://github.com/python-babel/babel/issues/799
find axbi/translations -type f \( -name "*.po" -o -name "*.pot" \) -print0 |
while IFS= read -r -d '' file
do
  mv "$file" "$file.tmp"
  sed "$ d" "$file.tmp" > "$file"
  rm "$file.tmp"
done

cd "$CURRENT_DIR"
