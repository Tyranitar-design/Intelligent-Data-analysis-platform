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

/** 图表的深色基调：与设计系统的主色保持一致 */
export const CHART_THEME = {
  color: ['#22d3ee', '#f59e0b', '#34d399', '#a78bfa', '#f87171', '#60a5fa'],
  textStyle: { fontSize: 11, color: 'rgba(226,232,240,0.75)' },
  backgroundColor: 'transparent',
}

export default echarts
export type { EChartsOption } from 'echarts'
