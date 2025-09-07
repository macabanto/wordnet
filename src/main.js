// main.js
import * as THREE from 'three';
import { CONFIG } from './config.js';
import { scene, camera, renderer, raycaster, mouse, attachResize } from './scene/scene.js';
import { installControls } from './scene/control.js';
import { nodeObjects } from './graph/state.js';
import { initialiseScene } from './setup.js';
import { transitionToNode, TransitionManager } from './flow/transition.js';
import { createPoseHUD } from './debug/poseHUD.js';

attachResize();

// World axes (helper)
const axesHelper = new THREE.AxesHelper(150);
scene.add(axesHelper);

// install controls (delta-per-frame version)
const controls = installControls({
  camera,
  raycaster,
  mouse,
  nodeObjects,
  onClickSprite: async (clicked) => { /* ... */ },
  rotateTarget: scene                 // ⇦ NEW
});

// HUD (can still show quaternion, velocities, etc.)
const hud = createPoseHUD({
  scene,
  camera,
  controls,
  getRotationVelocity: () => controls.getAngularVelocity()
});

function animate() {
  requestAnimationFrame(animate);
  controls.tick();    // now handles both drag and inertia smoothly
  hud.update();
  renderer.render(scene, camera);
}

(async function start() {
  try {
    await initialiseScene();
  } catch (e) {
    console.error('initial load failed:', e);
  }
  animate();
})();