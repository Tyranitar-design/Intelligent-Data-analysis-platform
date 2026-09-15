/**
 * ECharts 按需注册
 * ================
 *
 * 全量 `import * as echarts from 'echarts'` 会给主包增加约 1 MB。
 * 这里只注册实际用到的图表类型与组件。
 *
 * 注意：新增图表类型时必须在此处注册，否则表现为"图表区域空白但没有报错"——
 * 这是 ECharts 按需引入最典型的坑。
 */
import * as echarts from 'echarts/core'
import { BarChart, HeatmapChart, LineChart, PieChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  BarChart,
  HeatmapChart,
  LineChart,
  PieChart,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
  CanvasRenderer,
])

/**
 * 图表的 v4 调色板（与 index.css 的 tokens 一致，2026-09-15 目标图校准）
 * =====================================================================
 *
 * 首色 = 亮青 188 84% 56% (#31d4ed)——目标图（DataHarbor）的大数字/圆弧/主序列色相。
 * 其余沿用语义系：琥珀 / 绿 / 紫 / 红 / 蓝。
 */
export const CHART_THEME = {
  color: ['#31d4ed', '#f1a92c', '#2adf6d', '#a569bf', '#d93a3a', '#5b9bd5'],
  textStyle: { fontSize: 11, color: 'rgba(226,232,240,0.75)' },
  backgroundColor: 'transparent',
}

/**
 * 统一动效参数（L1 · 动效基础设施）
 * =================================
 *
 * 图表入场节奏：800ms cubicOut，更新 450ms。放位规则：
 * `{ ...CHART_THEME, ...CHART_MOTION, ...后端 option }` ——
 * 后端显式指定的 animation 字段优先（它才是可视化配置的生产者）。
 */
export const CHART_MOTION = {
  animationDuration: 800,
  animationEasing: 'cubicOut',
  animationDurationUpdate: 450,
  animationEasingUpdate: 'cubicInOut',
} as const

export default echarts
export type { EChartsOption } from 'echarts'
