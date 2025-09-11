import * as THREE from 'three';
import { CONFIG } from '../config.js';

export const WIDTH = window.innerWidth;
export const HEIGHT = window.innerHeight;

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
  window.addEventListener('resize', () => {
    const w = window.innerWidth;
    const h = window.innerHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  });
}