/**
 * Manage inputs and env variables.
 */
import * as core from '@actions/core';
import { Inputs, InputName, DefaultInputs } from '../constants';

export function getInput(name: keyof Inputs): string {
  const value = core.getInput(name);
  if (name === InputName.Parallel) {
    return value.toUpperCase() === 'TRUE' ? value : '';
  }
  return value || DefaultInputs[name] || '';
}

/**
 * Update env variables associated with some inputs.
 * See: https://github.com/actions/toolkit/blob/5b940ebda7e7b86545fe9741903c930bc1191eb0/packages/core/src/core.ts#L69-L77 .
 *
 * @param {Inputs} inputs - The new inputs to apply to the env variables.
 */
export function setInputs(inputs: Inputs): void {
  for (const [name, value] of Object.entries(inputs)) {
    const envName = `INPUT_${name.replace(/ /g, '_').toUpperCase()}`;
    process.env[envName] = value;
  }
}

export function maybeArrayToString(input: string[] | string) {
  return Array.isArray(input) ? input.join('\n') : input;
}
