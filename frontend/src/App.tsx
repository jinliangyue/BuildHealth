import { BrowserRouter, Routes, Route } from "react-router-dom";
import Sidebar from "./components/layout/Sidebar";
import Dashboard from "./pages/Dashboard";
import Buildings from "./pages/Buildings";
import BuildingDetail from "./pages/BuildingDetail";
import Monitoring from "./pages/Monitoring";
import RiskHealth from "./pages/RiskHealth";
import Settings from "./pages/Settings";

/**
 * BuildHealth Frontend App
 * Phase 0 Skeleton - 占位页面 + 路由骨架
 */
function App() {
  return (
    <BrowserRouter>
      <div className="flex h-full">
        <Sidebar />
        <main className="flex-1 overflow-auto p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/buildings" element={<Buildings />} />
            <Route path="/buildings/:id" element={<BuildingDetail />} />
            <Route path="/monitoring" element={<Monitoring />} />
            <Route path="/risk-health" element={<RiskHealth />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
