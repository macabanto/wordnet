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
  rotateTarget: scene,
  onClickSprite: async (clicked) => {
    const id = clicked?.userData?.id;
    if (!id) {
      console.warn('Clicked sprite lacks userData.id:', clicked?.userData);
      return;
    }
    try {
      TransitionManager.cancelAll();
      await transitionToNode(clicked, CONFIG.TRANSITION_MODE || 'serial');
    } catch (e) {
      console.error('transition error:', e);
    }
  }
});

// HUD
const hud = createPoseHUD({
  scene,
  camera,
  controls,
  getRotationVelocity: () => controls.getAngularVelocity()
});

function animate() {
  requestAnimationFrame(animate);
  controls.tick();        // drag + inertia
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