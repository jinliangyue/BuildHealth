import { BrowserRouter, Routes, Route } from "react-router-dom";
import Sidebar from "./components/layout/Sidebar";
import SimulatedBanner from "./components/layout/SimulatedBanner";
import Dashboard from "./pages/Dashboard";
import Buildings from "./pages/Buildings";
import BuildingDetail from "./pages/BuildingDetail";
import Monitoring from "./pages/Monitoring";
import RiskHealth from "./pages/RiskHealth";
import RetrofitDecision from "./pages/RetrofitDecision";
import AIAssistant from "./pages/AIAssistant";
import DataSettings from "./pages/DataSettings";

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-full bg-engineering-bg">
        <Sidebar />
        <main className="flex-1 overflow-auto p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/buildings" element={<Buildings />} />
            <Route path="/buildings/:id" element={<BuildingDetail />} />
            <Route path="/monitoring" element={<Monitoring />} />
            <Route path="/risk-health" element={<RiskHealth />} />
            <Route path="/retrofit" element={<RetrofitDecision />} />
            <Route path="/ai-assistant" element={<AIAssistant />} />
            <Route path="/data" element={<DataSettings />} />
            <Route path="/settings" element={<DataSettings />} />
          </Routes>
        </main>
        <SimulatedBanner />
      </div>
    </BrowserRouter>
  );
}
