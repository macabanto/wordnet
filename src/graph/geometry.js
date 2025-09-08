import { nodeGroup } from '../scene/scene.js';
import { createTextSprite } from './sprites.js';
import { getId } from '../data/id.js';
import { registerNode, clearNodeGroup } from './state.js';

export function buildGraph(termDoc) {
  clearNodeGroup();

  // center
  const centerSprite = createTextSprite(termDoc.term);
  const centerId = getId(termDoc);
  centerSprite.position.set(0, 0, 0);
  Object.assign(centerSprite.userData, {
    id: centerId, 
    term: termDoc.term, 
    isCenter: true
  });
  nodeGroup.add(centerSprite);
  registerNode(centerSprite);
  nodeGroup.userData.center = centerSprite;
  // --- synonyms ring ---
  const list = Array.isArray(termDoc.linked_synonyms) ? termDoc.linked_synonyms : [];
  for (const syn of list) {
    const sid = getId(syn);
    if (!sid) continue;
    const sprite = createTextSprite(syn.term);
    sprite.position.set(syn.x ?? 0, syn.y ?? 0, syn.z ?? 0);
    Object.assign(sprite.userData, {
      id: sid,
      term: syn.term,
      isSynonym: true
    });
    nodeGroup.add(sprite);
    registerNode(sprite);
  }
  return centerSprite;
}