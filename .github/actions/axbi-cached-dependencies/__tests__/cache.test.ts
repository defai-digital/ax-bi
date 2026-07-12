import path from 'path';
import { restoreCache, saveCache } from '@actions/cache';
import * as cache from '../src/cache';
import defaultCaches from '../src/cache/caches';
import { setInputs, maybeArrayToString } from '../src/utils/inputs';
import { InputName } from '../src/constants';
import caches, { npmExpectedHash } from './fixtures/caches';

jest.mock('@actions/cache', () => ({
  restoreCache: jest.fn(),
  saveCache: jest.fn(),
}));

const restoreCacheMock = restoreCache as jest.MockedFunction<
  typeof restoreCache
>;
const saveCacheMock = saveCache as jest.MockedFunction<typeof saveCache>;

describe('cache runner', () => {
  afterEach(() => {
    process.exitCode = 0;
  });

  it('should use default cache config', async () => {
    await cache.loadCustomCacheConfigs();
    // but `npm` actually come from `src/cache/caches.ts`
    const inputs = await cache.getCacheInputs('npm');
    expect(inputs?.[InputName.Path]).toStrictEqual(
      maybeArrayToString(defaultCaches.npm.path),
    );
    expect(inputs?.[InputName.RestoreKeys]).toStrictEqual('npm-');
  });

  it('should override cache config', async () => {
    setInputs({
      [InputName.Caches]: path.resolve(__dirname, 'fixtures/caches'),
    });
    await cache.loadCustomCacheConfigs();

    const inputs = await cache.getCacheInputs('npm');
    expect(inputs?.[InputName.Path]).toStrictEqual(
      maybeArrayToString(caches.npm.path),
    );
    expect(inputs?.[InputName.Key]).toStrictEqual(`npm-${npmExpectedHash}`);
    expect(inputs?.[InputName.RestoreKeys]).toStrictEqual(
      maybeArrayToString(caches.npm.restoreKeys),
    );
  });

  it('should apply inputs and restore cache', async () => {
    setInputs({
      [InputName.Caches]: path.resolve(__dirname, 'fixtures/caches'),
    });

    const inputs = await cache.getCacheInputs('npm');
    const result = await cache.run('restore', 'npm');

    expect(result).toBeUndefined();
    expect(restoreCacheMock).toHaveBeenCalledWith(
      inputs?.[InputName.Path]?.split('\n'),
      inputs?.[InputName.Key],
      inputs?.[InputName.RestoreKeys]?.split('\n'),
    );
  });

  it('should run saveCache', async () => {
    setInputs({
      [InputName.Parallel]: 'true',
    });
    const inputs = await cache.getCacheInputs('npm');
    await cache.run('save', 'npm');
    expect(saveCacheMock).toHaveBeenCalledWith(
      inputs?.[InputName.Path]?.split('\n'),
      inputs?.[InputName.Key],
    );
  });

  it('should exit on invalid args', async () => {
    // other calls do generate errors
    const processExitMock = jest
      .spyOn(process, 'exit')
      // @ts-ignore
      .mockImplementation(() => {});

    // incomplete arguments
    await cache.run();
    await cache.run('save');

    // bad arguments
    await cache.run('save', 'unknown-cache');
    await cache.run('unknown-action', 'unknown-cache');

    setInputs({
      [InputName.Caches]: 'non-existent',
    });
    await cache.run('save', 'npm');

    expect(processExitMock).toHaveBeenCalledTimes(5);
    processExitMock.mockRestore();
  });
});
