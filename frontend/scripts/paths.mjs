import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';

// Evidence belongs to the repository, regardless of the caller's working directory.
export const repositoryRoot = fileURLToPath(new URL('../../', import.meta.url));
export const artifactPath = (...segments) => resolve(repositoryRoot, 'artifacts', ...segments);
