import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import ProtectedRoute from './components/common/ProtectedRoute'
import AppLayout from './components/common/AppLayout'

const LoginPage = lazy(() => import('./pages/Auth/LoginPage'))
const RegisterPage = lazy(() => import('./pages/Auth/RegisterPage'))
const DashboardPage = lazy(() => import('./pages/Dashboard/DashboardPage'))
const SpinPreparationPage = lazy(() => import('./pages/Spin/SpinPreparationPage'))
const PracticePage = lazy(() => import('./pages/Practice/PracticePage'))
const PracticeChatPage = lazy(() => import('./pages/Practice/PracticeChatPage'))
const PracticeReviewPage = lazy(() => import('./pages/Practice/PracticeReviewPage'))
const ReportPage = lazy(() => import('./pages/Practice/ReportPage'))
const ProfilePage = lazy(() => import('./pages/User/ProfilePage'))
const HistoryPage = lazy(() => import('./pages/User/HistoryPage'))
const SettingsPage = lazy(() => import('./pages/User/SettingsPage'))
const KnowledgeBasePage = lazy(() => import('./pages/Knowledge/KnowledgeBasePage'))
const BriefListPage = lazy(() => import('./pages/Briefs/BriefListPage'))
const BriefDetailPage = lazy(() => import('./pages/Briefs/BriefDetailPage'))
const ScenarioManagementPage = lazy(() => import('./pages/Admin/ScenarioManagementPage'))
const AdminDashboardPage = lazy(() => import('./pages/Admin/AdminDashboardPage'))
const AuditManagementPage = lazy(() => import('./pages/Admin/AuditManagementPage'))
const UserManagementPage = lazy(() => import('./pages/Admin/UserManagementPage'))
const DataExportPage = lazy(() => import('./pages/Admin/DataExportPage'))
const SystemSettingsPage = lazy(() => import('./pages/Admin/SystemSettingsPage'))

const PageLoading = () => (
  <div className="min-h-screen flex items-center justify-center" role="status" aria-label="页面加载中">
    <div className="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin" />
  </div>
)

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
        <Suspense fallback={<PageLoading />}>
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
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
