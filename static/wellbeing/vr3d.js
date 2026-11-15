// Real-time 3D theme worlds for the VR session player (three.js, rendered on screen).
//
// Comfort rules (motion sickness would defeat a wellbeing session):
//   * the camera never travels; the viewer can only look around (drag), within limits
//   * slow, gentle motion; a steady horizon; reduced-motion users get a near-still scene
// If WebGL is unavailable or anything fails, the page keeps its illustrated fallback.
import * as THREE from "../vendor/three/three.module.min.js";

function webglAvailable() {
  try {
    const probe = document.createElement("canvas");
    return Boolean(window.WebGLRenderingContext && (probe.getContext("webgl2") || probe.getContext("webgl")));
  } catch {
    return false;
  }
}

/* ------------------------------------------------------------------ helpers */

function random(seed) {
  let value = seed;
  return () => {
    value = (value * 16807) % 2147483647;
    return (value - 1) / 2147483646;
  };
}

function skyDome(top, middle, bottom) {
  const geometry = new THREE.SphereGeometry(420, 32, 20);
  const colors = [];
  const [a, b, c] = [new THREE.Color(top), new THREE.Color(middle), new THREE.Color(bottom)];
  const position = geometry.attributes.position;
  for (let i = 0; i < position.count; i += 1) {
    const h = position.getY(i) / 420; // -1 … 1
    const color = h > 0.12 ? b.clone().lerp(a, Math.min(1, (h - 0.12) / 0.6)) : c.clone().lerp(b, Math.max(0, (h + 0.2) / 0.32));
    colors.push(color.r, color.g, color.b);
  }
  geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  return new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide, fog: false, depthWrite: false }));
}

function stars(count, rand, { radius = 380, minHeight = 0.05, size = 1.6, color = "#ffffff", opacity = 0.9 } = {}) {
  const positions = new Float32Array(count * 3);
  for (let i = 0; i < count; i += 1) {
    const theta = rand() * Math.PI * 2;
    const y = minHeight + rand() * (1 - minHeight);
    const r = Math.sqrt(1 - y * y);
    positions.set([Math.cos(theta) * r * radius, y * radius, Math.sin(theta) * r * radius], i * 3);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  return new THREE.Points(geometry, new THREE.PointsMaterial({ color, map: dot(), size: size * 1.6, sizeAttenuation: false, transparent: true, opacity, fog: false, depthWrite: false }));
}

function canvasTexture(width, height, draw) {
  const surface = document.createElement("canvas");
  surface.width = width;
  surface.height = height;
  draw(surface.getContext("2d"), width, height);
  const texture = new THREE.CanvasTexture(surface);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

function glow(color, scale, opacity = 1) {
  const map = canvasTexture(128, 128, (ctx, w) => {
    const gradient = ctx.createRadialGradient(w / 2, w / 2, 0, w / 2, w / 2, w / 2);
    gradient.addColorStop(0, "rgba(255,255,255,1)");
    gradient.addColorStop(0.25, "rgba(255,255,255,.55)");
    gradient.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, w, w);
  });
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map, color, transparent: true, opacity, depthWrite: false, blending: THREE.AdditiveBlending, fog: false }));
  sprite.scale.setScalar(scale);
  return sprite;
}

let dotTexture;
function dot() {
  dotTexture ||= canvasTexture(64, 64, (ctx, w) => {
    const gradient = ctx.createRadialGradient(w / 2, w / 2, 0, w / 2, w / 2, w / 2);
    gradient.addColorStop(0, "rgba(255,255,255,1)");
    gradient.addColorStop(0.45, "rgba(255,255,255,.8)");
    gradient.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, w, w);
  });
  return dotTexture;
}

function terrain(size, segments, height, color) {
  const geometry = new THREE.PlaneGeometry(size, size, segments, segments);
  geometry.rotateX(-Math.PI / 2);
  const position = geometry.attributes.position;
  for (let i = 0; i < position.count; i += 1) position.setY(i, height(position.getX(i), position.getZ(i)));
  geometry.computeVertexNormals();
  return new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color, roughness: 1, flatShading: true }));
}

function scatter(count, rand, { min, max, avoid = () => false }) {
  const points = [];
  while (points.length < count) {
    const angle = rand() * Math.PI * 2;
    const distance = min + rand() * (max - min);
    const x = Math.cos(angle) * distance;
    const z = Math.sin(angle) * distance;
    if (!avoid(x, z)) points.push([x, z]);
  }
  return points;
}

function instanced(geometry, material, items, place) {
  const mesh = new THREE.InstancedMesh(geometry, material, items.length);
  const matrix = new THREE.Matrix4();
  const quaternion = new THREE.Quaternion();
  const scale = new THREE.Vector3();
  const offset = new THREE.Vector3();
  items.forEach((item, index) => {
    const { position, size = 1, rotation = 0, color } = place(item, index);
    offset.set(...position);
    quaternion.setFromAxisAngle(new THREE.Vector3(0, 1, 0), rotation);
    scale.setScalar(size);
    matrix.compose(offset, quaternion, scale);
    mesh.setMatrixAt(index, matrix);
    if (color) mesh.setColorAt(index, new THREE.Color(color));
  });
  return mesh;
}

function glyphSprite(text, color = "#e0e7ff") {
  const map = canvasTexture(128, 128, (ctx, w) => {
    ctx.fillStyle = color;
    ctx.font = "700 84px system-ui, 'Segoe UI', sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.shadowColor = "rgba(165,180,252,.9)";
    ctx.shadowBlur = 18;
    ctx.fillText(text, w / 2, w / 2 + 4);
  });
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map, transparent: true, depthWrite: false, fog: false }));
  sprite.scale.setScalar(0.8);
  return sprite;
}

function cloud(rand) {
  const group = new THREE.Group();
  const material = new THREE.MeshStandardMaterial({ color: "#ffffff", roughness: 1, flatShading: true, transparent: true, opacity: 0.92 });
  const puff = new THREE.IcosahedronGeometry(1, 1);
  for (let i = 0; i < 5; i += 1) {
    const mesh = new THREE.Mesh(puff, material);
    mesh.position.set(i * 1.5 - 3 + rand(), rand() * 0.8, rand() * 1.2);
    mesh.scale.setScalar(1.2 + rand() * 1.4);
    group.add(mesh);
  }
  return group;
}

// 10-second breathing cycle: 4 s in (0 → 1), 6 s out (1 → 0).
function breath(t) {
  const phase = t % 10;
  const ease = (x) => 0.5 - Math.cos(Math.PI * x) / 2;
  return phase < 4 ? ease(phase / 4) : 1 - ease((phase - 4) / 6);
}

/* ------------------------------------------------------------------ worlds */

const WORLDS = {
  calm(scene, rand) {
    scene.background = new THREE.Color("#141844");
    scene.fog = new THREE.FogExp2("#2b2458", 0.022);
    scene.add(skyDome("#0f1238", "#3f3784", "#c27aa6"));
    const farStars = stars(900, rand, { size: 1.3, opacity: 0.75 });
    const brightStars = stars(160, rand, { size: 2.4, color: "#fff7d6" });
    scene.add(farStars, brightStars);

    const moon = new THREE.Sprite(new THREE.SpriteMaterial({
      map: canvasTexture(256, 256, (ctx) => {
        ctx.fillStyle = "#fdf3c6";
        ctx.beginPath(); ctx.arc(128, 128, 90, 0, Math.PI * 2); ctx.fill();
        ctx.globalCompositeOperation = "destination-out";
        ctx.beginPath(); ctx.arc(165, 102, 82, 0, Math.PI * 2); ctx.fill();
      }), transparent: true, fog: false, depthWrite: false,
    }));
    moon.position.set(70, 85, -230); moon.scale.setScalar(36);
    const moonGlow = glow("#fff1c1", 90, 0.35); moonGlow.position.copy(moon.position);
    scene.add(moonGlow, moon);

    const earth = new THREE.Mesh(new THREE.SphereGeometry(7, 40, 24), new THREE.MeshStandardMaterial({ color: "#3b82f6", emissive: "#1d4ed8", emissiveIntensity: 0.55, roughness: 0.6, fog: false }));
    earth.position.set(-75, 52, -210);
    const continents = new THREE.Mesh(new THREE.SphereGeometry(7.05, 24, 16), new THREE.MeshBasicMaterial({ color: "#86efac", wireframe: true, transparent: true, opacity: 0.25, fog: false }));
    earth.add(continents);
    const earthGlow = glow("#7dd3fc", 34, 0.7); earthGlow.position.copy(earth.position);
    scene.add(earthGlow, earth);

    scene.add(terrain(220, 90, (x, z) => 0.45 * Math.sin(x * 0.09) + 0.4 * Math.cos(z * 0.07 + 1) + (z < -30 ? (-z - 30) * 0.08 : 0) - 0.4, "#2d2660"));

    const bushes = scatter(70, rand, { min: 5, max: 45, avoid: (x, z) => Math.abs(x) < 2.5 && z < 0 && z > -14 });
    scene.add(instanced(new THREE.IcosahedronGeometry(1, 1), new THREE.MeshStandardMaterial({ color: "#3d3380", roughness: 1, flatShading: true }), bushes,
      ([x, z]) => ({ position: [x, -0.2, z], size: 0.6 + rand() * 1.4, rotation: rand() * 6 })));

    const flowerColors = ["#f0abfc", "#fde68a", "#c4b5fd", "#fbcfe8", "#a5f3fc"];
    const flowers = scatter(260, rand, { min: 2.2, max: 22 });
    scene.add(instanced(new THREE.IcosahedronGeometry(0.07, 0), new THREE.MeshBasicMaterial({ color: "#ffffff" }), flowers,
      ([x, z]) => ({ position: [x, 0.15 + rand() * 0.25, z], color: flowerColors[Math.floor(rand() * flowerColors.length)] })));

    const lantern = new THREE.Group();
    const post = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.05, 1.5, 8), new THREE.MeshStandardMaterial({ color: "#1b1740" }));
    post.position.y = 0.75;
    const lamp = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.36, 0.28), new THREE.MeshStandardMaterial({ color: "#ffe6a0", emissive: "#ffc861", emissiveIntensity: 2 }));
    lamp.position.y = 1.62;
    const lampLight = new THREE.PointLight("#ffd27a", 6, 14, 1.6);
    lampLight.position.y = 1.62;
    const lampGlow = glow("#ffd98a", 3.2, 0.9);
    lampGlow.position.y = 1.62;
    lantern.add(post, lamp, lampLight, lampGlow);
    lantern.position.set(0.9, 0, -5.5);
    scene.add(lantern);

    const flyCount = 90;
    const flyBase = scatter(flyCount, rand, { min: 1.5, max: 14 }).map(([x, z]) => [x, 0.4 + rand() * 1.8, z, rand() * 10]);
    const flyPositions = new Float32Array(flyCount * 3);
    const flies = new THREE.Points(new THREE.BufferGeometry().setAttribute("position", new THREE.BufferAttribute(flyPositions, 3)),
      new THREE.PointsMaterial({ color: "#fde68a", map: dot(), size: 0.22, transparent: true, opacity: 0.95, blending: THREE.AdditiveBlending, depthWrite: false }));
    scene.add(flies);

    scene.add(new THREE.HemisphereLight("#8b7cf6", "#1b1740", 1.1));
    const moonLight = new THREE.DirectionalLight("#c7d2fe", 0.9);
    moonLight.position.set(70, 85, -230);
    scene.add(moonLight);

    return {
      camera: { position: [0, 1.5, 0], yaw: 0, pitch: 0.06 },
      update(t, motion) {
        earth.rotation.y = t * 0.05;
        farStars.material.opacity = 0.6 + 0.2 * Math.sin(t * 0.7) * motion;
        brightStars.material.opacity = 0.75 + 0.25 * Math.sin(t * 1.3 + 1) * motion;
        flyBase.forEach(([x, y, z, phase], i) => {
          flyPositions.set([x + Math.sin(t * 0.4 + phase) * 0.6 * motion, y + Math.sin(t * 0.7 + phase * 2) * 0.35 * motion, z + Math.cos(t * 0.35 + phase) * 0.6 * motion], i * 3);
        });
        flies.geometry.attributes.position.needsUpdate = true;
        flies.material.opacity = 0.6 + 0.4 * Math.abs(Math.sin(t * 1.7));
      },
      breathe(level) {
        lampLight.intensity = 3 + 7 * level;
        lampGlow.scale.setScalar(2.4 + 2.2 * level);
        lamp.material.emissiveIntensity = 1.2 + 1.6 * level;
      },
    };
  },

  nature(scene, rand) {
    scene.background = new THREE.Color("#5d7d74");
    scene.fog = new THREE.Fog("#5f7f76", 6, 62);
    scene.add(skyDome("#2c4a42", "#557a70", "#a9c3b8"));
    scene.add(terrain(200, 70, (x, z) => 0.35 * Math.sin(x * 0.12) * Math.cos(z * 0.1) - 0.2, "#1f3d33"));

    const trees = scatter(320, rand, { min: 8, max: 70, avoid: (x, z) => Math.abs(x) < 4 && z < 0 && z > -18 });
    const foliage = new THREE.MeshStandardMaterial({ color: "#ffffff", roughness: 0.9, flatShading: true });
    const tiers = [[3.2, 1.6, 2.6], [2.6, 1.25, 3.7], [2.0, 0.9, 4.7]];
    tiers.forEach(([height, radius, lift]) => {
      scene.add(instanced(new THREE.ConeGeometry(radius, height, 7), foliage, trees, ([x, z], i) => {
        const size = 0.8 + ((i * 37) % 10) / 14;
        const shade = ["#1f5446", "#245b4b", "#2b6a57", "#1a4a3e"][i % 4];
        return { position: [x, lift * size - 0.2, z], size, rotation: i, color: shade };
      }));
    });
    scene.add(instanced(new THREE.CylinderGeometry(0.16, 0.22, 1.6, 6), new THREE.MeshStandardMaterial({ color: "#3a2a20", roughness: 1 }), trees,
      ([x, z], i) => ({ position: [x, 0.6, z], size: 0.8 + ((i * 37) % 10) / 14 })));

    const ferns = scatter(120, rand, { min: 2.5, max: 16 });
    scene.add(instanced(new THREE.ConeGeometry(0.35, 0.5, 5), new THREE.MeshStandardMaterial({ color: "#3f8a5c", flatShading: true }), ferns,
      ([x, z]) => ({ position: [x, 0.05, z], size: 0.6 + rand() * 0.8, rotation: rand() * 6 })));

    const dropCount = 2200;
    const drops = new Float32Array(dropCount * 6);
    const dropSpeed = new Float32Array(dropCount);
    const spawn = (i, anyHeight) => {
      const x = (rand() - 0.5) * 46;
      const z = -rand() * 40 + 6;
      const y = anyHeight ? rand() * 18 : 18;
      drops.set([x, y, z, x - 0.06, y - 0.55, z], i * 6);
      dropSpeed[i] = 11 + rand() * 6;
    };
    for (let i = 0; i < dropCount; i += 1) spawn(i, true);
    const rain = new THREE.LineSegments(new THREE.BufferGeometry().setAttribute("position", new THREE.BufferAttribute(drops, 3)),
      new THREE.LineBasicMaterial({ color: "#d6efe6", transparent: true, opacity: 0.38 }));
    scene.add(rain);

    const ripples = Array.from({ length: 10 }, (_, i) => {
      const ring = new THREE.Mesh(new THREE.RingGeometry(0.18, 0.22, 32), new THREE.MeshBasicMaterial({ color: "#d6efe6", transparent: true, opacity: 0, side: THREE.DoubleSide }));
      ring.rotation.x = -Math.PI / 2;
      ring.position.set((rand() - 0.5) * 6, 0.02, -2 - rand() * 9);
      ring.userData.phase = i * 0.37;
      scene.add(ring);
      return ring;
    });

    const mist = Array.from({ length: 5 }, (_, i) => {
      const plane = new THREE.Mesh(new THREE.PlaneGeometry(60, 6), new THREE.MeshBasicMaterial({ color: "#e6fff6", transparent: true, opacity: 0.07, depthWrite: false }));
      plane.position.set(0, 1.2 + i * 0.5, -12 - i * 8);
      scene.add(plane);
      return plane;
    });

    scene.add(new THREE.HemisphereLight("#d9efe6", "#1b2f28", 1.6));
    const sky = new THREE.DirectionalLight("#e8fff6", 0.8);
    sky.position.set(-10, 30, 10);
    scene.add(sky);

    return {
      camera: { position: [0, 1.55, 0], yaw: 0, pitch: 0.02 },
      update(t, motion, dt) {
        const fall = dt * Math.max(motion, 0.25);
        for (let i = 0; i < dropCount; i += 1) {
          const k = i * 6;
          const step = dropSpeed[i] * fall;
          drops[k + 1] -= step; drops[k + 4] -= step;
          drops[k] -= step * 0.11; drops[k + 3] -= step * 0.11;
          if (drops[k + 4] < 0) spawn(i, false);
        }
        rain.geometry.attributes.position.needsUpdate = true;
        ripples.forEach((ring) => {
          const p = ((t * 0.45 + ring.userData.phase) % 1);
          ring.scale.setScalar(0.4 + p * 4);
          ring.material.opacity = 0.45 * (1 - p);
          if (p < 0.02) ring.position.set((Math.random() - 0.5) * 6, 0.02, -2 - Math.random() * 9);
        });
        mist.forEach((plane, i) => { plane.position.x = Math.sin(t * 0.05 + i) * 6 * motion; });
      },
      breathe(level) { mist.forEach((plane) => { plane.material.opacity = 0.05 + 0.06 * level; }); },
    };
  },

  learning(scene, rand) {
    scene.background = new THREE.Color("#0b1035");
    scene.fog = new THREE.FogExp2("#141a4a", 0.02);
    scene.add(skyDome("#070a26", "#1d2a7a", "#3b4fc4"));
    scene.add(stars(1100, rand, { minHeight: -0.4, size: 1.4 }));

    const pivot = new THREE.Group();
    pivot.position.set(0, 1.75, -6.5);
    scene.add(pivot);
    const globe = new THREE.Mesh(new THREE.SphereGeometry(1.5, 48, 32), new THREE.MeshStandardMaterial({ color: "#4f6bff", emissive: "#2536a8", emissiveIntensity: 0.7, roughness: 0.45, metalness: 0.1 }));
    const grid = new THREE.Mesh(new THREE.SphereGeometry(1.53, 18, 12), new THREE.MeshBasicMaterial({ color: "#c7d2fe", wireframe: true, transparent: true, opacity: 0.35 }));
    globe.add(grid);
    const halo = glow("#8ea6ff", 7, 0.55);
    const ring = new THREE.Mesh(new THREE.TorusGeometry(2.5, 0.025, 8, 160), new THREE.MeshBasicMaterial({ color: "#f0abfc", transparent: true, opacity: 0.8 }));
    ring.rotation.set(Math.PI / 2.4, 0.3, 0);
    const ring2 = new THREE.Mesh(new THREE.TorusGeometry(3.3, 0.015, 8, 160), new THREE.MeshBasicMaterial({ color: "#5eead4", transparent: true, opacity: 0.5 }));
    ring2.rotation.set(Math.PI / 1.8, -0.4, 0);
    pivot.add(halo, globe, ring, ring2);

    const glyphs = ["A", "あ", "Ж", "ع", "文", "Ω", "ñ", "λ", "ü", "한", "ß", "अ", "é", "ç"].map((letter, i) => {
      const sprite = glyphSprite(letter);
      sprite.userData = { radius: 2.9 + (i % 3) * 0.7, speed: 0.12 + (i % 4) * 0.03, angle: (i / 14) * Math.PI * 2, height: ((i * 7) % 5) * 0.45 - 0.9 };
      pivot.add(sprite);
      return sprite;
    });

    const platform = new THREE.Mesh(new THREE.CylinderGeometry(3.2, 3.6, 0.25, 64), new THREE.MeshStandardMaterial({ color: "#151a4d", roughness: 0.8 }));
    platform.position.set(0, -0.15, -6.5);
    const rim = new THREE.Mesh(new THREE.TorusGeometry(3.2, 0.03, 8, 120), new THREE.MeshBasicMaterial({ color: "#818cf8" }));
    rim.rotation.x = Math.PI / 2;
    rim.position.set(0, -0.02, -6.5);
    scene.add(platform, rim);

    const globeLight = new THREE.PointLight("#a5b4fc", 30, 20, 1.8);
    globeLight.position.set(0, 3, -4);
    scene.add(globeLight, new THREE.HemisphereLight("#a5b4fc", "#0b1035", 0.9));

    return {
      camera: { position: [0, 1.6, 0], yaw: 0, pitch: 0.03 },
      update(t, motion) {
        globe.rotation.y = t * 0.12 * Math.max(motion, 0.2);
        ring.rotation.z = t * 0.1 * motion;
        ring2.rotation.z = -t * 0.06 * motion;
        glyphs.forEach((sprite) => {
          const { radius, speed, angle, height } = sprite.userData;
          const a = angle + t * speed * Math.max(motion, 0.15);
          sprite.position.set(Math.cos(a) * radius, height + Math.sin(t * 0.8 + angle * 3) * 0.18 * motion, Math.sin(a) * radius);
        });
      },
      breathe(level) { halo.material.opacity = 0.35 + 0.4 * level; },
    };
  },

  active(scene, rand) {
    scene.background = new THREE.Color("#7cc4ff");
    scene.fog = new THREE.Fog("#d4ecff", 40, 190);
    scene.add(skyDome("#2f7fd6", "#7cc4ff", "#eaf6ff"));
    const sun = glow("#fff3b0", 70, 1);
    sun.position.set(90, 70, -220);
    scene.add(sun);

    const sea = new THREE.Mesh(new THREE.PlaneGeometry(600, 300, 60, 30), new THREE.MeshStandardMaterial({ color: "#2f9fd6", roughness: 0.35, metalness: 0.15, flatShading: true }));
    sea.rotation.x = -Math.PI / 2;
    sea.position.set(0, -0.8, -190);
    scene.add(sea);
    const seaBase = Float32Array.from(sea.geometry.attributes.position.array);

    scene.add(terrain(160, 70, (x, z) => 0.5 * Math.sin(x * 0.07) + 0.4 * Math.cos(z * 0.09) + (z < -38 ? -(-z - 38) * 0.12 : 0), "#6cc35e"));
    const hills = terrain(400, 50, (x, z) => (Math.abs(x) > 60 ? (Math.abs(x) - 60) * 0.25 : 0) * (0.6 + 0.4 * Math.sin(z * 0.05)), "#86cf6c");
    hills.position.z = -40;
    scene.add(hills);

    const pathRadius = 12;
    const pathCenter = new THREE.Vector3(0, 0, -16);
    const path = new THREE.Mesh(new THREE.RingGeometry(pathRadius - 0.7, pathRadius + 0.7, 96), new THREE.MeshStandardMaterial({ color: "#f0dcae", roughness: 1 }));
    path.rotation.x = -Math.PI / 2;
    path.position.set(pathCenter.x, 0.42, pathCenter.z);
    scene.add(path);

    const bike = new THREE.Group();
    const dark = new THREE.MeshStandardMaterial({ color: "#24304a", roughness: 0.6 });
    const red = new THREE.MeshStandardMaterial({ color: "#e85d3f", roughness: 0.5 });
    const wheels = [-0.55, 0.55].map((x) => {
      const wheel = new THREE.Mesh(new THREE.TorusGeometry(0.33, 0.045, 8, 28), dark);
      wheel.position.set(x, 0.38, 0);
      bike.add(wheel);
      return wheel;
    });
    const bar = (length, x, y, rz) => { const m = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, length, 6), red); m.position.set(x, y, 0); m.rotation.z = rz; bike.add(m); };
    bar(0.95, 0, 0.62, Math.PI / 2.1); bar(0.6, -0.28, 0.58, 0.6); bar(0.6, 0.3, 0.6, -0.5); bar(0.3, 0.5, 0.85, 0);
    const seat = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.05, 0.12), dark); seat.position.set(-0.3, 0.9, 0); bike.add(seat);
    scene.add(bike);

    const ball = new THREE.Mesh(new THREE.SphereGeometry(0.22, 28, 18), new THREE.MeshStandardMaterial({
      roughness: 0.5,
      map: canvasTexture(256, 128, (ctx, w, h) => {
        ctx.fillStyle = "#ffffff"; ctx.fillRect(0, 0, w, h); ctx.fillStyle = "#1f2937";
        for (let i = 0; i < 6; i += 1) { ctx.beginPath(); const cx = 22 + i * 44, cy = 64 + (i % 2 ? -26 : 26); for (let k = 0; k < 5; k += 1) { const a = (k / 5) * Math.PI * 2; ctx.lineTo(cx + Math.cos(a) * 14, cy + Math.sin(a) * 14); } ctx.fill(); }
      }),
    }));
    const shadow = new THREE.Mesh(new THREE.CircleGeometry(0.25, 24), new THREE.MeshBasicMaterial({ color: "#000000", transparent: true, opacity: 0.25 }));
    shadow.rotation.x = -Math.PI / 2;
    ball.position.set(-0.8, 0.6, -4.2);
    shadow.position.set(-0.8, 0.38, -4.2);
    scene.add(ball, shadow);

    const white = new THREE.MeshStandardMaterial({ color: "#ffffff" });
    const goal = new THREE.Group();
    [[-1.6, 0.9, 0, 1.8, 0], [1.6, 0.9, 0, 1.8, 0], [0, 1.8, 0, 3.24, Math.PI / 2]].forEach(([x, y, z, len, rz]) => {
      const post = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, len, 8), white); post.position.set(x, y, z); post.rotation.z = rz; goal.add(post);
    });
    const net = new THREE.Mesh(new THREE.PlaneGeometry(3.2, 1.8, 10, 6), new THREE.MeshBasicMaterial({ color: "#ffffff", wireframe: true, transparent: true, opacity: 0.35 }));
    net.position.set(0, 0.9, -0.6);
    goal.add(net);
    goal.position.set(4.5, 0.35, -10);
    goal.rotation.y = -0.5;
    scene.add(goal);

    const clouds = Array.from({ length: 7 }, (_, i) => {
      const c = cloud(rand);
      c.position.set(-120 + i * 40 + rand() * 20, 38 + rand() * 18, -120 - rand() * 60);
      c.scale.setScalar(2 + rand() * 1.5);
      scene.add(c);
      return c;
    });

    scene.add(new THREE.HemisphereLight("#ffffff", "#5fae55", 1.4));
    const sunLight = new THREE.DirectionalLight("#fff4d6", 2.2);
    sunLight.position.set(90, 70, -100);
    scene.add(sunLight);

    return {
      camera: { position: [0, 1.65, 2], yaw: 0, pitch: -0.04 },
      update(t, motion, dt) {
        const speed = 0.16 * Math.max(motion, 0.2);
        const angle = t * speed;
        bike.position.set(pathCenter.x + Math.cos(angle) * pathRadius, 0.42, pathCenter.z + Math.sin(angle) * pathRadius);
        bike.rotation.y = -angle;
        wheels.forEach((wheel) => { wheel.rotation.z -= dt * 6 * Math.max(motion, 0.2); });
        const bounce = Math.abs(Math.sin(t * 2.4 * Math.max(motion, 0.3)));
        ball.position.y = 0.6 + bounce * 1.1 * motion;
        ball.rotation.x += dt * 2 * motion;
        shadow.scale.setScalar(1 - bounce * 0.45 * motion);
        shadow.material.opacity = 0.28 - bounce * 0.15 * motion;
        clouds.forEach((c) => { c.position.x += dt * 1.2 * motion; if (c.position.x > 160) c.position.x = -160; });
        const position = sea.geometry.attributes.position;
        for (let i = 0; i < position.count; i += 1) position.setZ(i, seaBase[i * 3 + 2] + Math.sin(seaBase[i * 3] * 0.05 + t * 0.8) * 0.4 * motion);
        position.needsUpdate = true;
      },
      breathe() {},
    };
  },

  family(scene, rand) {
    scene.background = new THREE.Color("#ffd9ae");
    scene.fog = new THREE.Fog("#ffd7b8", 30, 140);
    scene.add(skyDome("#7fb8ff", "#ffd9ae", "#ffb3a0"));
    const sun = glow("#fff2c2", 60, 1);
    sun.position.set(-80, 50, -200);
    scene.add(sun);

    scene.add(terrain(200, 60, (x, z) => (Math.abs(x) > 14 ? (Math.abs(x) - 14) * 0.05 : 0) + 0.15 * Math.sin(z * 0.2) * (Math.abs(x) > 3 ? 1 : 0), "#a9d68a"));
    const road = new THREE.Mesh(new THREE.PlaneGeometry(3.2, 140), new THREE.MeshStandardMaterial({ color: "#f2d7b6", roughness: 1 }));
    road.rotation.x = -Math.PI / 2;
    road.position.set(0, 0.03, -60);
    scene.add(road);

    const walls = ["#fde7d6", "#f9d9c6", "#e8f1ff", "#fff4cf", "#e6f7ea", "#fbe0ea"];
    const roofs = ["#e0705a", "#c8475c", "#7c6fd6", "#e09a3e", "#4f9d8b"];
    for (let i = 0; i < 9; i += 1) {
      [-1, 1].forEach((side) => {
        const house = new THREE.Group();
        const w = 3 + rand() * 1.5, h = 2.4 + rand() * 1.2, d = 3 + rand();
        const body = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), new THREE.MeshStandardMaterial({ color: walls[(i + side + 6) % walls.length], roughness: 0.9 }));
        body.position.y = h / 2;
        const roof = new THREE.Mesh(new THREE.ConeGeometry(Math.max(w, d) * 0.78, 1.6, 4), new THREE.MeshStandardMaterial({ color: roofs[(i * 2 + (side > 0 ? 1 : 0)) % roofs.length], roughness: 0.8, flatShading: true }));
        roof.position.y = h + 0.8;
        roof.rotation.y = Math.PI / 4;
        const windowMaterial = new THREE.MeshStandardMaterial({ color: "#ffd772", emissive: "#ffb84d", emissiveIntensity: 0.6 });
        [-w * 0.25, w * 0.25].forEach((x) => {
          const pane = new THREE.Mesh(new THREE.PlaneGeometry(0.6, 0.6), windowMaterial);
          pane.position.set(x, h * 0.62, d / 2 + 0.01);
          house.add(pane);
        });
        const door = new THREE.Mesh(new THREE.PlaneGeometry(0.6, 1.1), new THREE.MeshStandardMaterial({ color: "#9c5b4a" }));
        door.position.set(0, 0.55, d / 2 + 0.01);
        house.add(body, roof, door);
        house.position.set(side * (6.5 + rand() * 1.5), 0, -6 - i * 8 - rand() * 2);
        house.rotation.y = side > 0 ? -Math.PI / 2 : Math.PI / 2;
        scene.add(house);
      });
    }
    const treeSpots = Array.from({ length: 24 }, (_, i) => [((i % 2) ? 1 : -1) * (3.4 + rand() * 1.2), -3 - i * 3.2]);
    scene.add(instanced(new THREE.IcosahedronGeometry(1, 1), new THREE.MeshStandardMaterial({ color: "#ffffff", roughness: 1, flatShading: true }), treeSpots,
      ([x, z], i) => ({ position: [x, 2.1, z], size: 0.8 + rand() * 0.5, color: ["#74b06b", "#6aa361", "#86c06c"][i % 3] })));
    scene.add(instanced(new THREE.CylinderGeometry(0.1, 0.14, 1.6, 6), new THREE.MeshStandardMaterial({ color: "#7b5a44" }), treeSpots,
      ([x, z]) => ({ position: [x, 0.8, z] })));

    const person = (height, color, extra) => {
      const group = new THREE.Group();
      const material = new THREE.MeshStandardMaterial({ color, roughness: 0.8 });
      const body = new THREE.Mesh(new THREE.CapsuleGeometry(height * 0.16, height * 0.42, 4, 10), material);
      body.position.y = height * 0.45;
      const head = new THREE.Mesh(new THREE.SphereGeometry(height * 0.13, 16, 12), new THREE.MeshStandardMaterial({ color: "#c98d6b", roughness: 0.8 }));
      head.position.y = height * 0.88;
      group.add(body, head);
      if (extra) extra(group, height);
      return group;
    };
    const adult = person(1.75, "#5a56a8");
    const child = person(1.15, "#5b6ee1", (group, h) => {
      const bag = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.38, 0.16), new THREE.MeshStandardMaterial({ color: "#f3a25b" }));
      bag.position.set(0, h * 0.52, 0.2);
      group.add(bag);
    });
    const walkers = new THREE.Group();
    adult.position.x = -0.35;
    child.position.x = 0.4;
    const hand = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.5, 6), new THREE.MeshStandardMaterial({ color: "#c98d6b" }));
    hand.rotation.z = Math.PI / 2.4;
    hand.position.set(0.05, 0.72, 0);
    walkers.add(adult, child, hand);
    scene.add(walkers);

    const clouds = Array.from({ length: 6 }, (_, i) => {
      const c = cloud(rand);
      c.position.set(-100 + i * 40, 34 + rand() * 14, -110 - rand() * 50);
      c.scale.setScalar(2 + rand());
      scene.add(c);
      return c;
    });

    scene.add(new THREE.HemisphereLight("#fff1dc", "#9bd17e", 1.5));
    const morning = new THREE.DirectionalLight("#ffe2b8", 2);
    morning.position.set(-60, 40, -60);
    scene.add(morning);

    return {
      camera: { position: [0, 1.6, 2.5], yaw: 0, pitch: -0.03 },
      update(t, motion, dt) {
        const pace = 0.55 * Math.max(motion, 0.2);
        const z = -3 - ((t * pace) % 32);
        walkers.position.set(0, 0.03, z);
        adult.position.y = Math.abs(Math.sin(t * 5 * Math.max(motion, 0.2))) * 0.05;
        child.position.y = Math.abs(Math.sin(t * 6 * Math.max(motion, 0.2) + 1)) * 0.06;
        clouds.forEach((c) => { c.position.x += dt * 0.8 * motion; if (c.position.x > 140) c.position.x = -140; });
      },
      breathe() {},
    };
  },
};

/* ------------------------------------------------------------------ player */

function start(target) {
  const key = target.dataset.scene;
  if (!WORLDS[key]) return;
  const stage = target.closest("[data-session-timer]") || target.parentElement;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const motion = reduced ? 0.12 : 1;
  const breathing = target.dataset.breathing === "true";

  const renderer = new THREE.WebGLRenderer({ canvas: target, antialias: true, powerPreference: "low-power" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;

  const scene = new THREE.Scene();
  const world = WORLDS[key](scene, random(key.length * 977 + 13));
  const camera = new THREE.PerspectiveCamera(62, 1, 0.1, 900);
  camera.position.set(...world.camera.position);
  camera.rotation.order = "YXZ";

  // Look-around: drag (mouse or touch) or arrow keys, within comfortable limits.
  const view = { yaw: 0, pitch: 0, targetYaw: 0, targetPitch: 0 };
  const limits = { yaw: 0.75, pitch: 0.28 };
  let dragging = null;
  target.addEventListener("pointerdown", (event) => {
    dragging = { x: event.clientX, y: event.clientY, yaw: view.targetYaw, pitch: view.targetPitch };
    target.setPointerCapture(event.pointerId);
    stage.classList.add("is-looking");
  });
  target.addEventListener("pointermove", (event) => {
    if (!dragging) return;
    const scale = 2.2 / Math.max(target.clientWidth, 1);
    view.targetYaw = THREE.MathUtils.clamp(dragging.yaw + (event.clientX - dragging.x) * scale, -limits.yaw, limits.yaw);
    view.targetPitch = THREE.MathUtils.clamp(dragging.pitch + (event.clientY - dragging.y) * scale, -limits.pitch, limits.pitch);
  });
  const release = () => { dragging = null; };
  target.addEventListener("pointerup", release);
  target.addEventListener("pointercancel", release);
  target.addEventListener("keydown", (event) => {
    const step = 0.08;
    const moves = { ArrowLeft: [step, 0], ArrowRight: [-step, 0], ArrowUp: [0, step], ArrowDown: [0, -step] }[event.key];
    if (!moves) return;
    event.preventDefault();
    view.targetYaw = THREE.MathUtils.clamp(view.targetYaw + moves[0], -limits.yaw, limits.yaw);
    view.targetPitch = THREE.MathUtils.clamp(view.targetPitch + moves[1], -limits.pitch, limits.pitch);
  });

  function resize() {
    const width = Math.max(target.clientWidth, 1);
    const height = Math.max(target.clientHeight, 1);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(target);
  resize();

  const clock = new THREE.Clock();
  let elapsed = 0;
  let running = true;
  function frame() {
    if (!running) return;
    const dt = Math.min(clock.getDelta(), 0.05);
    elapsed += dt;
    view.yaw += (view.targetYaw - view.yaw) * Math.min(1, dt * 4);
    view.pitch += (view.targetPitch - view.pitch) * Math.min(1, dt * 4);
    const sway = reduced ? 0 : Math.sin(elapsed * 0.11) * 0.025;
    camera.rotation.set(world.camera.pitch + view.pitch, world.camera.yaw + view.yaw + sway, 0);
    world.update(elapsed, motion, dt);
    const level = breath(performance.now() / 1000); // same clock as the soundscape
    world.breathe(breathing ? level : 0.55);
    renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) { running = false; clock.stop(); }
    else if (!running) { running = true; clock.start(); requestAnimationFrame(frame); }
  });
  window.addEventListener("pagehide", () => { running = false; renderer.dispose(); });

  frame();
  stage.classList.add("has-3d");
  target.hidden = false;
}

/* ------------------------------------------------------------------ boot */
// Runs last so every world builder above is defined before use.
const canvas = document.querySelector("[data-vr3d]");
if (canvas && webglAvailable()) {
  try {
    start(canvas);
  } catch (error) {
    console.warn("3D scene unavailable; showing the illustrated scene instead.", error);
  }
}
