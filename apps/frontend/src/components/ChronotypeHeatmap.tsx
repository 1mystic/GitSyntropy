import { useEffect, useRef } from "react";
import * as d3 from "d3";

type Chronotype = "owl" | "lark" | "balanced";

interface ChronotypeHeatmapProps {
  chronotype: Chronotype;
  commitCount?: number;
}

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const HOUR_BLOCKS = ["00–04", "04–08", "08–12", "12–16", "16–20", "20–24"];

function generateHeatmapData(chronotype: Chronotype) {
  const data: { day: string; block: string; value: number }[] = [];
  const rng = (seed: number) => ((seed * 1664525 + 1013904223) >>> 0) / 2 ** 32;

  for (let di = 0; di < DAYS.length; di++) {
    const day = DAYS[di];
    const isWeekend = di >= 5;
    const weekendFactor = isWeekend ? 0.45 : 1.0;

    for (let bi = 0; bi < HOUR_BLOCKS.length; bi++) {
      const startHour = bi * 4;
      const seed = di * 100 + bi;
      const noise = rng(seed) * 0.2 - 0.1;
      let base = 0;

      if (chronotype === "owl") {
        // Peak: 20–24 (block 5) and 00–04 (block 0)
        if (bi === 5 || bi === 0) base = 0.85;
        else if (bi === 4) base = 0.55;
        else if (bi === 1) base = 0.35;
        else base = 0.12;
      } else if (chronotype === "lark") {
        // Peak: 04–08 (block 1) and 08–12 (block 2)
        if (bi === 1 || bi === 2) base = 0.85;
        else if (bi === 3) base = 0.5;
        else if (bi === 0) base = 0.25;
        else base = 0.08;
      } else {
        // balanced: peak 08–16 (blocks 2, 3)
        if (bi === 2 || bi === 3) base = 0.82;
        else if (bi === 1 || bi === 4) base = 0.42;
        else base = 0.1;
      }

      data.push({
        day,
        block: HOUR_BLOCKS[bi],
        value: Math.min(1, Math.max(0, (base + noise) * weekendFactor)),
      });
    }
  }
  return data;
}

export function ChronotypeHeatmap({ chronotype, commitCount }: ChronotypeHeatmapProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!svgRef.current || !containerRef.current) return;

    const data = generateHeatmapData(chronotype);
    const margin = { top: 8, right: 12, bottom: 28, left: 46 };
    const containerWidth = containerRef.current.clientWidth || 360;
    const height = 160;
    const innerW = containerWidth - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    svg.attr("width", containerWidth).attr("height", height);

    const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

    const xScale = d3.scaleBand().domain(DAYS).range([0, innerW]).padding(0.1);
    const yScale = d3.scaleBand().domain(HOUR_BLOCKS).range([0, innerH]).padding(0.1);
    const colorScale = d3
      .scaleSequential()
      .domain([0, 1])
      .interpolator(d3.interpolate("#1a1233", "#ccff00"));

    // Cells
    g.selectAll("rect.cell")
      .data(data)
      .enter()
      .append("rect")
      .attr("class", "cell")
      .attr("x", (d) => xScale(d.day) ?? 0)
      .attr("y", (d) => yScale(d.block) ?? 0)
      .attr("width", xScale.bandwidth())
      .attr("height", yScale.bandwidth())
      .attr("rx", 2)
      .attr("fill", (d) => colorScale(d.value))
      .attr("opacity", 0.92);

    // X axis
    g.append("g")
      .attr("transform", `translate(0,${innerH + 4})`)
      .call(d3.axisBottom(xScale).tickSize(0))
      .call((ax) => ax.select(".domain").remove())
      .selectAll("text")
      .style("fill", "#6b7280")
      .style("font-size", "10px");

    // Y axis
    g.append("g")
      .attr("transform", "translate(-4,0)")
      .call(d3.axisLeft(yScale).tickSize(0))
      .call((ax) => ax.select(".domain").remove())
      .selectAll("text")
      .style("fill", "#6b7280")
      .style("font-size", "10px");
  }, [chronotype, commitCount]);

  return (
    <div ref={containerRef} className="w-full">
      <svg ref={svgRef} className="w-full overflow-visible" />
    </div>
  );
}
