import { CONFIG } from './config.js';
import { loadTermById } from './data/api.js';
import { buildGraph } from './graph/geometry.js';

export async function initialiseScene(initialIdOverride) {
  const id = initialIdOverride || CONFIG.INITIAL_TERM_ID;
  const seed = await loadTermById(id);
  buildGraph(seed);
}