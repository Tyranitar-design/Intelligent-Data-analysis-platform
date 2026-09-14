/**
 * 卡片微倾斜（L1 · 动效基础设施）
 * ================================
 *
 * 鼠标跟随的 3D 倾斜（±max 度）。克制取用：max ≤ 3，只用在统计卡等
 * "值得停顿半秒"的容器上，列表与表格不用。
 *
 * 纪律（v5 蓝图 §2.2）：
 * - `prefers-reduced-motion` 时不启用；
 * - 离开复位带 200ms 过渡；
 * - 只写 transform，不触发布局（will-change: transform）。
 */
import { useRef, type CSSProperties, type MouseEvent, type ReactNode } from 'react'
import { useReducedMotion } from 'motion/react'
import { cn } from '@/lib/utils'

type TiltProps = {
  children: ReactNode
  className?: string
  style?: CSSProperties
  /** 最大倾斜角度（度），建议 ≤ 3 */
  max?: number
}

export default function Tilt({ children, className, style, max = 2.5 }: TiltProps) {
  const reduce = useReducedMotion()
  const ref = useRef<HTMLDivElement>(null)

  if (reduce) {
    return (
      <div className={className} style={style}>
        {children}
      </div>
    )
  }

  const handleMove = (event: MouseEvent<HTMLDivElement>) => {
    const el = ref.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    if (rect.width === 0 || rect.height === 0) return
    const px = (event.clientX - rect.left) / rect.width - 0.5
    const py = (event.clientY - rect.top) / rect.height - 0.5
    el.style.transform = `perspective(700px) rotateX(${(-py * max).toFixed(2)}deg) rotateY(${(px * max).toFixed(2)}deg)`
  }

  const handleLeave = () => {
    const el = ref.current
    if (el) el.style.transform = ''
  }

  return (
    <div
      ref={ref}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      className={cn('transition-transform duration-200 ease-out will-change-transform', className)}
      style={style}
    >
      {children}
    </div>
  )
}
