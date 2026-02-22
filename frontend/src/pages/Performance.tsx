import { Bar, BarChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CLVDistribution } from "../components/performance/CLVDistribution";
import { HitRateCard } from "../components/performance/HitRateCard";
import { ROIChart } from "../components/performance/ROIChart";
import { usePerformanceSummary } from "../hooks/usePerformance";

export default function PerformancePage() {
  const { data } = usePerformanceSummary();
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-4">
        <HitRateCard title="Total Picks" value={`${data?.totalPicks ?? 0}`} />
        <HitRateCard title="Win Rate" value={`${(data?.winRate ?? 0).toFixed(1)}%`} />
        <HitRateCard title="ROI" value={`${(data?.roi ?? 0).toFixed(1)}%`} />
        <HitRateCard title="Average CLV" value={`${(data?.avgClv ?? 0).toFixed(2)}`} />
      </div>
      <ROIChart data={[]} />
      <div className="grid gap-4 md:grid-cols-2">
        <div className="h-64 rounded-xl border border-gray-800 bg-gray-900 p-3"><ResponsiveContainer><BarChart data={[]}><XAxis dataKey="name" /><YAxis /><Tooltip /><Bar dataKey="value" fill="#60a5fa" /></BarChart></ResponsiveContainer></div>
        <div className="h-64 rounded-xl border border-gray-800 bg-gray-900 p-3"><ResponsiveContainer><PieChart><Pie data={[]} dataKey="value" nameKey="name" fill="#34d399" /></PieChart></ResponsiveContainer></div>
      </div>
      <CLVDistribution />
    </div>
  );
}
