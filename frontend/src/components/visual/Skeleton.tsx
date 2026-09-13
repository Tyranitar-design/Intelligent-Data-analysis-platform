/**
 * 骨架屏
 * ======
 *
 * 加载态用骨架而非 spinner：骨架能预示内容的结构与规模，
 * 让等待期间的布局不发生跳动，观感上比一个转圈更"快"。
 *
 * 所有骨架共用 `.animate-shimmer` 的微光扫过效果（定义在 index.css），
 * 保持与其他动效一致的节奏。
 */
import type { CSSProperties } from 'react'

import { cn } from '@/lib/utils'

export function Skeleton({
  className,
  style,
}: {
  className?: string
  style?: CSSProperties
}) {
  return (
    <div
      className={cn(
        'animate-shimmer relative overflow-hidden rounded-md bg-muted/45',
        className,
      )}
      style={style}
    />
  )
}

export function SkeletonText({
  lines = 3,
  className,
}: {
  lines?: number
  className?: string
}) {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton
          key={index}
          className={cn('h-3', index === lines - 1 ? 'w-2/3' : 'w-full')}
        />
      ))}
    </div>
  )
}

export function SkeletonStats({ count = 4 }: { count?: number }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="glass rounded-xl p-4">
          <Skeleton className="mb-3 h-2.5 w-16" />
          <Skeleton className="mb-2 h-7 w-24" />
          <Skeleton className="h-2.5 w-28" />
        </div>
      ))}
    </div>
  )
}

export function SkeletonCard({
  rows = 4,
  className,
}: {
  rows?: number
  className?: string
}) {
  return (
    <div className={cn('glass rounded-xl p-5', className)}>
      <div className="mb-4 flex items-center gap-2">
        <Skeleton className="h-4 w-4 rounded" />
        <Skeleton className="h-3 w-24" />
      </div>
      <SkeletonText lines={rows} />
    </div>
  )
}

export function SkeletonTable({ rows = 6, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="glass overflow-hidden rounded-xl">
      <div className="border-b border-border/60 px-5 py-3.5">
        <Skeleton className="h-3 w-32" />
      </div>
      <div className="divide-y divide-border/40">
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div key={rowIndex} className="flex items-center gap-4 px-5 py-3">
            {Array.from({ length: cols }).map((_, colIndex) => (
              <Skeleton
                key={colIndex}
                className={cn('h-3', colIndex === 0 ? 'w-28' : 'w-16')}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

export function SkeletonChart({ height = 260 }: { height?: number }) {
  return (
    <div className="glass overflow-hidden rounded-xl">
      <div className="border-b border-border/60 px-5 py-3">
        <Skeleton className="h-3 w-28" />
      </div>
      <div className="flex items-end gap-2 p-5" style={{ height }}>
        {[45, 72, 38, 88, 56, 64, 42, 78].map((value, index) => (
          <Skeleton
            key={index}
            className="flex-1 rounded-t"
            style={{ height: `${value}%` }}
          />
        ))}
      </div>
    </div>
  )
}
