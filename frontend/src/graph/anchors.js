import * as THREE from 'three';
import { scene } from '../scene/scene.js';

export function makeAnchorAt(obj3d) {
  const anchor = new THREE.Object3D();
  anchor.position.copy(obj3d.position);
  scene.add(anchor);
  return anchor;
}