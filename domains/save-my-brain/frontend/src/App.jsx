import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { isLoggedIn, getUser } from "./auth";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Onboarding from "./pages/Onboarding";
import Dashboard from "./pages/Dashboard";
import Settings from "./pages/Settings";
import Privacy from "./pages/Privacy";

function ProtectedRoute({ children, requireOnboarding = true }) {
  if (!isLoggedIn()) return <Navigate to="/login" replace />;
  const user = getUser();
  if (requireOnboarding && !user?.onboarding_complete) {
    return <Navigate to="/onboarding" replace />;
  }
  return children;
}

function OnboardingGate({ children }) {
  // User must be logged in, but NOT yet onboarded
  if (!isLoggedIn()) return <Navigate to="/login" replace />;
  const user = getUser();
  if (user?.onboarding_complete) return <Navigate to="/dashboard" replace />;
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route
          path="/onboarding"
          element={
            <OnboardingGate>
              <Onboarding />
            </OnboardingGate>
          }
        />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <Settings />
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
