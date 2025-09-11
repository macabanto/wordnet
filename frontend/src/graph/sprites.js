import * as THREE from 'three';
import { CONFIG } from '../config.js';

export function createTextSprite(text, meta = {}) {
  const fontSize = CONFIG.SPRITE_FONT_SIZE;
  const padding = CONFIG.SPRITE_PADDING;
  const dpr = window.devicePixelRatio || 1;

  // --- canvas setup ---
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  ctx.font = `bold ${fontSize}px Arial`;
  const textWidth = ctx.measureText(text).width;
  const textHeight = fontSize;

  canvas.width = (textWidth + padding * 2) * dpr;
  canvas.height = (textHeight + padding * 2) * dpr;
  ctx.scale(dpr, dpr);

  // --- draw text in WHITE only ---
  ctx.font = `bold ${fontSize}px Arial`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.shadowColor = 'black';
  ctx.shadowBlur = CONFIG.SPRITE_SHADOW_BLUR;
  ctx.fillStyle = 'white'; // always white, tint later
  ctx.fillText(text, (canvas.width / dpr) / 2, (canvas.height / dpr) / 2);

  // --- make texture ---
  const texture = new THREE.Texture(canvas);
  texture.needsUpdate = true;

  // tint via material.color, default from CONFIG
  const material = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    color: new THREE.Color(CONFIG.SPRITE_COLOR ?? 'white')
  });

  const sprite = new THREE.Sprite(material);

  // scale sprite so text size is consistent
  const scaleDivisor = CONFIG.SPRITE_SCALE_DIVISOR;
  sprite.scale.set(
    canvas.width / dpr / scaleDivisor,
    canvas.height / dpr / scaleDivisor,
    1
  );

  // --- attach metadata for click handling ---
  const id =
    typeof meta.id === 'object' && meta.id?.$oid ? meta.id.$oid :
    typeof meta.id === 'object' && meta.id?._id  ? meta.id._id  :
    meta.id;

  sprite.userData = {
    type: 'textSprite',
    term: text,
    ...meta,
    id, // ensure it's always directly available
  };

  sprite.name = meta.term || text; // useful in dev tools

  return sprite;
}