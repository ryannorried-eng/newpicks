import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/layout/AppLayout";
import BankrollPage from "./pages/Bankroll";
import Dashboard from "./pages/Dashboard";
import OddsPage from "./pages/Odds";
import ParlaysPage from "./pages/Parlays";
import PerformancePage from "./pages/Performance";
import PicksPage from "./pages/Picks";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/picks" element={<PicksPage />} />
        <Route path="/parlays" element={<ParlaysPage />} />
        <Route path="/odds" element={<OddsPage />} />
        <Route path="/performance" element={<PerformancePage />} />
        <Route path="/bankroll" element={<BankrollPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
