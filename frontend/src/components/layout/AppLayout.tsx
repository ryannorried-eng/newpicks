import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { usePollStatus } from "../../hooks/useOdds";

const titleMap: Record<string, string> = {
  "/": "Dashboard",
  "/picks": "Picks",
  "/parlays": "Parlays",
  "/odds": "Odds",
  "/performance": "Performance",
  "/bankroll": "Bankroll",
};

export function AppLayout() {
  const location = useLocation();
  const { data: pollStatus, dataUpdatedAt } = usePollStatus();
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 md:flex">
      <Sidebar pollStatus={pollStatus} />
      <div className="flex-1">
        <TopBar title={titleMap[location.pathname] ?? "SharpPicks"} updatedAt={dataUpdatedAt} />
        <main className="p-6"><Outlet /></main>
      </div>
    </div>
  );
}
