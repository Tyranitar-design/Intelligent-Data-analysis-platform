/**
 * 滚动揭示容器（L1 · 动效基础设施）
 * ==================================
 *
 * 进入视口时浮现。position-driven：由视口位置驱动（motion whileInView），
 * 不进渲染循环、不劫持滚动。
 *
 * 纪律（v5 蓝图 §2.2）：
 * - `prefers-reduced-motion` 时不做任何等待，内容直接静态呈现；
 * - `once: true` —— 只播一次，重复滚动不骚扰；
 * - 延迟用 delay 秒（列表场景传 index * 0.05 错峰）。
 */
import type { CSSProperties, ReactNode } from 'react'
import { motion, useReducedMotion } from 'motion/react'

type RevealProps = {
  children: ReactNode
  /** 延迟（秒）；列表可传 index * 0.05 实现错峰 */
  delay?: number
  /** 入场位移距离（px），0 表示只淡入 */
  y?: number
  className?: string
  style?: CSSProperties
  /** 视口触发边距 */
  margin?: string
}

export default function Reveal({
  children,
  delay = 0,
  y = 14,
  className,
  style,
  margin = '-40px',
}: RevealProps) {
  const reduce = useReducedMotion()

  if (reduce) {
    return (
      <div className={className} style={style}>
        {children}
      </div>
    )
  }

  return (
    <motion.div
      className={className}
      style={style}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin }}
      transition={{ duration: 0.5, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  )
}
