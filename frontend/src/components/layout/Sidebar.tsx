import { BarChart3, Layers, LayoutDashboard, Target, TrendingUp, Wallet, Crosshair, Circle } from "lucide-react";
import { NavLink } from "react-router-dom";
import type { PollStatus } from "../../types";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/picks", label: "Picks", icon: Target },
  { to: "/parlays", label: "Parlays", icon: Layers },
  { to: "/odds", label: "Odds", icon: TrendingUp },
  { to: "/performance", label: "Performance", icon: BarChart3 },
  { to: "/bankroll", label: "Bankroll", icon: Wallet },
];

export function Sidebar({ pollStatus }: { pollStatus?: PollStatus }) {
  return (
    <aside className="w-full border-r border-gray-800 bg-gray-950 p-4 md:w-60">
      <div className="mb-6 flex items-center gap-2 text-gray-100"><Crosshair className="h-5 w-5 text-emerald-400" />SharpPicks</div>
      <nav className="space-y-1">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} className={({ isActive }) => `flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${isActive ? "bg-gray-800 text-emerald-400" : "text-gray-300 hover:bg-gray-900"}`}>
            <Icon className="h-4 w-4" /> {label}
          </NavLink>
        ))}
      </nav>
      <div className="mt-8 rounded-lg border border-gray-800 bg-gray-900 p-3 text-xs text-gray-400">
        <div className="flex items-center gap-2 text-gray-200"><Circle className={`h-3 w-3 ${pollStatus?.mode === "off-hours" ? "text-gray-500" : "text-emerald-400"}`} />{pollStatus?.mode ?? "unknown"}</div>
        <div className="mt-1">Quota: {pollStatus?.quota_remaining ?? "N/A"}</div>
      </div>
    </aside>
  );
}
