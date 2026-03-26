import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import {
  FailureInsightsPage,
  PolicyManagerPage,
  ReliabilityCardsPage,
  RunDetailPage,
  RunListPage,
} from './pages'

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<RunListPage />} />
        <Route path="/runs/:run_id" element={<RunDetailPage />} />
        <Route path="/insights" element={<FailureInsightsPage />} />
        <Route path="/policies" element={<PolicyManagerPage />} />
        <Route path="/reliability" element={<ReliabilityCardsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
