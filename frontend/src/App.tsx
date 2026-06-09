import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { PracticePage, PracticeChatPage, PracticeReviewPage, ReportPage } from './pages/Practice'
import {
  ScenarioManagementPage,
  AdminDashboardPage,
  AuditManagementPage,
  UserManagementPage,
  DataExportPage,
  SystemSettingsPage
} from './pages/Admin'
import { LoginPage, RegisterPage } from './pages/Auth'
import { ProfilePage, HistoryPage, SettingsPage } from './pages/User'
import { DashboardPage } from './pages/Dashboard'
import { KnowledgeBasePage } from './pages/Knowledge'
import { BriefListPage, BriefDetailPage } from './pages/Briefs'
import SpinPreparationPage from './pages/Spin/SpinPreparationPage'
import { AuthProvider } from './contexts/AuthContext'
import ProtectedRoute from './components/common/ProtectedRoute'
import AppLayout from './components/common/AppLayout'

/**
 * Wrapper that every protected page goes through.
 * It (a) requires auth, (b) renders the global Navigation header so
 * users can move between pages without typing URLs.
 */
const ProtectedShell = () => (
  <ProtectedRoute>
    <AppLayout>
      <Outlet />
    </AppLayout>
  </ProtectedRoute>
)

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public routes — no global nav */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Protected routes — every one goes through ProtectedShell so
              the global Navigation + AppLayout is always present. */}
          <Route element={<ProtectedShell />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/spin/preparation" element={<SpinPreparationPage />} />
            <Route path="/practice" element={<PracticePage />} />
            <Route path="/practice/chat" element={<PracticeChatPage />} />
            <Route path="/practice/review" element={<PracticeReviewPage />} />
            <Route path="/practice/report/:session_id" element={<ReportPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/knowledge" element={<KnowledgeBasePage />} />
            <Route path="/briefs" element={<BriefListPage />} />
            <Route path="/briefs/:id" element={<BriefDetailPage />} />
          </Route>

          {/* Admin routes */}
          <Route path="/admin" element={
            <ProtectedRoute requiredRole="admin">
              <AppLayout>
                <AdminDashboardPage />
              </AppLayout>
            </ProtectedRoute>
          } />
          <Route path="/admin/dashboard" element={
            <ProtectedRoute requiredRole="admin">
              <AppLayout>
                <AdminDashboardPage />
              </AppLayout>
            </ProtectedRoute>
          } />
          <Route path="/admin/scenarios" element={
            <ProtectedRoute requiredRole="admin">
              <AppLayout>
                <ScenarioManagementPage />
              </AppLayout>
            </ProtectedRoute>
          } />
          <Route path="/admin/audits" element={
            <ProtectedRoute requiredRole="admin">
              <AppLayout>
                <AuditManagementPage />
              </AppLayout>
            </ProtectedRoute>
          } />
          <Route path="/admin/users" element={
            <ProtectedRoute requiredRole="admin">
              <AppLayout>
                <UserManagementPage />
              </AppLayout>
            </ProtectedRoute>
          } />
          <Route path="/admin/export" element={
            <ProtectedRoute requiredRole="admin">
              <AppLayout>
                <DataExportPage />
              </AppLayout>
            </ProtectedRoute>
          } />
          <Route path="/admin/settings" element={
            <ProtectedRoute requiredRole="admin">
              <AppLayout>
                <SystemSettingsPage />
              </AppLayout>
            </ProtectedRoute>
          } />

          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
