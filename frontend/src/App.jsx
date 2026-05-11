import { useEffect } from 'react'
import axios from 'axios'
import useStore from './store/useStore'
import ProblemLibrary from './components/ProblemLibrary'
import SessionView from './components/SessionView'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export default function App() {
  const { view, setProblems } = useStore()

  useEffect(() => {
    axios.get(`${API_URL}/flowsense/problems`)
      .then(res => setProblems(res.data.problems))
      .catch(err => console.error('Failed to load problems:', err))
  }, [])

  return (
    <div className="flex flex-col h-screen bg-zinc-950 text-zinc-100 overflow-hidden">
      {view === 'library' ? <ProblemLibrary /> : <SessionView />}
    </div>
  )
}
