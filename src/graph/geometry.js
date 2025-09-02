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
  centerSprite.userData = { id: centerId, term: termDoc.term, isCenter: true };
  nodeGroup.add(centerSprite);
  registerNode(centerSprite);
  nodeGroup.userData.center = centerSprite;

  // synonyms
  const list = Array.isArray(termDoc.linked_synonyms) ? termDoc.linked_synonyms : [];
  list.forEach(syn => {
    const sprite = createTextSprite(syn.term);
    const sid = getId(syn);
    sprite.position.set(syn.x, syn.y, syn.z);
    sprite.userData = { id: sid, term: syn.term, isSynonym: true };
    nodeGroup.add(sprite);
    registerNode(sprite);
  });

  return centerSprite;
}