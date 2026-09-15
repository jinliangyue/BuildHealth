/**
 * ECharts 按需引入
 * 只注册项目实际使用的组件，减小 bundle 体积。
 *
 * 注意：echarts-for-react 内部会 import 'echarts' 完整包，
 * 因此 tree-shaking 收益有限。本模块保留按需 use() 以备未来
 * 替换为直接使用 echarts/core 的实现。
 */
import * as echarts from "echarts/core";
import { LineChart, PieChart, RadarChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  MarkPointComponent,
  MarkLineComponent,
  RadarComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([
  LineChart,
  PieChart,
  RadarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  MarkPointComponent,
  MarkLineComponent,
  RadarComponent,
  CanvasRenderer,
]);

export default echarts;

