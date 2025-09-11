// debug/poseHUD.js
export function createPoseHUD({ scene, camera, controls, getRotationVelocity }) {
  const el = document.createElement('div');
  Object.assign(el.style, {
    position: 'fixed',
    left: '10px',
    bottom: '10px',          // ⇦ bottom-left
    fontFamily: 'ui-monospace, SF Mono, Menlo, Consolas, monospace',
    fontSize: '12px',
    lineHeight: '1.35',
    padding: '8px 10px',
    background: 'rgba(0,0,0,0.65)',
    color: '#fff',
    borderRadius: '8px',
    zIndex: 9999,
    whiteSpace: 'pre',
    pointerEvents: 'none',
    maxWidth: '42vw'
  });
  document.body.appendChild(el);

  // live mouse snapshot
  let lastMouse = { x: 0, y: 0 };
  window.addEventListener('mousemove', (e) => { 
    lastMouse = { x: e.clientX, y: e.clientY }; 
  }, { passive: true });

  const fmt = (v) => {
    if (typeof v === 'number') return (Math.abs(v) < 1e-6 ? 0 : v).toFixed(5);
    if (Array.isArray(v)) return v.map(fmt).join(', ');
    if (v && typeof v.x === 'number' && typeof v.y === 'number' && typeof v.z === 'number') {
      return `${fmt(v.x)}, ${fmt(v.y)}, ${fmt(v.z)}`;
    }
    return String(v);
  };

  function update() {
    const sq = scene.quaternion, sr = scene.rotation, cq = camera.quaternion;
    const rv = getRotationVelocity ? getRotationVelocity() : null;

    el.textContent =
`SCENE
  quat:  ${fmt([sq.x, sq.y, sq.z, sq.w])}
  euler: ${fmt([sr.x, sr.y, sr.z])}
  needsUpdate: ${scene.matrixWorldNeedsUpdate}

CAMERA
  pos:  ${fmt(camera.position)}
  quat: ${fmt([cq.x, cq.y, cq.z, cq.w])}

CONTROLS
  dragging: ${!!controls?.dragging}
  state:    ${controls?.state ?? 'n/a'}

INPUT
  mouse: ${lastMouse.x}, ${lastMouse.y}

INERTIA
  rotVel: ${rv ? fmt(rv) : 'n/a'}
`;
  }

  // Optional: press "h" to hide/show
  let visible = true;
  function toggle() { 
    visible = !visible; 
    el.style.display = visible ? 'block' : 'none'; 
  }
  window.addEventListener('keydown', (e) => { 
    if (e.key.toLowerCase() === 'h') toggle(); 
  });

  return { update, element: el, toggle };
}