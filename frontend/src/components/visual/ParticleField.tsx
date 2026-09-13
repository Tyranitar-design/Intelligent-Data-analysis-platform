/**
 * 粒子场（页面背景层）
 * ====================
 *
 * 全屏 Canvas 粒子网络，作为内容的背景层。
 *
 * 设计取向是"能感觉到但不抢戏"：
 * - 粒子密度按屏幕面积自适应，但上限压得很低——背景噪点多了会干扰读表格
 * - 近邻连线而非全连接，避免变成一团发光的雾
 * - 指针产生微弱斥力，让页面有"活着"的反馈，但不做夸张的跟随效果
 * - 颜色跟随设计系统主色（青），不引入第二套色相
 *
 * 性能与可访问性：
 * - 按 devicePixelRatio 适配高清屏，但上限 2 倍避免 4K 屏上开太多像素
 * - 页面不可见时暂停动画（切到后台标签页不再空转）
 * - 尊重 prefers-reduced-motion：偏好减弱动效时完全不渲染
 */
import { useEffect, useRef } from 'react'

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  r: number
}

const MAX_PARTICLES = 72
const DENSITY_DIVISOR = 26000
const LINK_DISTANCE = 130
const POINTER_RADIUS = 150
const MAX_DPR = 2

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export default function ParticleField({ className }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (prefersReducedMotion()) return

    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let width = 0
    let height = 0
    let dpr = 1
    let particles: Particle[] = []
    let frame = 0
    let running = true

    const pointer = { x: -9999, y: -9999, active: false }

    function resize() {
      dpr = Math.min(window.devicePixelRatio || 1, MAX_DPR)
      width = window.innerWidth
      height = window.innerHeight
      canvas!.width = Math.floor(width * dpr)
      canvas!.height = Math.floor(height * dpr)
      canvas!.style.width = `${width}px`
      canvas!.style.height = `${height}px`
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0)
      seed()
    }

    function seed() {
      const count = Math.min(
        MAX_PARTICLES,
        Math.floor((width * height) / DENSITY_DIVISOR),
      )
      particles = Array.from({ length: count }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.28,
        vy: (Math.random() - 0.5) * 0.28,
        r: Math.random() * 1.1 + 0.5,
      }))
    }

    function draw() {
      if (!running) return
      const c = ctx!
      c.clearRect(0, 0, width, height)

      for (const p of particles) {
        p.x += p.vx
        p.y += p.vy

        if (p.x < 0 || p.x > width) p.vx *= -1
        if (p.y < 0 || p.y > height) p.vy *= -1

        // 指针斥力：只推开，不吸引，避免粒子聚成不自然的团
        if (pointer.active) {
          const dx = p.x - pointer.x
          const dy = p.y - pointer.y
          const dist2 = dx * dx + dy * dy
          if (dist2 < POINTER_RADIUS * POINTER_RADIUS && dist2 > 0.01) {
            const force = (POINTER_RADIUS * POINTER_RADIUS - dist2) / 900000
            p.vx += dx * force * 0.12
            p.vy += dy * force * 0.12
          }
        }

        // 限速：斥力叠加后不能让粒子变成飞弹
        const speed = Math.hypot(p.vx, p.vy)
        if (speed > 0.9) {
          p.vx = (p.vx / speed) * 0.9
          p.vy = (p.vy / speed) * 0.9
        }
      }

      // 连线：只连近邻
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const a = particles[i]
          const b = particles[j]
          const dx = a.x - b.x
          const dy = a.y - b.y
          const dist = Math.hypot(dx, dy)
          if (dist > LINK_DISTANCE) continue

          const alpha = (1 - dist / LINK_DISTANCE) * 0.16
          c.strokeStyle = `rgba(34, 211, 238, ${alpha})`
          c.lineWidth = 0.6
          c.beginPath()
          c.moveTo(a.x, a.y)
          c.lineTo(b.x, b.y)
          c.stroke()
        }
      }

      // 粒子本体
      for (const p of particles) {
        c.fillStyle = 'rgba(34, 211, 238, 0.42)'
        c.beginPath()
        c.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        c.fill()
      }

      frame = requestAnimationFrame(draw)
    }

    function handlePointerMove(event: PointerEvent) {
      pointer.x = event.clientX
      pointer.y = event.clientY
      pointer.active = true
    }

    function handlePointerLeave() {
      pointer.active = false
      pointer.x = -9999
      pointer.y = -9999
    }

    // 后台标签页暂停，避免无意义的 CPU 占用
    function handleVisibility() {
      if (document.hidden) {
        running = false
        cancelAnimationFrame(frame)
      } else if (!running) {
        running = true
        frame = requestAnimationFrame(draw)
      }
    }

    resize()
    frame = requestAnimationFrame(draw)

    window.addEventListener('resize', resize)
    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerleave', handlePointerLeave)
    document.addEventListener('visibilitychange', handleVisibility)

    return () => {
      running = false
      cancelAnimationFrame(frame)
      window.removeEventListener('resize', resize)
      window.removeEventListener('pointermove', handlePointerMove)
      window.removeEventListener('pointerleave', handlePointerLeave)
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className={className}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 0,
        pointerEvents: 'none',
        // 上淡下浓：顶部让位给顶栏与标题，中部以下逐渐淡出
        maskImage:
          'radial-gradient(120% 90% at 50% 0%, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.35) 55%, transparent 100%)',
        WebkitMaskImage:
          'radial-gradient(120% 90% at 50% 0%, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.35) 55%, transparent 100%)',
      }}
    />
  )
}
