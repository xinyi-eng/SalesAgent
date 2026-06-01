/**
 * AppLayout - Main layout with Navigation
 */
import { ReactNode } from 'react'
import Navigation from '../common/Navigation'

interface AppLayoutProps {
  children: ReactNode
}

const AppLayout = ({ children }: AppLayoutProps) => {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      <main>{children}</main>
    </div>
  )
}

export default AppLayout