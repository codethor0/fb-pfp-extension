// Dependency-free release checks. Never scan or package runtime user pictures.
import {readdirSync, readFileSync, statSync} from 'node:fs';
import {join, relative} from 'node:path';
import {fileURLToPath} from 'node:url';
import {dirname, resolve} from 'node:path';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const manifest = JSON.parse(readFileSync(join(root, 'manifest.json'), 'utf8'));
const expected = ['storage', 'alarms'];
const errors = [];
const requireCheck = (ok, reason) => { if (!ok) errors.push(reason); };
requireCheck(manifest.manifest_version === 3, 'Manifest V3 required');
requireCheck(manifest.version === '0.2.3', 'Unexpected manifest version');
requireCheck(JSON.stringify(manifest.permissions) === JSON.stringify(expected), 'Permission set changed');
requireCheck(JSON.stringify(manifest.host_permissions) === JSON.stringify(['https://www.facebook.com/*']), 'Host permissions broadened');
requireCheck(manifest.background?.type === 'module', 'Background must use a module');
requireCheck(!('externally_connectable' in manifest), 'External messaging must remain disabled');
requireCheck(!('web_accessible_resources' in manifest), 'No web accessible resources permitted');
requireCheck(manifest.content_scripts.length === 1 &&
  JSON.stringify(manifest.content_scripts[0].matches) === JSON.stringify(['https://www.facebook.com/*']),
  'Content script is not restricted to Facebook');
const referenced = [manifest.background.service_worker, manifest.action.default_popup,
  manifest.content_scripts[0].js[0], ...Object.values(manifest.action.default_icon), ...Object.values(manifest.icons)];
for (const entry of referenced) {
  requireCheck(statSync(join(root, entry), {throwIfNoEntry:false})?.isFile(), 'Manifest missing ' + entry);
}

function walk(directory) {
  return readdirSync(directory,{withFileTypes:true}).flatMap(item => {
    if (item.name.startsWith('.') && !['.github','.gitignore'].includes(item.name)) return [];
    if (['dist','node_modules','.git','__pycache__'].includes(item.name)) return [];
    const full = join(directory,item.name);
    return item.isDirectory() ? walk(full) : [full];
  });
}
const paths = walk(root);
const allowedBinary = /^(?:icons\/icon(?:16|48|128)\.png|docs\/demo\.gif|docs\/screenshot-[a-z]+\.png)$/;
const imagePattern = /\.(?:png|jpe?g|webp|heic|gif|mp4|mov|zip|pdf|pem|key)$/i;
const textPattern = /\.(?:js|mjs|json|md|css|html|yml|yaml|txt|py)$|^LICENSE$|^Makefile$|^\.gitignore$/i;
for (const path of paths) {
  const file = relative(root,path).replaceAll('\\','/');
  if (imagePattern.test(file) && !allowedBinary.test(file)) errors.push('Unexpected media or secret material: ' + file);
  if (!textPattern.test(file)) continue;
  const data = readFileSync(path,'utf8');
  if (/\u2013|\u2014/.test(data)) errors.push('Non-ASCII dash found: '+file);
  const residue = [ ['as an',' ai language',' model'], ['system',' prompt'],
    ['assistant reasoning',' trace'], ['internal tool',' output'] ].map(parts => parts.join(''));
  if (residue.some(marker => data.toLowerCase().includes(marker)))
    errors.push('Prompt residue marker found: '+file);
  if (/\/Users\/(?!you\/)[\w.-]+\/|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|github_pat_[A-Za-z0-9_]{20,}/i.test(data))
    errors.push('Personal path or private key marker: '+file);
}
const serviceWorker = readFileSync(join(root,'src/background.mjs'),'utf8');
const content = readFileSync(join(root,'src/content.js'),'utf8');
requireCheck(!/\b(?:eval|Function)\s*\(/.test(serviceWorker+content), 'Dynamic execution found');
requireCheck(/message\.publish !== true/.test(content), 'Review must not click Save');
requireCheck(/await saveIfRequested\(/.test(content), 'Explicit publish action missing');
requireCheck(/if \(publish\)/.test(serviceWorker), 'Publication gating missing');
requireCheck(/dialog\.querySelectorAll\('input\[type="file"\]'\)/.test(content), 'File input must remain dialog scoped');
// A page-wide query is allowed only to count inputs for the failure message, never to pick one.
requireCheck(!/document\.querySelector(?:All)?\('input\[type="file"\]'\)(?!\.length)/.test(content), 'Page-wide file input lookup found');
// An input outside the dialog is used only when the dialog's own "Upload photo" button made Facebook click it, and only if it takes images alone.
requireCheck(/takesOnlyImages\(progress\.requested\)/.test(content) && /removeEventListener\('click', onClick, true\)/.test(content), 'Captured upload input must be image-only and released');
requireCheck(/Check the preview/.test(content), 'Content script review notice absent');
if (errors.length) {
  console.error(`Audit blocked: ${errors.length} issue(s).\n`+errors.join('\n'));
  process.exit(1);
}
console.log(`Static audit passed: ${paths.length} repository files; minimum permissions; no personal images; guarded upload input.`);
