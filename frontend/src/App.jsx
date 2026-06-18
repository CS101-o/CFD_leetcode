import { useEffect, useState } from 'react'
import axios from 'axios'
import useStore from './store/useStore'
import ProblemLibrary from './components/ProblemLibrary'
import SessionView from './components/SessionView'

const API_URL = import.meta.env.VITE_API_URL || '/api/v1'

export default function App() {
  const { view, setProblems, participantId, setParticipantId } = useStore()
  const [draft, setDraft] = useState('')

  useEffect(() => {
    axios.get(`${API_URL}/flowsense/problems`)
      .then(res => setProblems(res.data.problems))
      .catch(err => console.error('Failed to load problems:', err))
  }, [])

  if (!participantId) {
    return (
      <div className="flex h-screen items-center justify-center bg-zinc-950">
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 w-80 flex flex-col gap-4">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-5 h-5 bg-blue-500 rotate-45 rounded-sm" />
            <span className="text-xs font-bold tracking-widest text-zinc-100">AIRFOILLEARNER</span>
          </div>
          <p className="text-xs text-zinc-400 leading-relaxed">
            Enter your participant ID to begin the session. This is used only to label your activity log.
          </p>
          <input
            autoFocus
            type="text"
            value={draft}
            onChange={e => setDraft(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && draft.trim()) setParticipantId(draft.trim()) }}
            placeholder="e.g. P01"
            className="bg-zinc-800 border border-zinc-700 text-zinc-100 text-sm rounded-lg px-3 py-2 outline-none focus:border-blue-500 placeholder-zinc-600"
          />
          <button
            disabled={!draft.trim()}
            onClick={() => setParticipantId(draft.trim())}
            className="bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-white text-xs font-bold tracking-widest py-2 rounded-lg transition-colors"
          >
            START SESSION →
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen bg-zinc-950 text-zinc-100 overflow-hidden">
      {view === 'library' ? <ProblemLibrary /> : <SessionView />}
    </div>
  )
}
