import { Outlet } from 'react-router-dom'
import Sidebar from './components/Layout/Sidebar'
import Header from './components/Layout/Header'
import { useConfig } from './hooks/useConfig'
import './App.css'

export default function App() {
  const config = useConfig()

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-main">
        <Header />
        <main className="app-content">
          <Outlet context={config} />
        </main>
      </div>
    </div>
  )
}
