import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'

const dashboardLinks = [
  { to: '/', label: 'Overview', icon: '🏠', exact: true },
  { to: '/projects', label: 'Projects', icon: '📁' },
  { to: '/memory', label: 'Memory Records', icon: '🧠' },
  { to: '/workflow', label: 'Workflow', icon: '🔄' },
  { to: '/checks', label: 'Checks', icon: '✅' },
  { to: '/scheduler', label: 'Scheduler', icon: '⏰' },
]

const wikiLinks = [
  { to: '/wiki', label: 'All Topics', icon: '📚', exact: true },
  { to: '/wiki/graph', label: 'Knowledge Graph', icon: '🕸' },
  { to: '/wiki/lint', label: 'Lint Report', icon: '🔍' },
  { to: '/wiki/ingest', label: 'Ingest', icon: '📥' },
]

export default function RootLayout() {
  const location = useLocation()

  function isActive(to: string, exact?: boolean) {
    if (exact) return location.pathname === to
    if (to === '/wiki') return location.pathname === '/wiki'
    return location.pathname.startsWith(to)
  }

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 bg-white border-r border-gray-100 flex flex-col overflow-y-auto">
        {/* Logo */}
        <div className="px-4 py-5 border-b border-gray-100">
          <div className="text-lg font-bold text-brand-700">Agents Memory</div>
          <div className="text-xs text-gray-400 mt-0.5">Engineering Brain Console</div>
        </div>

        {/* Dashboard section */}
        <nav className="px-3 py-4 flex-1">
          <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-3 mb-2">Dashboard</div>
          {dashboardLinks.map(link => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.exact}
              className={({ isActive: active }) =>
                cn('nav-link', (active || isActive(link.to, link.exact)) && 'active')
              }
            >
              <span>{link.icon}</span>
              {link.label}
            </NavLink>
          ))}

          <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-3 mb-2 mt-5">Wiki</div>
          {wikiLinks.map(link => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.exact}
              className={({ isActive: active }) =>
                cn('nav-link', (active || isActive(link.to, link.exact)) && 'active')
              }
            >
              <span>{link.icon}</span>
              {link.label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-gray-100 text-xs text-gray-400">
          API: <span className="font-mono">:10100</span>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-6xl mx-auto px-6 py-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
