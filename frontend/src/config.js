// Central place for tunables. Keep your existing values here.
export const CONFIG = {
  API_BASE: import.meta.env.VITE_API_BASE ?? '',
  INITIAL_TERM_ID: '6890af9c82f836005c903e18',

  CAMERA_FOV: 60,
  CAMERA_NEAR: 0.1,
  CAMERA_FAR: 10000,
  CAMERA_Z: 400,

  SPRITE_COLOR: '#ffffff',
  SPRITE_FONT_SIZE: 64,
  SPRITE_PADDING: 20,
  SPRITE_SHADOW_BLUR: 8,
  SPRITE_SCALE_DIVISOR: 6,
  SPRITE_THRESHOLD: 0.7,

  LINE_COLOR: 0x888888,

  CLICK_THRESHOLD_PX: 4,
  INVERT_X: false,
  INVERT_Y: false,
  ROT_SPEED: 0.004,
  INERTIA_DECAY: 0.92,
  VELOCITY_EPS: 0.0003,

  ANIM_TRANSLATE_MS: 500,
  ANIM_EXPAND_MS: 900,
  TRANSITION_MODE: 'serial', // or 'parallel'
};

/*
 - - - - - PSEUDOCODE - - - - -
File: src/config.js

Imports
- (none)

Constants
- CONFIG: master configuration object for the frontend; groups all tunables and environment-derived values.
  - API_BASE: base URL for the backend API, injected by Vite via `VITE_API_BASE` (empty string if unset).
  - INITIAL_TERM_ID: seed lemma `_id` used for the first graph load.
  - CAMERA_FOV: Three.js perspective camera field of view in degrees.
  - CAMERA_NEAR: near clipping plane distance.
  - CAMERA_FAR: far clipping plane distance.
  - CAMERA_Z: initial camera z-position (distance from scene).
  - SPRITE_COLOR: CSS color for text sprites.
  - SPRITE_FONT_SIZE: base font size (px) for text sprites before scaling.
  - SPRITE_PADDING: pixel padding inside each text sprite canvas.
  - SPRITE_SHADOW_BLUR: blur radius for sprite text shadow/glow.
  - SPRITE_SCALE_DIVISOR: divisor used to convert font size into in-scene sprite scale.
  - SPRITE_THRESHOLD: visibility/LOD threshold for switching rendering behavior of sprites.
  - LINE_COLOR: numeric hex color for link lines in the graph.
  - CLICK_THRESHOLD_PX: max mouse movement (px) to still count as a click (vs drag).
  - INVERT_X: inverts horizontal drag direction if true.
  - INVERT_Y: inverts vertical drag direction if true.
  - ROT_SPEED: base multiplier for converting mouse delta to rotational velocity.
  - INERTIA_DECAY: per-frame damping factor applied to rotational velocity.
  - VELOCITY_EPS: epsilon under which inertial rotation is treated as stopped.
  - ANIM_TRANSLATE_MS: duration for camera/scene translate animations (ms).
  - ANIM_EXPAND_MS: duration for node expansion animations (ms).
  - TRANSITION_MODE: sequencing mode for transitions; `'serial'` or `'parallel'`.

Globals
- (none)

Functions
- (none)

Classes
- (none)

Event Wiring
- (none)

Exports
- Named export: `CONFIG` — imported by consumers needing app/scene tunables and API base.

Notes
- `API_BASE` is resolved at build/dev time by Vite; ensure `.env(.local|.production)` defines `VITE_API_BASE`.
- Keep this file side-effect free so tree-shaking and testability remain straightforward.
*/