import { useEffect, useRef, useState } from 'react'
import axios from 'axios'
import useStore from '../store/useStore'
import LeftPanel from './LeftPanel'
import SliderMode from './modes/SliderMode'
import TableMode from './modes/TableMode'
import ParetoMode from './modes/ParetoMode'
import TargetMode from './modes/TargetMode'
import MonteCarloMode from './modes/MonteCarloMode'

const API_URL = import.meta.env.VITE_API_URL || '/api/v1'

const DIFFICULTY_STYLES = {
  easy: 'text-green-400 border-green-400/30 bg-green-400/10',
  medium: 'text-orange-400 border-orange-400/30 bg-orange-400/10',
  hard: 'text-red-400 border-red-400/30 bg-red-400/10',
}

// ── inline chart components ───────────────────────────────────────────────────

function MiniPolar({ data, yKey, label, color, designAlpha }) {
  const W = 190, H = 100, P = { top: 8, right: 8, bottom: 22, left: 30 }
  const iW = W - P.left - P.right, iH = H - P.top - P.bottom
  const xs = data.map(d => d.alpha)
  const ys = data.map(d => d[yKey]).filter(v => v != null)
  const xMin = Math.min(...xs), xMax = Math.max(...xs)
  const yMin = Math.min(...ys), yMax = Math.max(...ys)
  const pad = (yMax - yMin) * 0.1 || 1
  const sx = a => P.left + ((a - xMin) / (xMax - xMin || 1)) * iW
  const sy = v => P.top + (1 - (v - (yMin - pad)) / ((yMax + pad) - (yMin - pad))) * iH
  const pts = data.filter(d => d[yKey] != null).map(d => `${sx(d.alpha)},${sy(d[yKey])}`).join(' ')
  const ticks = [yMin, (yMin + yMax) / 2, yMax]
  return (
    <svg width={W} height={H}>
      {ticks.map((v, i) => (
        <g key={i}>
          <line x1={P.left} x2={W - P.right} y1={sy(v)} y2={sy(v)} stroke="#3f3f46" strokeWidth={0.5} />
          <text x={P.left - 3} y={sy(v) + 3} textAnchor="end" fontSize={7} fill="#71717a">{v.toFixed(1)}</text>
        </g>
      ))}
      {designAlpha != null && (
        <line x1={sx(designAlpha)} x2={sx(designAlpha)} y1={P.top} y2={H - P.bottom} stroke="#f59e0b" strokeWidth={1} strokeDasharray="3,2" />
      )}
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1.5} />
      <text x={W / 2} y={H - 2} textAnchor="middle" fontSize={7} fill="#71717a">α (°)</text>
      <text x={8} y={H / 2} textAnchor="middle" fontSize={7} fill={color} transform={`rotate(-90,8,${H / 2})`}>{label}</text>
    </svg>
  )
}

function MiniDistBar({ label, dist, color }) {
  if (!dist) return null
  const lo = dist.p10, hi = dist.p90, mid = dist.p50
  const range = hi - lo || 1
  const pct = v => Math.max(0, Math.min(100, ((v - lo) / range) * 100))
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between text-xs" style={{ fontSize: 10 }}>
        <span style={{ color }} className="font-bold">{label}</span>
        <span className="text-zinc-400">{mid.toFixed(3)}</span>
      </div>
      <div className="relative h-3 bg-zinc-700 rounded overflow-hidden">
        <div className="absolute h-full rounded opacity-40" style={{ left: `${pct(dist.p25)}%`, width: `${pct(dist.p75) - pct(dist.p25)}%`, background: color }} />
        <div className="absolute h-full border-x" style={{ left: `${pct(lo)}%`, width: `${pct(hi) - pct(lo)}%`, borderColor: color }} />
        <div className="absolute top-0 h-full w-0.5" style={{ left: `${pct(mid)}%`, background: color }} />
      </div>
      <div className="flex justify-between" style={{ fontSize: 9, color: '#71717a' }}>
        <span>{lo.toFixed(3)}</span><span>P10–P90</span><span>{hi.toFixed(3)}</span>
      </div>
    </div>
  )
}

function InlineCharts({ data, designAlpha }) {
  if (!data) return null

  // Polar sweep
  if (Array.isArray(data.polar_data) && data.polar_data.length > 0) {
    const peak = data.summary || {}
    const cruise = data.polar_data.find(p => p.alpha === designAlpha) || data.polar_data[Math.floor(data.polar_data.length / 2)]
    return (
      <div className="mt-2 border border-zinc-700 rounded-lg overflow-hidden">
        <div className="bg-zinc-800 px-3 py-1.5 flex items-center justify-between">
          <div>
            <span className="text-blue-400 font-mono font-bold text-xs">NACA {data.airfoil}</span>
            <span className="text-zinc-500 text-xs ml-2">polar sweep</span>
          </div>
          <div className="flex gap-3 text-xs">
            <span className="text-zinc-400">peak L/D <span className="text-emerald-400 font-bold">{peak.max_L_D ?? '—'}</span></span>
            {cruise && <span className="text-zinc-400">α{designAlpha}° CL <span className="text-blue-400 font-bold">{cruise.CL?.toFixed(3)}</span></span>}
          </div>
        </div>
        <div className="bg-zinc-900 p-2 flex gap-1">
          <MiniPolar data={data.polar_data} yKey="CL"  label="CL"  color="#3b82f6" designAlpha={designAlpha} />
          <MiniPolar data={data.polar_data} yKey="L_D" label="L/D" color="#10b981" designAlpha={designAlpha} />
        </div>
        <div className="bg-zinc-800/50 px-3 py-1 text-center text-zinc-600" style={{ fontSize: 10 }}>
          dashed line = cruise α · click to expand
        </div>
      </div>
    )
  }

  // Monte Carlo
  if (data.distributions) {
    return (
      <div className="mt-2 border border-zinc-700 rounded-lg overflow-hidden">
        <div className="bg-zinc-800 px-3 py-1.5 flex items-center justify-between">
          <div>
            <span className="text-purple-400 font-mono font-bold text-xs">NACA {data.airfoil}</span>
            <span className="text-zinc-500 text-xs ml-2">monte carlo · {data.n_samples} samples</span>
          </div>
          <span className="text-zinc-400 text-xs">median L/D <span className="text-emerald-400 font-bold">{data.distributions.L_D?.p50}</span></span>
        </div>
        <div className="bg-zinc-900 px-3 py-3 flex flex-col gap-3">
          <MiniDistBar label="CL"  dist={data.distributions.CL}  color="#3b82f6" />
          <MiniDistBar label="L/D" dist={data.distributions.L_D} color="#10b981" />
        </div>
        <div className="bg-zinc-800/50 px-3 py-1 text-center text-zinc-600" style={{ fontSize: 10 }}>
          bar = P10–P90 range · click to expand
        </div>
      </div>
    )
  }

  return null
}

const TOOLS = [
  { id: 'chat',       label: 'CHAT' },
  { id: 'sliders',    label: 'SLIDERS' },
  { id: 'table',      label: 'TABLE' },
  { id: 'pareto',     label: 'PARETO' },
  { id: 'target',     label: 'TARGET' },
  { id: 'montecarlo', label: 'MC' },
]

export default function SessionView() {
  const {
    currentProblem,
    chatMessages,
    addChatMessage,
    setResults,
    setPolarData,
    incrementStats,
    resetSession,
    sessionId,
    participantId,
    activeMode,
    setActiveMode,
    markSolved,
    solvedProblems,
  } = useStore()

  const [input, setInput] = useState('')
  const [isChatLoading, setIsChatLoading] = useState(false)
  const chatEndRef = useRef(null)

  const [briefHeight, setBriefHeight] = useState(220)
  const [expandedChart, setExpandedChart] = useState(null)
  const dragState = useRef(null)

  function onDragStart(e) {
    dragState.current = { startY: e.clientY, startH: briefHeight }
    e.preventDefault()
  }

  useEffect(() => {
    function onMove(e) {
      if (!dragState.current) return
      const delta = dragState.current.startY - e.clientY
      setBriefHeight(Math.min(400, Math.max(80, dragState.current.startH + delta)))
    }
    function onUp() { dragState.current = null }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp) }
  }, [])

  const welcomeSent = useRef(false)
  useEffect(() => {
    if (!currentProblem) return
    // Pre-load starting airfoil so the 3D view is never empty
    const airfoil = currentProblem.starting_airfoil.replace('naca', '')
    axios.post(`${API_URL}/simulate/single`, {
      airfoil,
      alpha: currentProblem.design_alpha ?? 4,
      reynolds: currentProblem.Re,
      mach: currentProblem.mach ?? 0,
    }).then(res => {
      setResults({ coordinates: res.data.coordinates, airfoil })
    }).catch(() => {})

    if (!welcomeSent.current) {
      welcomeSent.current = true
      addChatMessage({
        role: 'assistant',
        content: `[${currentProblem.sender}]\n${currentProblem.mission_briefing}\n\n── TOOLS ──\nSLIDERS — single simulation at a fixed angle\nTABLE   — compare multiple airfoils side by side\nPARETO  — plot the L/D vs CL tradeoff across all your runs\nTARGET  — search for airfoils that meet a specific target\nMC      — Monte Carlo uncertainty sweep\n\nTo run a simulation, name a NACA code in chat: "run NACA 4412" or "sweep NACA 5409".`,
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
        session_id: sessionId,
        participant_id: participantId,
      })

      if (res.data.simulation_triggered && res.data.simulation_results) {
        const sim = res.data.simulation_results
        addChatMessage({ role: 'assistant', content: res.data.response, chartData: sim })
      } else {
        addChatMessage({ role: 'assistant', content: res.data.response })
      }

      if (res.data.response?.includes('✓ BOTTLENECK SOLVED') && !solvedProblems.has(currentProblem.id)) {
        markSolved(currentProblem.id)
        addChatMessage({
          role: 'assistant',
          content: `[${currentProblem.sender}]\n${currentProblem.mission_complete}`,
        })
      }

      if (res.data.simulation_triggered && res.data.simulation_results) {
        const sim = res.data.simulation_results
        // For polar sweeps pick the point closest to alpha=4 (design point); fallback to midpoint
        let statsResult
        if (Array.isArray(sim.polar_data)) {
          statsResult = sim.polar_data.reduce((best, pt) =>
            Math.abs(pt.alpha - 4) < Math.abs(best.alpha - 4) ? pt : best
          )
        } else {
          statsResult = sim.results || sim
        }

        setResults({
          CL: statsResult?.CL ?? sim.CL,
          CD: statsResult?.CD ?? sim.CD,
          L_D: statsResult?.L_D ?? sim.L_D,
          time_ms: sim.time_ms,
          coordinates: sim.coordinates,
          airfoil: sim.airfoil || sim.best_ld,
          conditions: sim.conditions,
        })
        if (Array.isArray(sim.polar_data)) setPolarData(sim.polar_data)
        incrementStats(sim.polar_data?.length || sim.num_points || 1)

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
    <>
    <div className="flex flex-col md:flex-row h-full">

      {/* Left: 3D viz + problem brief */}
      <div className="flex flex-col shrink-0 md:flex-1 md:shrink border-b md:border-b-0 md:border-r border-zinc-800 min-w-0">

        {/* Session header — desktop only */}
        <div className="hidden md:flex border-b border-zinc-800 px-4 py-3 items-center justify-between bg-zinc-950 shrink-0">
          <div className="flex items-center gap-3">
            <button onClick={resetSession} className="text-zinc-500 hover:text-zinc-300 text-xs tracking-widest transition-colors">
              ← PROBLEMS
            </button>
            <span className="text-zinc-700">|</span>
            <span className="text-xs text-zinc-400">{currentProblem?.title}</span>
            <span className={`text-xs font-bold px-2 py-0.5 rounded border tracking-widest ${DIFFICULTY_STYLES[currentProblem?.difficulty]}`}>
              {currentProblem?.difficulty?.toUpperCase()}
            </span>
          </div>
        </div>

        {/* 3D viz — fixed height on mobile, flex-1 on desktop */}
        <div className="h-48 shrink-0 md:h-auto md:shrink md:flex-1 overflow-hidden">
          <LeftPanel />
        </div>

        {/* Drag handle — desktop only */}
        {currentProblem && (
          <div
            onMouseDown={onDragStart}
            className="hidden md:block h-1.5 bg-zinc-800 hover:bg-blue-500/50 cursor-row-resize shrink-0 transition-colors"
          />
        )}

        {/* Problem brief — desktop only */}
        {currentProblem && (
          <div style={{ height: briefHeight }} className="hidden md:flex bg-zinc-950 shrink-0 overflow-y-auto px-6 py-4 gap-8 items-start">
            <div className="shrink-0">
              <div className="text-xs text-zinc-600 tracking-widest mb-2">BASELINE</div>
              <div className="text-2xl font-mono font-bold text-blue-400">
                NACA {currentProblem.starting_airfoil.replace('naca', '')}
              </div>
              <div className="text-xs text-zinc-500 mt-1 space-y-0.5">
                <div>Re {currentProblem.Re.toLocaleString()}</div>
                <div>α = {currentProblem.design_alpha}° · Mach {currentProblem.mach}</div>
              </div>
            </div>
            <div className="w-px bg-zinc-800 self-stretch" />
            <div className="flex-1 min-w-0">
              <div className="text-xs text-zinc-600 tracking-widest mb-2">BOTTLENECK</div>
              <p className="text-base text-zinc-200 leading-relaxed border-l-2 border-amber-500 pl-3 mb-3">
                {currentProblem.bottleneck.split('\n')[0]}
              </p>
              <div className="flex gap-2 flex-wrap pl-3">
                {Object.entries(currentProblem.success_criteria).map(([k, v]) => (
                  <span key={k} className="text-xs font-mono font-bold text-red-300 bg-red-950/40 border border-red-500/20 rounded px-2 py-1">
                    {k.replace(/_/g, ' ').toUpperCase()} {typeof v === 'number' ? `> ${v}` : `+${v}°`}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Right: tool + chat panel — full width on mobile */}
      <div className="flex-1 md:flex-none w-full md:w-[460px] bg-zinc-900 flex flex-col shrink-0">

        {/* Mobile-only header */}
        <div className="md:hidden border-b border-zinc-800 px-4 py-3 flex items-center gap-3 bg-zinc-950 shrink-0">
          <button onClick={resetSession} className="text-zinc-500 hover:text-zinc-300 text-xs tracking-widest transition-colors shrink-0">
            ← PROBLEMS
          </button>
          <span className="text-zinc-700">|</span>
          <span className="text-xs text-zinc-400 truncate">{currentProblem?.title}</span>
        </div>

        {/* Tab nav */}
        <div className="border-b border-zinc-800 flex shrink-0">
          {TOOLS.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveMode(t.id)}
              className={`px-3 py-2.5 text-xs font-bold tracking-widest transition-colors border-b-2 -mb-px flex-1 ${
                activeMode === t.id
                  ? 'text-blue-400 border-blue-500 bg-zinc-800/50'
                  : 'text-zinc-600 border-transparent hover:text-zinc-400'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Tool content */}
        {activeMode !== 'chat' && (
          <div className="flex-1 overflow-hidden">
            {activeMode === 'sliders'    && <SliderMode />}
            {activeMode === 'table'      && <TableMode />}
            {activeMode === 'pareto'     && <ParetoMode />}
            {activeMode === 'target'     && <TargetMode />}
            {activeMode === 'montecarlo' && <MonteCarloMode />}
          </div>
        )}

        {/* Chat content */}
        {activeMode === 'chat' && (
          <>
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
              {chatMessages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-sm rounded-lg px-3 py-2 text-xs leading-relaxed whitespace-pre-wrap ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white rounded-br-sm'
                      : 'bg-zinc-800 text-zinc-100 rounded-bl-sm'
                  }`}>
                    {msg.role === 'assistant' && (
                      <div className="text-blue-400 text-xs tracking-widest mb-1 font-bold">AIRFOILLEARNER</div>
                    )}
                    {msg.content}
                    {msg.chartData && (
                      <div onClick={() => setExpandedChart(msg.chartData)} className="cursor-zoom-in">
                        <InlineCharts data={msg.chartData} designAlpha={currentProblem?.design_alpha} />
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {isChatLoading && (
                <div className="flex justify-start">
                  <div className="bg-zinc-800 rounded-lg rounded-bl-sm px-3 py-2">
                    <div className="text-blue-400 text-xs tracking-widest mb-1 font-bold">AIRFOILLEARNER</div>
                    <div className="flex gap-1">
                      {[0, 1, 2].map(i => (
                        <div key={i} className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce"
                          style={{ animationDelay: `${i * 100}ms` }} />
                      ))}
                    </div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            <div className="border-t border-zinc-800 p-3">
              <div className="flex gap-2 items-end bg-zinc-800 rounded-lg px-3 py-2">
                <textarea
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
                  }}
                  placeholder="Ask AirfoilLearner or request a simulation..."
                  className="flex-1 bg-transparent text-zinc-100 text-xs resize-none outline-none placeholder-zinc-600 leading-relaxed"
                  rows={2}
                />
                <button
                  onClick={handleSend}
                  disabled={isChatLoading || !input.trim()}
                  className="text-xs text-blue-400 font-bold tracking-widest disabled:text-zinc-700 hover:text-blue-300 transition-colors shrink-0 pb-0.5"
                >
                  SEND →
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>

    {/* Chart expand modal */}
    {expandedChart && (
      <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center" onClick={() => setExpandedChart(null)}>
        <div className="bg-zinc-900 border border-zinc-700 rounded-xl p-6 max-w-3xl w-full mx-6 shadow-2xl" onClick={e => e.stopPropagation()}>
          <div className="flex items-center justify-between mb-4">
            <div className="text-xs text-zinc-400 tracking-widest font-bold">
              {expandedChart.polar_data ? `POLAR — NACA ${expandedChart.airfoil}` : `MONTE CARLO — NACA ${expandedChart.airfoil}`}
            </div>
            <button onClick={() => setExpandedChart(null)} className="text-zinc-500 hover:text-zinc-200 text-lg leading-none">✕</button>
          </div>
          {Array.isArray(expandedChart.polar_data) && (
            <div className="flex gap-6 justify-center">
              {[{yKey:'CL', label:'CL', color:'#3b82f6'}, {yKey:'L_D', label:'L/D', color:'#10b981'}].map(cfg => (
                <MiniPolar key={cfg.yKey} data={expandedChart.polar_data} yKey={cfg.yKey} label={cfg.label} color={cfg.color} designAlpha={currentProblem?.design_alpha} W={320} H={200} />
              ))}
            </div>
          )}
          {expandedChart.distributions && (
            <div className="flex flex-col gap-5">
              <MiniDistBar label="CL"  dist={expandedChart.distributions.CL}  color="#3b82f6" />
              <MiniDistBar label="L/D" dist={expandedChart.distributions.L_D} color="#10b981" />
            </div>
          )}
          <div className="text-xs text-zinc-600 text-center mt-4">click outside to close</div>
        </div>
      </div>
    )}
    </>
  )
}
