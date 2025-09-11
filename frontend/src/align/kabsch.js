import * as THREE from 'three';

export function meanVec3(arr){ const m=new THREE.Vector3(); for(const v of arr)m.add(v); return m.multiplyScalar(arr.length?1/arr.length:0); }

function covariance3x3(A0,B0){
  const H = new THREE.Matrix3(); const h = [0,0,0,0,0,0,0,0,0];
  for (let i=0;i<A0.length;i++){
    const a=A0[i], b=B0[i];
    h[0]+=a.x*b.x; h[1]+=a.x*b.y; h[2]+=a.x*b.z;
    h[3]+=a.y*b.x; h[4]+=a.y*b.y; h[5]+=a.y*b.z;
    h[6]+=a.z*b.x; h[7]+=a.z*b.y; h[8]+=a.z*b.z;
  }
  H.set(h[0],h[1],h[2], h[3],h[4],h[5], h[6],h[7],h[8]); return H;
}

// Nearest orthogonal to M via polar iterations
function nearestRotationPolar(M){
  const I=[1,0,0,0,1,0,0,0,1];
  let X = M.toArray(); const XT=new Float32Array(9), XinvT=new Float32Array(9);

  const transpose=(A,AT)=>{ AT[0]=A[0];AT[1]=A[3];AT[2]=A[6]; AT[3]=A[1];AT[4]=A[4];AT[5]=A[7]; AT[6]=A[2];AT[7]=A[5];AT[8]=A[8]; };
  const invert3x3=(A,out)=>{
    const a=A,b=out;
    const a00=a[0],a01=a[1],a02=a[2], a10=a[3],a11=a[4],a12=a[5], a20=a[6],a21=a[7],a22=a[8];
    const c00=a11*a22-a12*a21, c01=a02*a21-a01*a22, c02=a01*a12-a02*a11;
    const det=a00*c00+a10*c01+a20*c02; if (Math.abs(det)<1e-12){ out.set(I); return 0; }
    const inv=1/det;
    b[0]=c00*inv; b[1]=(a12*a20-a10*a22)*inv; b[2]=(a10*a21-a11*a20)*inv;
    b[3]=c01*inv; b[4]=(a00*a22-a02*a20)*inv; b[5]=(a01*a20-a00*a21)*inv;
    b[6]=c02*inv; b[7]=(a02*a10-a00*a12)*inv; b[8]=(a00*a11-a01*a10)*inv;
    return det;
  };

  for (let k=0;k<12;k++){
    transpose(X,XT); const det=invert3x3(XT,XinvT); if (!det) break;
    for (let i=0;i<9;i++) X[i]=0.5*(X[i]+XinvT[i]);
    const off=Math.abs(X[1]+X[3])+Math.abs(X[2]+X[6])+Math.abs(X[5]+X[7]); if (off<1e-7) break;
  }
  const detX = X[0]*(X[4]*X[8]-X[5]*X[7]) - X[1]*(X[3]*X[8]-X[5]*X[6]) + X[2]*(X[3]*X[7]-X[4]*X[6]);
  if (detX<0){ // ensure proper rotation
    const c0=Math.hypot(X[0],X[3],X[6]), c1=Math.hypot(X[1],X[4],X[7]), c2=Math.hypot(X[2],X[5],X[8]);
    const j=(c0<=c1&&c0<=c2)?0:(c1<=c2?1:2); X[j]*=-1; X[j+3]*=-1; X[j+6]*=-1;
  }
  const R=new THREE.Matrix3(); R.fromArray(X); return R;
}

export function kabschRotation(sharedIds, currentPos, targetPos){
  const A=[], B=[];
  for (const id of sharedIds){
    const a=currentPos[id], b=targetPos[id];
    if (a && b){ A.push(a.clone()); B.push(b.clone()); }
  }
  if (A.length<2) return new THREE.Matrix3().identity();
  const aMean=meanVec3(A), bMean=meanVec3(B);
  const A0=A.map(v=>v.sub(aMean)), B0=B.map(v=>v.sub(bMean));
  const H=covariance3x3(A0,B0);
  return nearestRotationPolar(H);
}