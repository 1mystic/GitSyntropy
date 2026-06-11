import {
  Radar,
  RadarChart as RechartsRadarChart,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

const DIMENSION_LABELS: Record<string, string> = {
  innovation_drive: "Innovation Drive",
  leadership_orientation: "Leadership",
  team_resilience: "Team Resilience",
  work_style: "Work Style",
  decision_style: "Decision Style",
  risk_tolerance: "Risk Tolerance",
  stress_response: "Stress Response",
  chronotype_sync: "Chronotype Sync",
};

const DIMENSION_WEIGHTS: Record<string, number> = {
  innovation_drive: 1,
  leadership_orientation: 2,
  team_resilience: 3,
  work_style: 4,
  decision_style: 5,
  risk_tolerance: 6,
  stress_response: 7,
  chronotype_sync: 8,
};

interface RadarChartProps {
  dimensionScores: Record<string, number>;
}

export function RadarChart({ dimensionScores }: RadarChartProps) {
  const data = Object.keys(DIMENSION_LABELS).map((key) => {
    const score = dimensionScores[key] ?? 0;
    const weight = DIMENSION_WEIGHTS[key] ?? 1;
    return {
      dimension: DIMENSION_LABELS[key],
      value: Math.round((score / weight) * 100),
      fullMark: 100,
    };
  });

  return (
    <ResponsiveContainer width="100%" height={260}>
      <RechartsRadarChart cx="50%" cy="50%" outerRadius="75%" data={data}>
        <PolarGrid stroke="rgba(255,255,255,0.08)" />
        <PolarAngleAxis
          dataKey="dimension"
          tick={{ fill: "#9ca3af", fontSize: 11, fontFamily: "monospace" }}
        />
        <Radar
          name="Alignment Score"
          dataKey="value"
          stroke="#7c3aed"
          fill="#7c3aed"
          fillOpacity={0.25}
          strokeWidth={2}
          dot={{ fill: "#ccff00", r: 3, strokeWidth: 0 }}
        />
        <Tooltip
          contentStyle={{
            background: "#0f0f1a",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 4,
            fontSize: 12,
          }}
          itemStyle={{ color: "#ccff00" }}
          formatter={(value) => [`${String(value)}%`, "Score"]}
        />
      </RechartsRadarChart>
    </ResponsiveContainer>
  );
}
