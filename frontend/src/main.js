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

// === Toggle UI for HUD & Axes (with persistence) ===
(function createToggleUI({ hud, axesHelper }) {
  // container
  const ui = document.createElement('div');
  Object.assign(ui.style, {
    position: 'fixed', top: '10px', left: '10px',
    display: 'flex', flexDirection: 'column', gap: '6px',
    zIndex: 10000, fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, Arial'
  });

  // button factory`
  const mkBtn = (id, label) => {
    const b = document.createElement('button');
    b.id = id; b.textContent = label;
    Object.assign(b.style, {
      padding: '6px 10px', borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.2)',
      background: 'rgba(0,0,0,0.6)', color: '#fff',
      cursor: 'pointer', backdropFilter: 'blur(6px)'
    });
    b.onmouseenter = () => (b.style.background = 'rgba(0,0,0,0.75)');
    b.onmouseleave = () => (b.style.background = 'rgba(0,0,0,0.6)');
    return b;
  };

  const btnHud = mkBtn('toggleHud', 'Hide HUD');
  const btnAx  = mkBtn('toggleAxes', 'Hide Axes');
  ui.append(btnHud, btnAx);
  document.body.appendChild(ui);

  // persistence helpers
  const LS = {
    get(k, fb) { const v = localStorage.getItem(k); return v === null ? fb : v === 'true'; },
    set(k, v) { localStorage.setItem(k, String(v)); }
  };

  // setters keep UI + storage in sync
  const setHudVisible = (v) => {
    hud.element.style.display = v ? 'block' : 'none';
    LS.set('hudVisible', v);
    updateButtons();
  };
  const setAxesVisible = (v) => {
    axesHelper.visible = v;
    LS.set('axesVisible', v);
    updateButtons();
  };

  // init from storage (defaults: true)
  setHudVisible(LS.get('hudVisible', true));
  setAxesVisible(LS.get('axesVisible', true));

  // handlers
  btnHud.addEventListener('click', () => {
    const isVisible = hud.element.style.display !== 'none';
    setHudVisible(!isVisible);
  });
  btnAx.addEventListener('click', () => setAxesVisible(!axesHelper.visible));

  function updateButtons() {
    const hudVisible = hud.element.style.display !== 'none';
    btnHud.textContent = hudVisible ? 'Hide HUD' : 'Show HUD';
    btnAx.textContent  = axesHelper.visible ? 'Hide Axes' : 'Show Axes';
  }

  // keep labels in sync if user presses your existing 'h' hotkey
  window.addEventListener('keydown', (e) => {
    if (e.key.toLowerCase() === 'h') {
      setTimeout(() => {
        const hudVisibleNow = hud.element.style.display !== 'none';
        LS.set('hudVisible', hudVisibleNow);
        updateButtons();
      }, 0);
    }
  });

  updateButtons();
})({ hud, axesHelper });

function animate() {
  requestAnimationFrame(animate);
  controls.tick();        // drag + inertia
  hud.update();
  renderer.render(scene, camera);
}

(async function start() {
  try {
    const savedCenter = localStorage.getItem('centerId');
    await initialiseScene(savedCenter || undefined);
  } catch (e) {
    console.error('initial load failed:', e);
  }
  animate();
})();