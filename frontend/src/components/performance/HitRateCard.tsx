export function HitRateCard({ title, value }: { title: string; value: string }) {
  return <div className="rounded-xl border border-gray-800 bg-gray-900 p-4"><div className="text-sm text-gray-400">{title}</div><div className="mt-1 text-2xl font-semibold">{value}</div></div>;
}
