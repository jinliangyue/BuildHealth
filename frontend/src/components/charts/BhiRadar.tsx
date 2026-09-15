/**
 * BHI 雷达图 · ECharts
 * 显示 5 个维度评分
 */
import { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import {
  BHI_WEIGHTS,
  DIMENSION_LABELS,
  type DimensionInfo,
} from "../../types/api";

interface Props {
  scores: Record<DimensionInfo["key"], number>;
  height?: number;
}

export default function BhiRadar({ scores, height = 280 }: Props) {
  const option: EChartsOption = useMemo(() => {
    const dims: DimensionInfo["key"][] = [
      "structural_safety",
      "facility_condition",
      "environmental_quality",
      "energy_performance",
      "fire_safety",
    ];
    return {
      animation: false,
      tooltip: {
        trigger: "item",
        formatter: (params: unknown) => {
          const arr = params as Array<{ name: string; value: number }>;
          const p = arr[0];
          if (!p) return "";
          const w = BHI_WEIGHTS[p.name as DimensionInfo["key"]];
          return `${DIMENSION_LABELS[p.name as DimensionInfo["key"]]}<br/>Score: <b>${p.value}</b><br/>Weight: ${(w * 100).toFixed(0)}%`;
        },
      },
      radar: {
        indicator: dims.map((d) => ({ name: d, max: 100 })),
        radius: "65%",
        splitArea: { areaStyle: { color: ["#F8FAFC", "#F1F5F9"] } },
        axisName: {
          color: "#475569",
          fontSize: 11,
        },
      },
      series: [
        {
          type: "radar",
          data: [
            {
              name: "BHI Dimensions",
              value: dims.map((d) => scores[d] ?? 0),
              areaStyle: { color: "rgba(37,99,235,0.18)" },
              lineStyle: { color: "#2563EB", width: 2 },
              symbol: "circle",
              symbolSize: 5,
              itemStyle: { color: "#2563EB" },
            },
          ],
        },
      ],
    };
  }, [scores]);

  return (
    <ReactECharts
      option={option}
      style={{ height, width: "100%" }}
      notMerge
      lazyUpdate
    />
  );
}
