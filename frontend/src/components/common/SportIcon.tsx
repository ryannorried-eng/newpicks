import { Activity, CircleDot, Goal, Trophy } from "lucide-react";

export function SportIcon({ sport }: { sport: string }) {
  if (sport.includes("basketball") || sport.includes("nba") || sport.includes("ncaab")) return <CircleDot className="h-4 w-4" />;
  if (sport.includes("football") || sport.includes("nfl")) return <Goal className="h-4 w-4" />;
  if (sport.includes("baseball") || sport.includes("mlb")) return <Activity className="h-4 w-4" />;
  return <Trophy className="h-4 w-4" />;
}
