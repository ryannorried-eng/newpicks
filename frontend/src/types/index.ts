export interface Pick {
  id: number;
  game_id: number;
  sport_key: string;
  home_team: string;
  away_team: string;
  commence_time: string;
  market: string;
  side: string;
  line: number | null;
  odds_american: number;
  best_book: string;
  fair_prob: number;
  prob_source: string;
  implied_prob: number;
  ev_pct: number;
  composite_score: number;
  confidence_tier: "high" | "medium" | "low";
  signals: SignalBreakdown;
  data_quality: DataQuality;
  suggested_kelly_fraction: number;
  outcome: string | null;
  market_clv: number | null;
  book_clv: number | null;
  created_at: string;
}

export interface SignalBreakdown {
  ev_positive: number;
  ev_magnitude: number;
  steam_move: number;
  reverse_line_movement: number;
  best_line_available: number;
  consensus_deviation: number;
  closing_line_trend: number;
  data_quality_score: number;
  composite: number;
}

export interface DataQuality {
  books_covered: number;
  snapshot_freshness_minutes: number;
  sharp_books_present: boolean;
  line_dispersion: number;
  market_completeness: number;
}

export interface ParlayLeg {
  id: number;
  pick_id: number;
  leg_order: number;
  result: string | null;
  pick: Pick;
}

export interface Parlay {
  id: number;
  risk_level: "conservative" | "moderate" | "aggressive";
  num_legs: number;
  combined_odds_american: number;
  combined_odds_decimal: number;
  combined_ev_pct: number;
  combined_fair_prob: number;
  correlation_score: number;
  suggested_kelly_fraction: number;
  outcome: string | null;
  profit_loss: number | null;
  created_at: string;
  legs: ParlayLeg[];
}

export interface OddsSnapshot {
  game_id: number;
  home_team: string;
  away_team: string;
  sport_key: string;
  bookmaker: string;
  market: string;
  side: string;
  odds: number;
  line: number | null;
  snapshot_time: string;
}

export interface PollStatus {
  mode: string;
  active_sports: string[];
  quota_remaining: number | null;
  next_poll_time: string;
}

export interface PerformanceSummary {
  totalPicks: number;
  winRate: number;
  roi: number;
  avgClv: number;
}

export interface BankrollSummary {
  balance: number;
  history: { date: string; balance: number }[];
}
