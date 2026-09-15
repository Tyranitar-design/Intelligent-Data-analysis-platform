/**
 * 数据星云 · three.js 场景（L3 展示岛）
 * =====================================
 *
 * 命令式挂载（dynamic import 目标）：
 *
 *     const handle = mountNebula(container)
 *     // 卸载时：handle.dispose()
 *
 * 设计（原创美术方向）：
 * - 约 5000 粒子的分层流场——主壳体（扁平球面）+ 赤道数据流环 + 少数琥珀"数据点"；
 * - 呼吸波动在顶点着色器完成（CPU 每帧只转 group）；不引入后处理链控制体积；
 * - 缓慢自转 + 指针视差（阻尼跟随）；页面隐藏时暂停渲染。
 *
 * 生命周期：调用方负责在卸载时调用 `dispose`——停止 RAF、移除事件、释放 GPU 资源。
 */
import * as THREE from 'three'

const PARTICLE_COUNT = 5000

const COLOR_PRIMARY = new THREE.Color('#41d2bf')
const COLOR_DEEP = new THREE.Color('#2a8f82')
const COLOR_ACCENT = new THREE.Color('#f1a92c')

const VERTEX_SHADER = /* glsl */ `
  attribute float aSize;
  attribute float aPhase;
  attribute vec3 aColor;
  uniform float uTime;
  varying vec3 vColor;
  varying float vAlpha;

  void main() {
    vColor = aColor;
    // 呼吸波动：沿径向轻微位移（无 GPGPU 的近似，保持轻量）
    float breathe = sin(uTime * 0.6 + aPhase + position.y * 0.22) * 0.32;
    vec3 pos = position + normalize(position + 0.0001) * breathe;

    vec4 mv = modelViewMatrix * vec4(pos, 1.0);
    gl_PointSize = aSize * (150.0 / -mv.z);
    // 远处粒子渐隐，增强纵深
    vAlpha = clamp(1.0 - (-mv.z - 6.0) / 30.0, 0.12, 1.0);
    gl_Position = projectionMatrix * mv;
  }
`

const FRAGMENT_SHADER = /* glsl */ `
  varying vec3 vColor;
  varying float vAlpha;

  void main() {
    vec2 uv = gl_PointCoord - vec2(0.5);
    float dist = length(uv);
    if (dist > 0.5) discard;
    float glow = smoothstep(0.5, 0.04, dist);
    gl_FragColor = vec4(vColor, glow * vAlpha * 0.92);
  }
`

export interface NebulaHandle {
  dispose: () => void
}

export function mountNebula(container: HTMLElement): NebulaHandle {
  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(
    55,
    container.clientWidth / Math.max(1, container.clientHeight),
    0.1,
    120,
  )
  camera.position.set(0, 0, 16)

  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: true,
    powerPreference: 'high-performance',
  })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
  renderer.setSize(container.clientWidth, Math.max(1, container.clientHeight))
  renderer.setClearColor(0x000000, 0)
  renderer.domElement.style.display = 'block'
  renderer.domElement.setAttribute('data-nebula', '1') // 挂载标记（验证脚本识别用）
  container.appendChild(renderer.domElement)

  // ---------------- 粒子分布 ----------------
  const positions = new Float32Array(PARTICLE_COUNT * 3)
  const colors = new Float32Array(PARTICLE_COUNT * 3)
  const sizes = new Float32Array(PARTICLE_COUNT)
  const phases = new Float32Array(PARTICLE_COUNT)

  for (let index = 0; index < PARTICLE_COUNT; index += 1) {
    let x: number
    let y: number
    let z: number
    const roll = Math.random()

    if (roll < 0.2) {
      // 赤道数据流环
      const angle = Math.random() * Math.PI * 2
      const radius = 4 + Math.random() * 2.4
      x = Math.cos(angle) * radius
      z = Math.sin(angle) * radius
      y = (Math.random() - 0.5) * 1.5
    } else {
      // 主壳体：扁平化球面（星系盘感）
      const u = Math.random() * 2 - 1
      const theta = Math.random() * Math.PI * 2
      const shell = Math.sqrt(1 - u * u)
      const radius = 6.5 + Math.random() * 5.5
      x = shell * Math.cos(theta) * radius
      z = shell * Math.sin(theta) * radius
      y = u * radius * 0.62
    }

    positions[index * 3] = x
    positions[index * 3 + 1] = y
    positions[index * 3 + 2] = z

    const accent = Math.random() < 0.06
    const deep = !accent && Math.random() < 0.3
    const color = accent ? COLOR_ACCENT : deep ? COLOR_DEEP : COLOR_PRIMARY
    colors[index * 3] = color.r
    colors[index * 3 + 1] = color.g
    colors[index * 3 + 2] = color.b

    sizes[index] = (accent ? 0.26 : 0.11) + Math.random() * 0.13
    phases[index] = Math.random() * Math.PI * 2
  }

  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geometry.setAttribute('aColor', new THREE.BufferAttribute(colors, 3))
  geometry.setAttribute('aSize', new THREE.BufferAttribute(sizes, 1))
  geometry.setAttribute('aPhase', new THREE.BufferAttribute(phases, 1))

  const material = new THREE.ShaderMaterial({
    vertexShader: VERTEX_SHADER,
    fragmentShader: FRAGMENT_SHADER,
    uniforms: { uTime: { value: 0 } },
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  })

  const points = new THREE.Points(geometry, material)
  const group = new THREE.Group()
  group.add(points)
  group.rotation.z = -0.18
  scene.add(group)

  // ---------------- 交互与循环 ----------------
  const clock = new THREE.Clock()
  const target = { x: 0, y: 0 }
  const current = { x: 0, y: 0 }
  let rafId = 0

  const onPointerMove = (event: PointerEvent) => {
    const rect = container.getBoundingClientRect()
    if (rect.width === 0 || rect.height === 0) return
    target.x = ((event.clientX - rect.left) / rect.width - 0.5) * 2
    target.y = ((event.clientY - rect.top) / rect.height - 0.5) * 2
  }

  const onResize = () => {
    const width = container.clientWidth
    const height = Math.max(1, container.clientHeight)
    camera.aspect = width / height
    camera.updateProjectionMatrix()
    renderer.setSize(width, height)
  }

  const animate = () => {
    rafId = requestAnimationFrame(animate)
    const time = clock.getElapsedTime()
    material.uniforms.uTime.value = time

    group.rotation.y = time * 0.045
    group.rotation.x = Math.sin(time * 0.07) * 0.05

    current.x += (target.x - current.x) * 0.04
    current.y += (target.y - current.y) * 0.04
    camera.position.x = current.x * 1.7
    camera.position.y = -current.y * 1.15
    camera.lookAt(0, 0, 0)

    renderer.render(scene, camera)
  }

  const onVisibility = () => {
    if (document.hidden) {
      cancelAnimationFrame(rafId)
      rafId = 0
    } else if (!rafId) {
      animate()
    }
  }

  container.addEventListener('pointermove', onPointerMove)
  window.addEventListener('resize', onResize)
  document.addEventListener('visibilitychange', onVisibility)
  animate()

  return {
    dispose: () => {
      cancelAnimationFrame(rafId)
      rafId = 0
      container.removeEventListener('pointermove', onPointerMove)
      window.removeEventListener('resize', onResize)
      document.removeEventListener('visibilitychange', onVisibility)
      geometry.dispose()
      material.dispose()
      renderer.dispose()
      if (renderer.domElement.parentElement === container) {
        container.removeChild(renderer.domElement)
      }
    },
  }
}
