export function TopBar({ title, updatedAt }: { title: string; updatedAt?: number }) {
  return (
    <header className="flex items-center justify-between border-b border-gray-800 bg-gray-950 px-6 py-4">
      <h1 className="text-xl text-gray-100">{title}</h1>
      <div className="text-xs text-gray-400">Auto-refresh 60s · Last updated {updatedAt ? new Date(updatedAt).toLocaleTimeString() : "--"}</div>
    </header>
  );
}
