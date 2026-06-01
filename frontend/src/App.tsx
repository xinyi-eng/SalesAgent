import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
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
import SpinPreparationPage from './pages/Spin/SpinPreparationPage'
import { AuthProvider } from './contexts/AuthContext'
import ProtectedRoute from './components/common/ProtectedRoute'

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Protected routes */}
          <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="/spin/preparation" element={<ProtectedRoute><SpinPreparationPage /></ProtectedRoute>} />
          <Route path="/practice" element={<ProtectedRoute><PracticePage /></ProtectedRoute>} />
          <Route path="/practice/chat" element={<ProtectedRoute><PracticeChatPage /></ProtectedRoute>} />
          <Route path="/practice/review" element={<ProtectedRoute><PracticeReviewPage /></ProtectedRoute>} />
          <Route path="/practice/report/:session_id" element={<ProtectedRoute><ReportPage /></ProtectedRoute>} />
          <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
          <Route path="/history" element={<ProtectedRoute><HistoryPage /></ProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
          <Route path="/knowledge" element={<ProtectedRoute><KnowledgeBasePage /></ProtectedRoute>} />

          {/* Admin routes */}
          <Route path="/admin" element={<ProtectedRoute requiredRole="admin"><AdminDashboardPage /></ProtectedRoute>} />
          <Route path="/admin/dashboard" element={<ProtectedRoute requiredRole="admin"><AdminDashboardPage /></ProtectedRoute>} />
          <Route path="/admin/scenarios" element={<ProtectedRoute requiredRole="admin"><ScenarioManagementPage /></ProtectedRoute>} />
          <Route path="/admin/audits" element={<ProtectedRoute requiredRole="admin"><AuditManagementPage /></ProtectedRoute>} />
          <Route path="/admin/users" element={<ProtectedRoute requiredRole="admin"><UserManagementPage /></ProtectedRoute>} />
          <Route path="/admin/export" element={<ProtectedRoute requiredRole="admin"><DataExportPage /></ProtectedRoute>} />
          <Route path="/admin/settings" element={<ProtectedRoute requiredRole="admin"><SystemSettingsPage /></ProtectedRoute>} />

          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App