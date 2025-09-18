import * as THREE from 'three';
import { CONFIG } from '../config.js';

export const WIDTH = window.innerWidth;
export const HEIGHT = window.innerHeight;
export const DEVICE_PIXEL_RATIO = window.devicePixelRatio || 1;

export const scene = new THREE.Scene();

export const camera = new THREE.PerspectiveCamera(
  CONFIG.CAMERA_FOV,
  WIDTH / HEIGHT,
  CONFIG.CAMERA_NEAR,
  CONFIG.CAMERA_FAR
);
camera.position.z = CONFIG.CAMERA_Z;

export const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio || 1);
renderer.setSize(WIDTH, HEIGHT);
document.getElementById('container').appendChild(renderer.domElement);

export const raycaster = new THREE.Raycaster();
raycaster.params.Sprite = { threshold: CONFIG.SPRITE_THRESHOLD };

export const mouse = new THREE.Vector2();
export const nodeGroup = new THREE.Group();   // edges are currently disabled
scene.add(nodeGroup);

export const debugEl = document.getElementById('debug');

// Resize handling
export function attachResize() {
  let resizeTimeout;

  window.addEventListener('resize', () => {
    // clear any pending resize calls
    clearTimeout(resizeTimeout);

    // wait 150ms after last resize event
    resizeTimeout = setTimeout(() => {
      const w = window.innerWidth;
      const h = window.innerHeight;

      // Update camera
      camera.aspect = w / h;
      camera.updateProjectionMatrix();

      // Update renderer
      renderer.setSize(w, h);
      renderer.setPixelRatio(window.devicePixelRatio || 1);

      console.log(`Resized: ${w}x${h}, DPR=${window.devicePixelRatio}`);
    }, 150);
  });
}

/*
- - - - - - PSEUDOCODE - - - - - -
File: src/scene/scene.js

Imports
- * as THREE from 'three': Three.js core (Scene, Camera, Renderer, Vector2, Raycaster, Group).
- { CONFIG } from '../config.js': central tunables (camera, sprite threshold, etc.).

Constants
- WIDTH: snapshot of `window.innerWidth` at module load; used for initial renderer/camera sizing.
- HEIGHT: snapshot of `window.innerHeight` at module load; used for initial renderer/camera sizing.

Globals
- scene: Three.js `Scene` instance holding all renderable objects.
- camera: `PerspectiveCamera` configured from `CONFIG` and initial aspect `WIDTH/HEIGHT`; z-position set to `CONFIG.CAMERA_Z`.
- renderer: `WebGLRenderer` with antialiasing; pixel ratio set; size set; **canvas appended to `#container` immediately**.
- raycaster: `Raycaster` for picking; `.params.Sprite.threshold` set from `CONFIG.SPRITE_THRESHOLD`.
- mouse: `Vector2` used to store normalised device coords for raycasting.
- nodeGroup: `Group` added to `scene`; primary container for node sprites (edges currently disabled).
- debugEl: reference to `#debug` element (used by debug HUD if present).

Functions
- attachResize() → void  
  Registers a `window` `'resize'` listener that recalculates width/height, updates `camera.aspect`, calls `camera.updateProjectionMatrix()`, and resizes the `renderer`.  
  Side effects: mutates `camera.aspect`, `renderer` size; relies on `window.innerWidth/innerHeight`.

Classes
- (none)

Event Wiring
- `attachResize()` sets up a global `'resize'` handler when called (not at import time).

Exports
- Named exports: `WIDTH`, `HEIGHT`, `scene`, `camera`, `renderer`, `raycaster`, `mouse`, `nodeGroup`, `debugEl`, `attachResize`.

Notes
- This module performs side effects **at import time**: it creates and configures the renderer and appends its canvas to `#container`. Ensure the DOM has an element with `id="container"` before import/initialisation.
- `WIDTH`/`HEIGHT` are **static snapshots**; use `attachResize()` (and `window.innerWidth/innerHeight`) for up-to-date dimensions after resizes.
- `raycaster.params.Sprite.threshold` tunes sprite hit testing; keep in sync with `CONFIG.SPRITE_THRESHOLD`.
*/