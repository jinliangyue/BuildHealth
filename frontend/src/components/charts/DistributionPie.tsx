/**
 * 风险分布饼图
 */
import { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import {
  RISK_LEVEL_COLORS,
  RISK_LEVEL_LABELS,
  type RiskDistribution,
} from "../../types/api";
import "./echarts";

interface Props {
  distribution: RiskDistribution;
  height?: number;
}

export default function DistributionPie({ distribution, height = 240 }: Props) {
  const option: EChartsOption = useMemo(() => {
    const data = (Object.keys(distribution) as Array<keyof RiskDistribution>).map(
      (k) => ({
        name: RISK_LEVEL_LABELS[k],
        value: distribution[k],
        itemStyle: { color: RISK_LEVEL_COLORS[k] },
      }),
    );
    return {
      animation: false,
      tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
      legend: { bottom: 0, textStyle: { fontSize: 11, color: "#475569" } },
      series: [
        {
          type: "pie",
          radius: ["45%", "70%"],
          center: ["50%", "45%"],
          avoidLabelOverlap: true,
          itemStyle: { borderColor: "#fff", borderWidth: 2 },
          label: { show: false },
          data,
        },
      ],
    };
  }, [distribution]);

  return (
    <ReactECharts
      option={option}
      style={{ height, width: "100%" }}
      notMerge
      lazyUpdate
    />
  );
}
