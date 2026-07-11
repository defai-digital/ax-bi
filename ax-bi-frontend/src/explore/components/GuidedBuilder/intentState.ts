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
import { JsonObject } from '@superset-ui/core';
import { GuidedIntent } from './types';
import { intentFromFormData } from './intentFromFormData';
import {
  DEFAULT_GUIDED_VIZ_TYPE,
  isGuidedVizType,
} from './vizDescriptors';

/**
 * Build the initial guided intent from Explore form_data. When form_data has no
 * viz_type or a type the guided builder cannot represent, fall back to the
 * default guided viz so the Select and measure fields stay coherent.
 */
export function initialGuidedIntent(formData?: JsonObject): GuidedIntent {
  const fromForm = intentFromFormData(formData);
  if (isGuidedVizType(fromForm.vizType)) {
    return fromForm;
  }
  return { ...fromForm, vizType: DEFAULT_GUIDED_VIZ_TYPE };
}

/**
 * Sync local intent when Redux form_data.viz_type changes externally (e.g.
 * chart load completing after mount). Returns `prev` unchanged when the type
 * is unsupported or already matches, so in-progress measure edits are not
 * clobbered by unrelated form_data churn.
 */
export function nextGuidedIntentOnFormDataChange(
  prev: GuidedIntent,
  formData?: JsonObject,
): GuidedIntent {
  const nextType = formData?.viz_type as string | undefined;
  if (!isGuidedVizType(nextType) || prev.vizType === nextType) {
    return prev;
  }
  return intentFromFormData(formData);
}
