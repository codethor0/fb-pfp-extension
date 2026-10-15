// Builds a Firefox-ready copy of the extension in dist/firefox. The Chrome
// manifest stays untouched, so the Chrome Web Store package is unaffected.
// Dependency-free. Usage: node tools/build_firefox.mjs [outDir]
import {cpSync, mkdirSync, readFileSync, rmSync, writeFileSync} from 'node:fs';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

export const GECKO_ID = 'fb-pfp@codethor0.github.io';
// data_collection_permissions arrived in Firefox 140 on desktop and 142 on Android.
export const MIN_FIREFOX = '140.0';
export const MIN_FIREFOX_ANDROID = '142.0';

// Pure transform, exported so the tests can check it without touching disk.
export function firefoxManifest(chromeManifest) {
  const manifest = structuredClone(chromeManifest);
  delete manifest.minimum_chrome_version;
  // Firefox runs MV3 background code as an event page, not a service worker.
  manifest.background = {scripts: [chromeManifest.background.service_worker], type: 'module'};
  manifest.browser_specific_settings = {
    gecko: {
      id: GECKO_ID,
      strict_min_version: MIN_FIREFOX,
      // The extension collects nothing; this is Mozilla's required declaration.
      data_collection_permissions: {required: ['none']}
    },
    gecko_android: {strict_min_version: MIN_FIREFOX_ANDROID}
  };
  return manifest;
}

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

export function buildFirefox(out = join(root, 'dist', 'firefox')) {
  const manifest = JSON.parse(readFileSync(join(root, 'manifest.json'), 'utf8'));
  rmSync(out, {recursive: true, force: true});
  mkdirSync(out, {recursive: true});
  cpSync(join(root, 'src'), join(out, 'src'), {recursive: true});
  cpSync(join(root, 'icons'), join(out, 'icons'), {recursive: true});
  writeFileSync(join(out, 'manifest.json'), JSON.stringify(firefoxManifest(manifest), null, 2) + '\n');
  return out;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  console.log(`Firefox build written to ${buildFirefox(process.argv[2] ? resolve(process.argv[2]) : undefined)}`);
}
