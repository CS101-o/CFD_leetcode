import { useEffect, useState } from 'react'
import axios from 'axios'
import useStore from './store/useStore'
import ProblemLibrary from './components/ProblemLibrary'
import SessionView from './components/SessionView'
import Module01 from './components/module/Module01'
import HeroLanding from './components/HeroLanding'

const API_URL = import.meta.env.VITE_API_URL || '/api/v1'

export default function App() {
  const { view, setProblems, participantId, setParticipantId, resetSession } = useStore()
  const [briefAccepted, setBriefAccepted] = useState(true)
  // Research mode is the default starting page; Module01 is reached via the library card
  const [appMode, setAppMode] = useState('study')

  useEffect(() => {
    axios.get(`${API_URL}/flowsense/problems`)
      .then(res => setProblems(res.data.problems))
      .catch(err => console.error('Failed to load problems:', err))
  }, [])

  if (!briefAccepted) {
    return <HeroLanding onEnter={() => { setBriefAccepted(true); setAppMode('module') }} />
  }

  if (appMode === 'module') {
    return (
      <Module01
        onExit={() => {
          resetSession()
          setAppMode('study')
        }}
      />
    )
  }

  return (
    <div className="flex flex-col h-screen bg-zinc-950 text-zinc-100 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800 bg-zinc-950 shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-blue-500 rotate-45 rounded-sm" />
          <span className="text-[11px] font-bold tracking-widest">AIRFOILLEARNER</span>
          <span className="text-zinc-700 text-[11px]">·</span>
          <span className="text-[11px] text-zinc-500 tracking-widest hidden sm:inline">RESEARCH MODE</span>
        </div>
      </div>
      {view === 'library'
        ? <ProblemLibrary onGoToModule={() => setAppMode('module')} />
        : <SessionView />
      }
    </div>
  )
}
