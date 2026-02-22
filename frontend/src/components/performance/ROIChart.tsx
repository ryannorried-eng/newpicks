import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function ROIChart({ data }: { data: { date: string; roi: number }[] }) {
  if (!data.length) return <div className="rounded-xl border border-gray-800 bg-gray-900 p-8 text-gray-400">Awaiting settled picks</div>;
  return <div className="h-72 rounded-xl border border-gray-800 bg-gray-900 p-3"><ResponsiveContainer><LineChart data={data}><XAxis dataKey="date" /><YAxis /><Tooltip /><Line dataKey="roi" stroke="#34d399" /></LineChart></ResponsiveContainer></div>;
}
