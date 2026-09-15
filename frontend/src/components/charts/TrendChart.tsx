/**
 * TrendChart · ECharts 时序图
 * - 支持 series 数据 + anomaly 点叠加（markPoint）
 * - 浅色工程仪表盘主题
 */
import { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import "./echarts";

export interface TrendPoint {
  ts: string;
  value: number;
}
export interface AnomalyPoint {
  ts: string;
  value: number;
  severity: "low" | "medium" | "high";
  method: string;
}

interface Props {
  series: TrendPoint[];
  anomalies?: AnomalyPoint[];
  unit: string;
  metricLabel: string;
  height?: number;
}

const SEVERITY_COLOR: Record<string, string> = {
  low: "#94A3B8",
  medium: "#F59E0B",
  high: "#EF4444",
};

export default function TrendChart({
  series,
  anomalies = [],
  unit,
  metricLabel,
  height = 320,
}: Props) {
  const option: EChartsOption = useMemo(() => {
    const sortedSeries = [...series].sort(
      (a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime(),
    );
    const data = sortedSeries.map((p) => [p.ts, p.value]);

    const anomalyData = anomalies
      .filter((a) =>
        sortedSeries.some((p) => p.ts === a.ts),
      )
      .map((a) => ({
        name: `${a.severity}/${a.method}`,
        coord: [a.ts, a.value],
        itemStyle: { color: SEVERITY_COLOR[a.severity] || "#EF4444" },
      }));

    return {
      animation: false,
      grid: { left: 60, right: 30, top: 30, bottom: 50 },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "cross" },
        formatter: (params: unknown) => {
          const arr = params as Array<{
            axisValue: string;
            data: [string, number];
          }>;
          const p = arr[0];
          if (!p) return "";
          const dt = new Date(p.axisValue).toLocaleString("zh-CN");
          const v = typeof p.data === "object" ? p.data[1] : p.data;
          return `${dt}<br/>${metricLabel}: <b>${v}</b> ${unit}`;
        },
      },
      xAxis: {
        type: "time",
        axisLabel: { color: "#475569", fontSize: 11 },
        axisLine: { lineStyle: { color: "#CBD5E1" } },
      },
      yAxis: {
        type: "value",
        name: unit,
        nameTextStyle: { color: "#475569", fontSize: 11 },
        axisLabel: { color: "#475569", fontSize: 11 },
        splitLine: { lineStyle: { color: "#F1F5F9" } },
      },
      series: [
        {
          name: metricLabel,
          type: "line",
          showSymbol: false,
          smooth: false,
          sampling: "lttb",
          lineStyle: { color: "#2563EB", width: 1.5 },
          areaStyle: {
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: "rgba(37,99,235,0.15)" },
                { offset: 1, color: "rgba(37,99,235,0.02)" },
              ],
            },
          },
          data,
          markPoint:
            anomalyData.length > 0
              ? {
                  symbol: "circle",
                  symbolSize: 7,
                  data: anomalyData,
                  label: { show: false },
                }
              : undefined,
          markLine: {
            silent: true,
            symbol: "none",
            lineStyle: { color: "#94A3B8", type: "dashed", width: 1 },
            data: [],
          },
        },
      ],
    };
  }, [series, anomalies, unit, metricLabel]);

  return (
    <ReactECharts
      option={option}
      style={{ height, width: "100%" }}
      notMerge
      lazyUpdate
    />
  );
}
