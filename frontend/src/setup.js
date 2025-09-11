import { CONFIG } from './config.js';
import { loadTermById } from './data/api.js';
import { buildGraph } from './graph/geometry.js';

export async function initialiseScene() {
  const seed = await loadTermById(CONFIG.INITIAL_TERM_ID);
  buildGraph(seed);
}