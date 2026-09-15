/**
 * 工程网格背景层（v3 精密工程）
 * ==============================
 * v2 的三层极光团已被移除——参考图三轮评审一致判定"极光/光团"属于装饰过载，
 * 与数据语义无关且会干扰前景文字对比度。v3 改为只有两样东西：
 *   1. 一张 32px 的 1px 精密工程网格（约 3% 不透明度），提供"图纸/仪器"的语义纵深
 *   2. 极弱的方向性暗角，把视线收拢到内容区
 *
 * 与 ParticleField 的关系：
 * - ParticleField（cyan 粒子网络）已在 v3 中从布局移除——参考图评审判定彩色粒子
 *   属装饰噪音，与"实色简洁"的工程语言冲突。组件文件仍保留，需要时可挂回。
 * - 本组件：静态网格 + 暗角，零 rAF、零成本，是 v3 唯一的背景层。
 *
 * 层次（自后向前）：工程网格 → 颗粒 → 暗角 → 内容
 * 纪律：无彩色光团、无模糊、无发光；只有静态纹理。
 */
export default function AuroraBackdrop() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 overflow-hidden"
      style={{ zIndex: 0 }}
    >
      {/* 精密工程网格：向顶部淡出，避免整页铺满细线造成视觉疲劳 */}
      <div
        className="eng-grid absolute inset-0"
        style={{
          maskImage: 'radial-gradient(130% 75% at 50% 0%, black 0%, transparent 78%)',
          WebkitMaskImage: 'radial-gradient(130% 75% at 50% 0%, black 0%, transparent 78%)',
        }}
      />

      {/* 颗粒：消除大面积纯色的塑料感（v3 已降到 2%） */}
      <div className="noise-layer absolute inset-0 opacity-80" />

      {/* 方向性暗角：不引入任何色相，只做明度收拢 */}
      <div
        className="absolute inset-0"
        style={{
          background:
            'radial-gradient(125% 80% at 50% 0%, transparent 45%, hsl(222 60% 2% / 0.5) 100%)',
        }}
      />
    </div>
  )
}