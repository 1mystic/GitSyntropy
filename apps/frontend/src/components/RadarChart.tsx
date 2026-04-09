import {
  Radar,
  RadarChart as RechartsRadarChart,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

const DIMENSION_LABELS: Record<string, string> = {
  varna_alignment: "Varna",
  vashya_influence: "Vashya",
  tara_resilience: "Tara",
  yoni_workstyle: "Yoni",
  graha_maitri_cognition: "Graha",
  gana_temperament: "Gana",
  bhakoot_strategy: "Bhakoot",
  nadi_chronotype_sync: "Nadi",
};

const DIMENSION_WEIGHTS: Record<string, number> = {
  varna_alignment: 1,
  vashya_influence: 2,
  tara_resilience: 3,
  yoni_workstyle: 4,
  graha_maitri_cognition: 5,
  gana_temperament: 6,
  bhakoot_strategy: 7,
  nadi_chronotype_sync: 8,
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
