import { nodeGroup } from '../scene/scene.js';

export const byId = new Map();
export const nodeObjects = []; // clickable ring
let centeredNode = null;

export const nodeById = (id) => byId.get(id);
export const getCentered = () => centeredNode;
export const setCentered = (obj) => { centeredNode = obj; };

export function registerNode(obj) {
  const id = obj?.userData?.id;
  if (!id) return;
  byId.set(id, obj);
  if (obj.userData?.isSynonym) {
    if (!nodeObjects.includes(obj)) nodeObjects.push(obj);
  }
}

export function removeNode(obj) {
  const id = obj?.userData?.id;
  if (obj?.parent === nodeGroup) nodeGroup.remove(obj);
  if (obj?.material?.map) obj.material.map.dispose?.();
  obj?.material?.dispose?.();
  obj?.geometry?.dispose?.();
  if (id) byId.delete(id);
  const idx = nodeObjects.indexOf(obj);
  if (idx !== -1) nodeObjects.splice(idx, 1);
}

export function clearNodeGroup() {
  const children = [...nodeGroup.children];
  for (const sprite of children) removeNode(sprite);
}

export function currentSynIdsFromScene() {
  return nodeObjects
    .filter(o => o.userData?.isSynonym)
    .map(o => o.userData.id);
}