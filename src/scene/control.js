// scene/control.js
import * as THREE from 'three';
import { CONFIG } from '../config.js';

export function installControls({
  camera,
  raycaster,
  mouse,
  nodeObjects,
  onClickSprite,
  rotateTarget   // usually your scene
}) {
  let isDragging = false;
  let clickCandidate = false;
  let lastSeen = { x: 0, y: 0 };
  let prev = { x: 0, y: 0 };

  // inertia
  let angularVelocity = new THREE.Vector3();

  // hover
  let hovered = null;

  const DRAG_CANCEL_PX = CONFIG.CLICK_THRESHOLD_PX ?? 5;
  const DRAG_SENS      = CONFIG.ROT_SPEED ?? 0.005;
  const INERTIA_DECAY  = CONFIG.INERTIA_DECAY ?? 0.92;

  function onMouseMove(e) {
    // always update mouse coords for raycaster
    mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
    lastSeen = { x: e.clientX, y: e.clientY };

    // --- HOVER LOGIC ---
    raycaster.setFromCamera(mouse, camera);
    const hit = raycaster.intersectObjects(nodeObjects, false)[0];

    if (hit?.object !== hovered) {
      if (hovered) {
        hovered.material.color.set(CONFIG.SPRITE_COLOR ?? 'white'); // reset old
      }
      if (hit?.object) {
        hit.object.material.color.set('teal'); // highlight new
      }
      hovered = hit?.object ?? null;
    }
  }

  function onMouseDown(e) {
    isDragging = true;
    clickCandidate = true;
    prev = lastSeen = { x: e.clientX, y: e.clientY };
    angularVelocity.set(0, 0, 0); // stop inertia
  }

  function onMouseUp(e) {
    isDragging = false;

    // refresh coords in case no move occurred
    mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
    lastSeen = { x: e.clientX, y: e.clientY };

    const movedFar =
      Math.abs(prev.x - lastSeen.x) > DRAG_CANCEL_PX ||
      Math.abs(prev.y - lastSeen.y) > DRAG_CANCEL_PX;
    const click = clickCandidate && !movedFar;
    clickCandidate = false;

    if (!click) return;
    raycaster.setFromCamera(mouse, camera);
    const hit = raycaster.intersectObjects(nodeObjects, false)[0];
    if (hit?.object) onClickSprite?.(hit.object);
  }

  // --- per-frame tick ---
  function tick(target3D = rotateTarget) {
    if (!target3D) return;

    if (isDragging) {
      const dx = lastSeen.x - prev.x;
      const dy = lastSeen.y - prev.y;
      if (dx !== 0 || dy !== 0) {
        prev = { ...lastSeen };

        // camera-space axes
        const forward = new THREE.Vector3(); camera.getWorldDirection(forward).normalize();
        const up = camera.up.clone().normalize();
        const right = new THREE.Vector3().crossVectors(forward, up).normalize();

        const yawDelta   = dx * DRAG_SENS;
        const pitchDelta = dy * DRAG_SENS;

        const qYaw   = new THREE.Quaternion().setFromAxisAngle(up,    yawDelta);
        const qPitch = new THREE.Quaternion().setFromAxisAngle(right, pitchDelta);
        const qDelta = qYaw.multiply(qPitch);

        target3D.quaternion.premultiply(qDelta);

        // inertia from delta
        const angle = 2 * Math.acos(Math.min(1, qDelta.w));
        if (angle > 1e-6) {
          const s = Math.sqrt(1 - qDelta.w * qDelta.w);
          const axis = new THREE.Vector3(qDelta.x / s, qDelta.y / s, qDelta.z / s);
          angularVelocity.copy(axis.multiplyScalar(angle));
        }
      }
      return;
    }

    // inertia path
    if (angularVelocity.lengthSq() > 1e-8) {
      const angle = angularVelocity.length();
      const axis = angularVelocity.clone().normalize();
      const q = new THREE.Quaternion().setFromAxisAngle(axis, angle);
      target3D.quaternion.premultiply(q);
      angularVelocity.multiplyScalar(INERTIA_DECAY);
    }
  }

  // listeners
  document.addEventListener('mousemove', onMouseMove);
  document.addEventListener('mousedown', onMouseDown);
  document.addEventListener('mouseup', onMouseUp);

  return {
    tick,
    getAngularVelocity: () => angularVelocity.clone(),
    get dragging() { return isDragging; },
    dispose() {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mousedown', onMouseDown);
      document.removeEventListener('mouseup', onMouseUp);
    }
  };
}