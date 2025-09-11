// flow/transition.js
import * as THREE from 'three';
import { CONFIG } from '../config.js';
import { scene, nodeGroup } from '../scene/scene.js';
import { loadTermById } from '../data/api.js';
import { getId } from '../data/id.js';
import { nodeById, currentSynIdsFromScene, nodeObjects, removeNode, registerNode } from '../graph/state.js';
import { makeAnchorAt } from '../graph/anchors.js';
import { createTextSprite } from '../graph/sprites.js';

// --- tiny math ---
const ZERO = new THREE.Vector3(0,0,0);
const easeInOutQuad = (t) => (t < 0.5 ? 2*t*t : -1 + (4 - 2*t)*t);

// sets
const intersect = (A,B) => { const s = new Set(B); return A.filter(x => s.has(x)); };
const subtract  = (A,B) => { const s = new Set(B); return A.filter(x => !s.has(x)); };

// targets helper
function buildTargetMapFromDoc(termDoc) {
  const map = {};
  const list = Array.isArray(termDoc.linked_synonyms) ? termDoc.linked_synonyms : [];
  for (const s of list) map[getId(s)] = new THREE.Vector3(s.x, s.y, s.z);
  map[getId(termDoc)] = new THREE.Vector3(0, 0, 0);
  return map;
}

// cancellable scheduling
const PendingTimers = new Set();
function delay(ms, token) {
  return new Promise((resolve) => {
    const t = setTimeout(() => { PendingTimers.delete(t); resolve(); }, ms);
    PendingTimers.add(t);
    token?.cancelCallbacks.push(() => { clearTimeout(t); PendingTimers.delete(t); });
  });
}
function clearAllDelays() {
  for (const t of PendingTimers) clearTimeout(t);
  PendingTimers.clear();
}
export const TransitionManager = (() => {
  const active = new Set();
  let currentToken = null;

  function newToken() { return { cancelled: false, cancelCallbacks: [] }; }
  function cancelAll() {
    clearAllDelays();
    if (currentToken) {
      currentToken.cancelled = true;
      for (const cb of currentToken.cancelCallbacks) cb();
    }
    active.clear();
  }
  function track(p) { active.add(p); p.finally(() => active.delete(p)); }

  return {
    begin() { cancelAll(); currentToken = newToken(); return currentToken; },
    cancelAll,
    track,
    get token() { return currentToken; },
  };
})();

// raf helpers
function rafProgress(duration, onUpdate, token) {
  return new Promise((resolve) => {
    let rafId = null;
    const start = performance.now();
    const cancel = () => { if (rafId !== null) cancelAnimationFrame(rafId); resolve(); };
    token && token.cancelCallbacks.push(cancel);

    function frame(now) {
      if (token?.cancelled) return cancel();
      const t = Math.min((now - start) / duration, 1);
      onUpdate(t);
      if (t < 1) rafId = requestAnimationFrame(frame);
      else resolve();
    }
    rafId = requestAnimationFrame(frame);
  });
}

function tweenPosition(obj, toVec3, { duration, ease = easeInOutQuad, onUpdate, onComplete, token } = {}) {
  const from = obj.position.clone();
  const to = toVec3.clone();
  const p = rafProgress(duration, (t) => {
    if (token?.cancelled) return;
    const e = ease(t);
    obj.position.copy(from).lerp(to, e);
    onUpdate && onUpdate(obj);
    if (t === 1 && onComplete) onComplete();
  }, token);
  TransitionManager.track(p);
  return p;
}

// Smooth group translate so `targetObj` moves to origin, then bake.
function bakeGroupOffsetToChildren() {
  if (!nodeGroup.position.equals(ZERO)) {
    const off = nodeGroup.position.clone();
    nodeGroup.children.forEach(obj => obj.position.add(off));
    nodeGroup.position.set(0, 0, 0);
  }
}
function recenterAnimate(targetObj, duration = CONFIG.ANIM_TRANSLATE_MS || 500, token) {
  const from = nodeGroup.position.clone();
  const to   = from.clone().sub(targetObj.position);
  return rafProgress(duration, (t) => {
    if (token?.cancelled) return;
    const e = easeInOutQuad(t);
    nodeGroup.position.copy(from).lerp(to, e);
  }, token).then(() => bakeGroupOffsetToChildren());
}

function followMovingAnchor(obj, anchorObj, {
  duration,
  ease = easeInOutQuad,
  fade = true,
  scaleTo = 0.6,
  onUpdate,
  onComplete,
  token
} = {}) {
  const from = obj.position.clone();
  const scaleFrom = obj.scale.x;
  const startOpacity = obj.material?.opacity ?? 1;

  const p = rafProgress(duration, (t) => {
    if (token?.cancelled) return;
    const e = ease(t);
    const anchorPos = anchorObj.position;
    const cur = new THREE.Vector3().lerpVectors(from, anchorPos, e);
    obj.position.copy(cur);

    if (fade && obj.material) {
      obj.material.transparent = true;
      obj.material.opacity = startOpacity * (1 - e);
    }
    const s = THREE.MathUtils.lerp(scaleFrom, scaleTo, e);
    obj.scale.setScalar(s);

    onUpdate && onUpdate(obj);
    if (t === 1 && onComplete) onComplete();
  }, token);
  TransitionManager.track(p);
  return p;
}

// public: the click transition
export async function transitionToNode(clicked, mode = 'parallel') {
  const newCenterId = clicked.userData?.id;
  if (!newCenterId) return;
  const token = TransitionManager.begin();

  // fetch doc
  let doc;
  try {
    doc = await loadTermById(newCenterId);
    if (token.cancelled) return;
    if (!doc || !doc.term) return;
  } catch (e) {
    if (!token.cancelled) console.error('fetch failed:', e);
    return;
  }

  const oldCenter = nodeGroup.userData.center;
  const prevCenterId = oldCenter?.userData?.id;

  // sets before recenter
  const A0 = currentSynIdsFromScene();
  const A  = A0.filter(id => id !== newCenterId);
  const B  = (doc.linked_synonyms || []).map(s => getId(s)).filter(Boolean);
  const Aplus = prevCenterId ? [...new Set([...A, prevCenterId])] : A;

  const shared  = intersect(Aplus, B);
  const former  = subtract(A, B);
  const current = subtract(B, Aplus);

  const targetPos = buildTargetMapFromDoc(doc);

  // animate recenter
  await recenterAnimate(clicked, CONFIG.ANIM_TRANSLATE_MS || 500, token);
  if (token.cancelled) return;

  // center bookkeeping
  nodeGroup.userData.center = clicked;
  Object.assign(clicked.userData, { isCenter: true, isSynonym: false });
  { const i = nodeObjects.indexOf(clicked); if (i !== -1) nodeObjects.splice(i, 1); }

  // frozen anchor at old center after recenter
  let formerAnchor = null;
  if (oldCenter && oldCenter !== clicked) {
    formerAnchor = makeAnchorAt(oldCenter);
  }

  const D = CONFIG.ANIM_EXPAND_MS ?? 900;
  const schedule = (mode === 'serial')
    ? { shared: { delay: 0,       dur: 0.5*D },
        former: { delay: 0.5*D,   dur: 0.3*D },
        fresh:  { delay: 0.8*D,   dur: 0.8*D },
        gate: true }
    : { shared: { delay: 0,       dur: 1.0*D },
        former: { delay: 0,       dur: 0.6*D },
        fresh:  { delay: 0.15*D,  dur: 0.85*D },
        gate: false };

  const guard = (p) => { TransitionManager.track(p); return p; };

  const prevIsInNew = prevCenterId && B.includes(prevCenterId);
  let prevTask = Promise.resolve();
  if (oldCenter && oldCenter !== clicked) {
    if (prevIsInNew) {
      Object.assign(oldCenter.userData, { isCenter: false, isSynonym: true });
      if (!nodeObjects.includes(oldCenter)) nodeObjects.push(oldCenter);
      prevTask = guard(tweenPosition(oldCenter, targetPos[prevCenterId], {
        duration: schedule.shared.dur, token
      }));
    } else {
      prevTask = Promise.resolve(); // let former collapses go first
    }
  }

  const sharedTasks = shared.map((id) => {
    const obj = nodeById(id); if (!obj) return Promise.resolve();
    return delay(schedule.shared.delay, token).then(() =>
      guard(tweenPosition(obj, targetPos[id], { duration: schedule.shared.dur, token }))
    );
  });

  const formerTasks = former.map((id) => {
    const obj = nodeById(id); if (!obj || !formerAnchor) return Promise.resolve();
    return delay(schedule.former.delay, token).then(() =>
      guard(followMovingAnchor(obj, formerAnchor, {
        duration: schedule.former.dur, fade: true, token,
        onComplete: () => { if (!token.cancelled) removeNode(obj); }
      }))
    );
  });

  // fresh nodes: create via factory, merge userData, register so hover/click works
  const freshSet = new Set(current);
  const freshTasks = (doc.linked_synonyms || []).map((s) => {
    const sid = getId(s);
    if (!sid || !freshSet.has(sid)) return Promise.resolve();

    const spriteNode = createTextSprite(s.term, { id: sid, term: s.term, isSynonym: true });

    nodeGroup.add(spriteNode);
    registerNode(spriteNode);

    const tgt = targetPos[sid];
    const dir = tgt.clone().sub(clicked.position);
    const spawn = dir.lengthSq() === 0
      ? clicked.position.clone()
      : clicked.position.clone().add(dir.multiplyScalar(0.15));

    spriteNode.position.copy(spawn);
    if (spriteNode.material) {
      spriteNode.material.transparent = true;
      spriteNode.material.opacity = 0;
      spriteNode.material.color?.set?.(CONFIG.SPRITE_COLOR ?? '#ffffff');
    }

    return delay(schedule.fresh.delay, token).then(() =>
      guard(tweenPosition(spriteNode, tgt, {
        duration: schedule.fresh.dur, token,
        onUpdate: (o) => {
          const total = spawn.distanceTo(tgt);
          if (total === 0) { if (o.material) o.material.opacity = 1; return; }
          const left = o.position.distanceTo(tgt);
          const pTravel = Math.min(1, (total - left) / (0.5 * total));
          if (o.material) o.material.opacity = Math.min(1, pTravel);
        }
      }))
    );
  });

  if (schedule.gate) {
    await Promise.all([prevTask, ...sharedTasks]);
    await Promise.all(formerTasks);
    if (oldCenter && oldCenter !== clicked && !prevIsInNew) {
      await guard(followMovingAnchor(oldCenter, clicked, {
        duration: 0.5 * D, fade: true, token,
        onComplete: () => { if (!token.cancelled) removeNode(oldCenter); }
      }));
    }
    await Promise.all(freshTasks);
  } else {
    await Promise.all([prevTask, ...sharedTasks, ...formerTasks, ...freshTasks]);
    if (oldCenter && oldCenter !== clicked && !prevIsInNew) {
      await guard(followMovingAnchor(oldCenter, clicked, {
        duration: 0.5 * D, fade: true, token,
        onComplete: () => { if (!token.cancelled) removeNode(oldCenter); }
      }));
    }
  }

  if (formerAnchor) scene.remove(formerAnchor);

  // prune nodeObjects to exactly B
  for (let i = nodeObjects.length - 1; i >= 0; i--) {
    const id = nodeObjects[i].userData?.id;
    if (!id) continue;
    if (!B.includes(id)) nodeObjects.splice(i, 1);
  }
}