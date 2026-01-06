import { Routes, Route, NavLink } from 'react-router-dom'
import { useState } from 'react'
import KnowledgeGraphPage from './pages/KnowledgeGraph'
import VaultPage from './pages/Vault'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Navigation component
function Navigation() {
  return (
    <nav className="fixed top-0 left-0 h-full w-16 bg-slate-900 border-r border-slate-800 flex flex-col items-center py-4 z-50">
      {/* Logo */}
      <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center mb-8">
        <svg
          className="w-6 h-6 text-white"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
          />
        </svg>
      </div>

      {/* Nav Links */}
      <div className="flex flex-col gap-2">
        <NavItem to="/" icon={<HomeIcon />} title="Home" />
        <NavItem to="/vault" icon={<VaultIcon />} title="Vault" />
        <NavItem to="/graph" icon={<GraphIcon />} title="Knowledge Graph" />
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Settings */}
      <NavItem to="/settings" icon={<SettingsIcon />} title="Settings" />
    </nav>
  )
}

function NavItem({ to, icon, title }) {
  return (
    <NavLink
      to={to}
      title={title}
      className={({ isActive }) =>
        `w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-200 ${
          isActive
            ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
            : 'text-slate-400 hover:text-white hover:bg-slate-800'
        }`
      }
    >
      {icon}
    </NavLink>
  )
}

// Icons
function HomeIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
      />
    </svg>
  )
}

function VaultIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"
      />
    </svg>
  )
}

function GraphIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      {/* Network/graph nodes */}
      <circle cx="5" cy="6" r="2" strokeWidth={2} />
      <circle cx="12" cy="4" r="2" strokeWidth={2} />
      <circle cx="19" cy="8" r="2" strokeWidth={2} />
      <circle cx="6" cy="18" r="2" strokeWidth={2} />
      <circle cx="18" cy="18" r="2" strokeWidth={2} />
      <circle cx="12" cy="12" r="2.5" strokeWidth={2} />
      {/* Connections */}
      <path strokeLinecap="round" strokeWidth={1.5} d="M7 7l3.5 3.5M14.5 10l3-1M9.5 12.5l-2 4M14.5 13.5l2 3M12 14.5v0" />
    </svg>
  )
}

function SettingsIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
      />
    </svg>
  )
}

// Home page
function HomePage() {
  const [text, setText] = useState('')
  const [status, setStatus] = useState(null)

  const handleCapture = async () => {
    if (!text.trim()) return

    try {
      const response = await fetch(`${API_URL}/api/capture/text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })

      if (response.ok) {
        setStatus({ type: 'success', message: 'Text captured successfully!' })
        setText('')
      } else {
        setStatus({ type: 'error', message: 'Failed to capture text' })
      }
    } catch (error) {
      setStatus({ type: 'error', message: 'Connection error' })
    }

    setTimeout(() => setStatus(null), 3000)
  }

  return (
    <div className="min-h-screen bg-slate-950 p-8">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="mb-12">
          <h1 className="text-4xl font-bold text-white mb-3">Second Brain</h1>
          <p className="text-slate-400 text-lg">
            Your personal knowledge management system
          </p>
        </div>

        {/* Quick Capture */}
        <div className="bg-slate-900 rounded-2xl p-6 border border-slate-800 mb-8">
          <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
            <span className="w-8 h-8 bg-indigo-600/20 rounded-lg flex items-center justify-center">
              ⚡
            </span>
            Quick Capture
          </h2>

          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Capture a thought, idea, or note..."
            className="w-full h-32 bg-slate-800 border border-slate-700 rounded-lg p-4 text-white placeholder-slate-500 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />

          <div className="flex items-center justify-between mt-4">
            {status && (
              <p
                className={`text-sm ${
                  status.type === 'success' ? 'text-emerald-400' : 'text-red-400'
                }`}
              >
                {status.message}
              </p>
            )}
            <button
              onClick={handleCapture}
              disabled={!text.trim()}
              className="ml-auto px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium"
            >
              Capture
            </button>
          </div>
        </div>

        {/* Quick Links */}
        <div className="grid grid-cols-2 gap-4">
          <QuickLink
            to="/graph"
            icon="🕸️"
            title="Knowledge Graph"
            description="Visualize your knowledge connections"
          />
          <QuickLink
            to="/vault"
            icon="📚"
            title="Vault"
            description="Browse your notes and content"
          />
        </div>
      </div>
    </div>
  )
}

function QuickLink({ to, icon, title, description }) {
  return (
    <NavLink
      to={to}
      className="bg-slate-900 hover:bg-slate-800 rounded-xl p-5 border border-slate-800 hover:border-slate-700 transition-all duration-200 group"
    >
      <span className="text-3xl mb-3 block">{icon}</span>
      <h3 className="text-lg font-semibold text-white group-hover:text-indigo-400 transition-colors">
        {title}
      </h3>
      <p className="text-sm text-slate-400 mt-1">{description}</p>
    </NavLink>
  )
}

// Settings page placeholder
function SettingsPage() {
  return (
    <div className="min-h-screen bg-slate-950 p-8">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-4xl font-bold text-white mb-3">Settings</h1>
        <p className="text-slate-400">Settings page coming soon...</p>
      </div>
    </div>
  )
}

function App() {
  return (
    <div className="flex">
      <Navigation />
      <main className="flex-1 ml-16">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/graph" element={<KnowledgeGraphPage />} />
          <Route path="/vault" element={<VaultPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
