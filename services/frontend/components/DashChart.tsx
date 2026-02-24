"use client";

import { useRenderToolCall } from "@copilotkit/react-core";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const COLORS = [
  "#3b82f6", // blue-500
  "#10b981", // emerald-500
  "#f59e0b", // amber-500
  "#ef4444", // red-500
  "#8b5cf6", // violet-500
  "#ec4899", // pink-500
  "#06b6d4", // cyan-500
  "#f97316", // orange-500
];

/**
 * DashChart — Generative UI component for Dash Analytics.
 *
 * Registers a useRenderToolCall hook that matches "render_chart" ToolCall
 * events from the AG-UI adapter. When the Dash agent calls render_chart,
 * the backend emits ToolCallStart → ToolCallArgs → ToolCallEnd events,
 * and this component renders the appropriate Recharts chart inline in chat.
 *
 * Must be rendered inside <CopilotKit> context.
 */
export function DashChart() {
  useRenderToolCall({
    name: "render_chart",
    description: "Display an interactive chart",
    parameters: [
      {
        name: "chart_type",
        type: "string",
        description: "Chart type: line, bar, area, pie",
      },
      {
        name: "title",
        type: "string",
        description: "Chart title",
      },
      {
        name: "data",
        type: "string",
        description: "JSON array of data points",
      },
      {
        name: "x_key",
        type: "string",
        description: "Key for X axis",
      },
      {
        name: "y_keys",
        type: "string",
        description: "Comma-separated Y axis keys",
      },
    ],
    render: ({ status, args }) => {
      // Parse data from JSON string
      let chartData: Record<string, unknown>[] | null = null;
      try {
        if (args?.data) {
          chartData = JSON.parse(args.data as string);
        }
      } catch {
        // data might not be valid JSON yet during streaming
      }

      // Loading state
      if (status === "inProgress" && !chartData) {
        return (
          <div className="flex items-center gap-2 p-4 text-sm text-slate-500">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
            Generating chart...
          </div>
        );
      }

      if (!chartData || chartData.length === 0) {
        return (
          <div className="p-4 text-sm text-slate-400">No chart data available</div>
        );
      }

      const chartType = (args?.chart_type as string) || "bar";
      const title = (args?.title as string) || "";
      const xKey = (args?.x_key as string) || "";
      const yKeys = ((args?.y_keys as string) || "")
        .split(",")
        .map((k: string) => k.trim())
        .filter(Boolean);

      return (
        <div className="my-3 rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
          {title && (
            <h4 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">
              {title}
            </h4>
          )}
          <ResponsiveContainer width="100%" height={320}>
            {renderChart(chartType, chartData, xKey, yKeys)}
          </ResponsiveContainer>
        </div>
      );
    },
  });

  // This component doesn't render any visible UI itself —
  // it only registers the useRenderToolCall hook.
  return null;
}

function renderChart(
  chartType: string,
  data: Record<string, unknown>[],
  xKey: string,
  yKeys: string[],
) {
  switch (chartType) {
    case "line":
      return (
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend />
          {yKeys.map((key, i) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={2}
              dot={{ r: 3 }}
            />
          ))}
        </LineChart>
      );

    case "area":
      return (
        <AreaChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend />
          {yKeys.map((key, i) => (
            <Area
              key={key}
              type="monotone"
              dataKey={key}
              stroke={COLORS[i % COLORS.length]}
              fill={COLORS[i % COLORS.length]}
              fillOpacity={0.2}
            />
          ))}
        </AreaChart>
      );

    case "pie":
      return (
        <PieChart>
          <Tooltip />
          <Legend />
          <Pie
            data={data}
            dataKey={yKeys[0] || "value"}
            nameKey={xKey}
            cx="50%"
            cy="50%"
            outerRadius={120}
            label={({ name, percent }) =>
              `${name ?? ""}: ${((percent ?? 0) * 100).toFixed(0)}%`
            }
          >
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
        </PieChart>
      );

    case "bar":
    default:
      return (
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend />
          {yKeys.map((key, i) => (
            <Bar
              key={key}
              dataKey={key}
              fill={COLORS[i % COLORS.length]}
              radius={[4, 4, 0, 0]}
            />
          ))}
        </BarChart>
      );
  }
}
