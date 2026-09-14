/**
 * 数字滚动（L1 · 动效基础设施）
 * ==============================
 *
 * 零依赖：rAF + easeOutCubic 收敛。数值更新时从"当前显示值"滚到"新值"，
 * 不会闪跳回 0。
 *
 * 纪律（v5 蓝图 §2.2）：
 * - `prefers-reduced-motion` 时直接落终值；
 * - 千分位分隔默认开启（数据平台的数字都好大）。
 */
import { useEffect, useRef, useState } from 'react'
import { useReducedMotion } from 'motion/react'

type CountUpProps = {
  value: number
  /** 滚动时长（秒） */
  duration?: number
  /** 小数位（默认 0） */
  decimals?: number
  className?: string
  /** 千分位分隔（默认 true） */
  separator?: boolean
}

export default function CountUp({
  value,
  duration = 0.9,
  decimals = 0,
  className,
  separator = true,
}: CountUpProps) {
  const reduce = useReducedMotion()
  const [display, setDisplay] = useState(() => (reduce ? value : 0))
  const displayRef = useRef(display)
  displayRef.current = display

  useEffect(() => {
    if (reduce) {
      setDisplay(value)
      return
    }
    const startValue = displayRef.current
    if (startValue === value) return

    let raf = 0
    const t0 = performance.now()
    const tick = (now: number) => {
      const progress = Math.min(1, (now - t0) / (duration * 1000))
      const eased = 1 - Math.pow(1 - progress, 3) // easeOutCubic
      setDisplay(startValue + (value - startValue) * eased)
      if (progress < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [value, reduce, duration])

  const text = separator
    ? display.toLocaleString('zh-CN', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      })
    : decimals > 0
      ? display.toFixed(decimals)
      : String(Math.round(display))

  return <span className={className}>{text}</span>
}
