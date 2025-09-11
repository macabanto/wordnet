// scene/orient.js
import * as THREE from 'three';

// Compose yaw/pitch/roll into a quaternion
export function composeQuaternion({ yaw = 0, pitch = 0, roll = 0 }) {
  const qYaw   = new THREE.Quaternion();
  const qPitch = new THREE.Quaternion();
  const qRoll  = new THREE.Quaternion();

  // yaw about world Y
  qYaw.setFromAxisAngle(new THREE.Vector3(0, 1, 0), yaw);

  // pitch about local X after yaw
  const xLocal = new THREE.Vector3(1, 0, 0).applyQuaternion(qYaw);
  qPitch.setFromAxisAngle(xLocal, pitch);

  // roll about local Z after yaw·pitch
  const qYawPitch = qYaw.clone().multiply(qPitch);
  const zLocal = new THREE.Vector3(0, 0, 1).applyQuaternion(qYawPitch);
  qRoll.setFromAxisAngle(zLocal, roll);

  // final quaternion
  return qYaw.multiply(qPitch).multiply(qRoll).normalize();
}

// Slerp between two quaternions (smooth blend)
export function slerpQuat(q1, q2, t) {
  return q1.clone().slerp(q2, t).normalize();
}

// Convert quaternion back to yaw/pitch/roll (optional)
export function toEulerAngles(q) {
  const euler = new THREE.Euler().setFromQuaternion(q, 'YXZ'); 
  return { yaw: euler.y, pitch: euler.x, roll: euler.z };
}