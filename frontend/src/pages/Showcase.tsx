/**
 * 展示视图（L3 展示岛）
 * ====================
 *
 * 数据星云：约 5000 粒子的分层流场。three.js 按需加载（独立懒加载 chunk），
 * 能力门槛（WebGL / 核数 / 动效偏好）不达标时降级到 CSS 星云——
 * 每一级都好看，只有复杂度递减。
 */
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight, Sparkles } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type SceneMode = 'loading' | 'webgl' | 'fallback'

/** 能力门槛：reduced-motion / 核心数 / WebGL 可用性，任一不满足则降级。 */
function canUseWebGL(): boolean {
  try {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return false
    const cores = navigator.hardwareConcurrency ?? 8
    if (cores < 4) return false
    const canvas = document.createElement('canvas')
    return Boolean(canvas.getContext('webgl2') ?? canvas.getContext('webgl'))
  } catch {
    return false
  }
}

export default function ShowcasePage() {
  const containerRef = useRef<HTMLDivElement>(null)
  const [mode, setMode] = useState<SceneMode>('loading')

  useEffect(() => {
    if (!canUseWebGL()) {
      setMode('fallback')
      return
    }
    let alive = true
    let dispose: (() => void) | undefined

    import('@/components/visual/nebula-scene')
      .then((module) => {
        if (!alive || !containerRef.current) return
        try {
          const handle = module.mountNebula(containerRef.current)
          dispose = handle.dispose
          setMode('webgl')
        } catch {
          setMode('fallback')
        }
      })
      .catch(() => {
        if (alive) setMode('fallback')
      })

    return () => {
      alive = false
      dispose?.()
    }
  }, [])

  return (
    <div className="relative h-[calc(100vh-7.5rem)] min-h-[560px] overflow-hidden rounded-2xl border border-border/60 bg-background">
      {/* three.js 场景容器 */}
      <div ref={containerRef} className="absolute inset-0" aria-hidden />

      {/* CSS 星云（降级层；webgl 就绪后淡出） */}
      <div
        className={cn(
          'pointer-events-none absolute inset-0 transition-opacity duration-1000',
          mode === 'webgl' && 'opacity-0',
        )}
        aria-hidden
      >
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,hsl(186_92%_50%/0.10),transparent_62%)]" />
        <div className="grid-bg absolute inset-0 opacity-30" />
        <div
          className="absolute inset-0 opacity-80"
          style={{
            backgroundImage: [
              'radial-gradient(1.6px 1.6px at 18% 26%, hsl(186 92% 72% / 0.9), transparent 62%)',
              'radial-gradient(1.2px 1.2px at 72% 18%, hsl(186 92% 72% / 0.7), transparent 62%)',
              'radial-gradient(1.8px 1.8px at 62% 68%, hsl(38 92% 62% / 0.8), transparent 62%)',
              'radial-gradient(1.1px 1.1px at 30% 74%, hsl(186 92% 72% / 0.6), transparent 62%)',
              'radial-gradient(1.4px 1.4px at 84% 48%, hsl(210 90% 66% / 0.7), transparent 62%)',
              'radial-gradient(1px 1px at 44% 42%, hsl(186 92% 72% / 0.5), transparent 62%)',
              'radial-gradient(1.3px 1.3px at 10% 58%, hsl(210 90% 66% / 0.6), transparent 62%)',
              'radial-gradient(1.1px 1.1px at 90% 80%, hsl(186 92% 72% / 0.5), transparent 62%)',
            ].join(', '),
          }}
        />
      </div>

      {/* 覆盖层 */}
      <div className="relative z-10 flex h-full flex-col items-center justify-center px-6 text-center">
        <div className="animate-rise flex items-center gap-2 text-[0.7rem] font-medium uppercase tracking-[0.22em] text-primary/90">
          <Sparkles className="h-3.5 w-3.5" />
          WebInsight · Showcase
        </div>
        <h1
          className="animate-rise mt-4 max-w-2xl text-3xl font-semibold leading-tight tracking-tight sm:text-[2.6rem]"
          style={{ ['--stagger' as string]: '120ms' }}
        >
          数据在此流动
        </h1>
        <p
          className="animate-rise mt-3 max-w-lg text-sm leading-relaxed text-muted-foreground"
          style={{ ['--stagger' as string]: '220ms' }}
        >
          从任意站点的可采判定，到定时采集、合规留痕与洞察报告——一条看得见的流水线。
        </p>
        <div
          className="animate-rise mt-7 flex flex-wrap items-center justify-center gap-3"
          style={{ ['--stagger' as string]: '320ms' }}
        >
          <Link to="/">
            <Button>
              进入工作台
              <ArrowUpRight className="ml-1 h-3.5 w-3.5" />
            </Button>
          </Link>
          <Link to="/compliance">
            <Button variant="outline">看看合规中心</Button>
          </Link>
        </div>

        <div className="absolute bottom-5 left-0 right-0 text-center text-[0.66rem] text-muted-foreground/70">
          {mode === 'webgl'
            ? 'Three.js 场景运行中（独立懒加载 chunk）· 跟随鼠标轻微视差'
            : mode === 'fallback'
              ? '已按设备能力 / 动效偏好降级为静态星云'
              : '正在加载场景…'}
        </div>
      </div>
    </div>
  )
}
