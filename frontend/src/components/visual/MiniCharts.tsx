/**
 * 迷你图表组件（v5 升级）
 * ========================
 *
 * 纯 SVG 零依赖。数据真实性纪律：调用方只传真实数据，无序列时不渲染。
 */
import { useId } from 'react'

import { cn } from '@/lib/utils'

export function RingProgress({
  value,
  size = 56,
  stroke = 5,
  label,
  sub,
  className,
}: {
  /** 0..1 的比例（真实数据） */
  value: number
  size?: number
  stroke?: number
  label?: string
  sub?: string
  className?: string
}) {
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const clamped = Math.max(0, Math.min(1, value))
  return (
    <div
      className={cn('relative grid shrink-0 place-items-center', className)}
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={stroke}
          className="stroke-muted/30"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - clamped)}
          strokeLinecap="round"
          className="stroke-primary transition-[stroke-dashoffset] duration-700 ease-out"
        />
      </svg>
      <div className="absolute text-center leading-none">
        {label && (
          <div className="num text-[0.7rem] font-semibold text-foreground">{label}</div>
        )}
        {sub && <div className="mt-0.5 text-[0.52rem] text-muted-foreground">{sub}</div>}
      </div>
    </div>
  )
}

export function Sparkline({
  data,
  width = 132,
  height = 26,
  className,
}: {
  /** 真实数据序列（<2 个点不渲染） */
  data: number[]
  width?: number
  height?: number
  className?: string
}) {
  const gradientId = useId()
  if (!data || data.length < 2) return null
  const min = Math.min(...data)
  const max = Math.max(...data)
  const span = max - min || 1
  const step = width / (data.length - 1)
  const points = data.map(
    (v, i) =>
      [i * step, height - 3 - ((v - min) / span) * (height - 6)] as const,
  )
  const line = points
    .map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`)
    .join(' ')
  const area = `${line} L${width.toFixed(1)},${height} L0,${height} Z`
  return (
    <svg
      width="100%"
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className={className}
      aria-hidden
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.22" />
          <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${gradientId})`} />
      <path
        d={line}
        fill="none"
        strokeWidth="1.5"
        strokeLinecap="round"
        className="stroke-primary/80"
      />
    </svg>
  )
}
