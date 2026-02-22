import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function BalanceChart({ data }: { data: { date: string; balance: number }[] }) {
  if (!data.length) return <div className="rounded-xl border border-gray-800 bg-gray-900 p-8 text-gray-400">No transactions yet</div>;
  return <div className="h-72 rounded-xl border border-gray-800 bg-gray-900 p-3"><ResponsiveContainer><AreaChart data={data}><XAxis dataKey="date" /><YAxis /><Tooltip /><Area dataKey="balance" stroke="#34d399" fill="#34d39933" /></AreaChart></ResponsiveContainer></div>;
}
