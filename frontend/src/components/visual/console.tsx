/**
 * v3 精密工程 · 共享监控组件
 * ============================
 * 参考图（design/refs/v3-monitor-draft.png）复刻所抽出的公共件：
 * 全部零装饰——无发光、无玻璃、无彩虹色，语义色只出现在状态点与读数上。
 *
 *  - StatusStrip   ：控制台顶部的实时读数条（等宽数字 + 状态点）
 *  - Sparkline     : 极简走势线（SVG polyline，无坐标轴，用于卡片角落）
 *  - StatusPill    : 语义状态胶囊（ok / warn / err / info / off）
 *  - DualStatBar   : 基准值 vs 当前值的单色对比条（限速/覆盖率等）
 *  - SectionHead   : 面板标题行（左标题 + 右侧操作位），统一卡片头网格
 */
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

/* ------------------------------------------------------------------ */
/* 状态点语义色（v3 纪律：语义色只以小点/小胶囊出现）                    */
/* ------------------------------------------------------------------ */

export type Tone = 'ok' | 'warn' | 'err' | 'info' | 'off'

export const TONE_DOT: Record<Tone, string> = {
  ok: 'bg-emerald-400',
  warn: 'bg-amber-400',
  err: 'bg-red-400',
  info: 'bg-sky-400',
  off: 'bg-zinc-500',
}

export const TONE_TEXT: Record<Tone, string> = {
  ok: 'text-emerald-400',
  warn: 'text-amber-400',
  err: 'text-red-400',
  info: 'text-sky-400',
  off: 'text-zinc-400',
}

/* ------------------------------------------------------------------ */
/* StatusStrip — 实时读数条                                            */
/* ------------------------------------------------------------------ */

export function StripItem({
  label,
  value,
  tone,
}: {
  label: string
  value: ReactNode
  tone?: Tone
}) {
  return (
    <span className="flex items-center gap-1.5 whitespace-nowrap">
      {tone ? <span className={cn('status-dot', TONE_DOT[tone])} aria-hidden="true" /> : null}
      <span>{label}</span>
      <span className="num font-medium text-foreground/90">{value}</span>
    </span>
  )
}

export function StatusStrip({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('status-strip', className)}>{children}</div>
}

/* ------------------------------------------------------------------ */
/* Sparkline — 统一到 MiniCharts（v5：渐变 + 末端点 + 空态占位）        */
/* ------------------------------------------------------------------ */

export { Sparkline } from './MiniCharts'

/* ------------------------------------------------------------------ */
/* StatusPill — 状态胶囊（v5 合并统一：实底 .pill 语言）                 */
/* ------------------------------------------------------------------ */

const PILL_TONE: Record<Tone, string> = {
  ok: 'pill-ok',
  warn: 'pill-warn',
  err: 'pill-err',
  info: 'pill-info',
  off: 'pill-off',
}

export function StatusPill({ tone, children }: { tone: Tone; children: ReactNode }) {
  return <span className={cn('pill', PILL_TONE[tone])}>{children}</span>
}

/* ------------------------------------------------------------------ */
/* DualStatBar — 基准 vs 当前 单色对比条                                */
/* ------------------------------------------------------------------ */

export function DualStatBar({
  current,
  base,
  max,
  className,
}: {
  current: number
  base?: number
  max: number
  className?: string
}) {
  const curPct = Math.max(0, Math.min(100, (current / (max || 1)) * 100))
  const basePct = base == null ? null : Math.max(0, Math.min(100, (base / (max || 1)) * 100))
  return (
    <div className={cn('relative h-1.5 w-full overflow-hidden rounded-full bg-muted', className)}>
      <div
        className="absolute inset-y-0 left-0 rounded-full bg-primary/70"
        style={{ width: `${curPct}%` }}
      />
      {basePct != null ? (
        <div
          className="absolute inset-y-0 w-px bg-foreground/50"
          style={{ left: `${basePct}%` }}
          title="基准值"
        />
      ) : null}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* SectionHead — 面板标题行（标题左 / 操作右）                           */
/* ------------------------------------------------------------------ */

export function SectionHead({
  icon,
  title,
  meta,
  action,
}: {
  icon?: ReactNode
  title: string
  meta?: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="hairline-b flex items-center justify-between gap-3 px-4 py-3">
      <div className="flex min-w-0 items-center gap-2">
        {icon ? <span className="shrink-0 text-muted-foreground">{icon}</span> : null}
        <h3 className="truncate text-sm font-semibold">{title}</h3>
        {meta ? <span className="num shrink-0 text-[0.7rem] text-muted-foreground">{meta}</span> : null}
      </div>
      {action ? <div className="flex shrink-0 items-center gap-2">{action}</div> : null}
    </div>
  )
}
