// Copy licensed dependency assets locally, keeping runtime drawing off third-party CDNs.
import { cp, mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const destination = resolve(root, 'public/tldraw-assets');
await mkdir(destination, {recursive: true});
for (const directory of ['fonts','icons','translations','embed-icons']) {
  await cp(resolve(root, 'node_modules/@tldraw/assets', directory), resolve(destination, directory), {recursive: true});
}
console.log('Prepared self-hosted tldraw assets');
