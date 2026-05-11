import { useEffect, useRef, useState } from 'react'
import axios from 'axios'
import useStore from '../store/useStore'
import LeftPanel from './LeftPanel'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

const DIFFICULTY_STYLES = {
  easy: 'text-green-400 border-green-400/30 bg-green-400/10',
  medium: 'text-orange-400 border-orange-400/30 bg-orange-400/10',
  hard: 'text-red-400 border-red-400/30 bg-red-400/10',
}

export default function SessionView() {
  const {
    currentProblem,
    chatMessages,
    addChatMessage,
    setResults,
    incrementStats,
    sessionStats,
    resetSession,
  } = useStore()

  const [input, setInput] = useState('')
  const [isChatLoading, setIsChatLoading] = useState(false)
  const chatEndRef = useRef(null)

  // Welcome message on session start
  useEffect(() => {
    if (chatMessages.length === 0 && currentProblem) {
      addChatMessage({
        role: 'assistant',
        content: `FlowSense ready.\n\nBottleneck loaded: ${currentProblem.title}\n\nDescribe what you already know about this problem, or ask me to diagnose it and propose an experiment plan.`,
      })
    }
  }, [currentProblem])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages, isChatLoading])

  const handleSend = async () => {
    if (!input.trim() || isChatLoading) return
    const userMessage = input.trim()
    setInput('')
    addChatMessage({ role: 'user', content: userMessage })
    setIsChatLoading(true)

    try {
      const res = await axios.post(`${API_URL}/flowsense/message`, {
        problem_id: currentProblem.id,
        message: userMessage,
        conversation_history: chatMessages,
        current_results: null,
      })

      addChatMessage({ role: 'assistant', content: res.data.response })

      if (res.data.simulation_triggered && res.data.simulation_results) {
        const sim = res.data.simulation_results

        const statsResult = Array.isArray(sim.polar_data)
          ? sim.polar_data[Math.floor(sim.polar_data.length / 2)]
          : (sim.results || sim)

        setResults({
          CL: statsResult?.CL ?? sim.CL,
          CD: statsResult?.CD ?? sim.CD,
          L_D: statsResult?.L_D ?? sim.L_D,
          time_ms: sim.time_ms,
          coordinates: sim.coordinates,
          airfoil: sim.airfoil || sim.best_ld,
          conditions: sim.conditions,
        })
        incrementStats(sim.polar_data?.length || sim.num_points || 50)
      }
    } catch (err) {
      addChatMessage({
        role: 'assistant',
        content: err.response?.data?.detail || 'Connection error. Is the backend running?',
      })
    }

    setIsChatLoading(false)
  }

  return (
    <div className="flex h-full">
      {/* Left: 3D Visualizer */}
      <div className="flex-1 border-r border-zinc-800 flex flex-col">
        {/* Session header */}
        <div className="border-b border-zinc-800 px-6 py-3 flex items-center justify-between bg-zinc-950">
          <div className="flex items-center gap-3">
            <button
              onClick={resetSession}
              className="text-zinc-500 hover:text-zinc-300 text-xs tracking-widest transition-colors"
            >
              ← PROBLEMS
            </button>
            <span className="text-zinc-700">|</span>
            <span className="text-xs text-zinc-400">{currentProblem?.title}</span>
            <span className={`text-xs font-bold px-2 py-0.5 rounded border tracking-widest ${DIFFICULTY_STYLES[currentProblem?.difficulty]}`}>
              {currentProblem?.difficulty?.toUpperCase()}
            </span>
          </div>
          {/* Session stats */}
          <div className="flex gap-6">
            {[
              { label: 'ITERATIONS', value: sessionStats.iterationCount },
              { label: 'CASES', value: sessionStats.casesTotal },
              { label: 'EXPERIMENTS', value: sessionStats.experimentsRun },
            ].map(s => (
              <div key={s.label} className="text-right">
                <div className="text-blue-400 font-bold text-sm">{s.value}</div>
                <div className="text-zinc-600 text-xs tracking-widest">{s.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* 3D canvas */}
        <div className="flex-1">
          <LeftPanel />
        </div>

        {/* Problem statement panel */}
        <div className="border-t border-zinc-800 px-6 py-4 bg-zinc-900/50 max-h-36 overflow-y-auto">
          <div className="text-xs text-blue-400 tracking-widest mb-1">BOTTLENECK</div>
          <p className="text-xs text-zinc-400 leading-relaxed whitespace-pre-wrap">
            {currentProblem?.bottleneck}
          </p>
        </div>
      </div>

      {/* Right: Chat */}
      <div className="w-96 bg-zinc-900 flex flex-col">
        {/* Chat header */}
        <div className="border-b border-zinc-800 px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
            <span className="text-xs font-bold tracking-widest text-zinc-300">FLOWSENSE</span>
          </div>
          <div className="text-xs text-zinc-600 mt-0.5">
            ✓ {currentProblem?.success_criteria
              ? Object.entries(currentProblem.success_criteria)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(' · ')
              : ''}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
          {chatMessages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs rounded-lg px-3 py-2 text-xs leading-relaxed whitespace-pre-wrap ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white rounded-br-sm'
                    : 'bg-zinc-800 text-zinc-100 rounded-bl-sm'
                }`}
              >
                {msg.role === 'assistant' && (
                  <div className="text-blue-400 text-xs tracking-widest mb-1 font-bold">FLOWSENSE</div>
                )}
                {msg.content}
              </div>
            </div>
          ))}

          {isChatLoading && (
            <div className="flex justify-start">
              <div className="bg-zinc-800 rounded-lg rounded-bl-sm px-3 py-2">
                <div className="text-blue-400 text-xs tracking-widest mb-1 font-bold">FLOWSENSE</div>
                <div className="flex gap-1">
                  {[0, 1, 2].map(i => (
                    <div
                      key={i}
                      className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce"
                      style={{ animationDelay: `${i * 100}ms` }}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-zinc-800 p-3">
          <div className="flex gap-2 items-end bg-zinc-800 rounded-lg px-3 py-2">
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
              placeholder="Describe what you've tried, or ask FlowSense to diagnose..."
              className="flex-1 bg-transparent text-zinc-100 text-xs resize-none outline-none placeholder-zinc-600 leading-relaxed"
              rows={2}
            />
            <button
              onClick={handleSend}
              disabled={isChatLoading || !input.trim()}
              className="text-xs text-blue-400 font-bold tracking-widest disabled:text-zinc-700 hover:text-blue-300 transition-colors shrink-0 pb-0.5"
            >
              RUN →
            </button>
          </div>
          <div className="text-zinc-700 text-xs mt-1.5 px-1">
            ↵ send · shift+↵ newline
          </div>
        </div>
      </div>
    </div>
  )
}
