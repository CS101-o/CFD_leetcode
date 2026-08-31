import { useEffect, useRef, useState } from 'react'
import axios from 'axios'
import useStore from '../store/useStore'
import LeftPanel from './LeftPanel'
import SliderMode from './modes/SliderMode'
import TableMode from './modes/TableMode'
import ParetoMode from './modes/ParetoMode'
import TargetMode from './modes/TargetMode'
import MonteCarloMode from './modes/MonteCarloMode'
import AIChatPopup from './AIChatPopup'

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

function PrimerCard({ title, children }) {
  const [open, setOpen] = useState(false)
  return (
    <div className={`border rounded-lg overflow-hidden transition-colors ${open ? 'border-zinc-600' : 'border-zinc-800'}`}>
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-3 py-2 text-left bg-zinc-900 hover:bg-zinc-800/80 transition-colors"
      >
        <span className="text-[10px] font-bold tracking-widest text-zinc-400">{title}</span>
        <span className={`text-zinc-600 text-base leading-none transition-transform ${open ? 'rotate-45' : ''}`}>+</span>
      </button>
      {open && (
        <div className="px-3 pb-3 pt-2 bg-zinc-900 text-[11px] text-zinc-400 leading-relaxed flex flex-col gap-2 border-t border-zinc-800">
          {children}
        </div>
      )}
    </div>
  )
}

function AerodynamicsBackground({ problem }) {
  return (
    <div className="flex flex-col gap-1.5 mt-3">
      <div className="text-[9px] text-zinc-700 tracking-widest">BACKGROUND READING</div>

      <PrimerCard title="NACA 4-DIGIT AIRFOILS — READING THE CODE">
        <p>Each digit describes the shape. Take NACA 2412: <b className="text-zinc-200">2</b> = max camber 2% chord;
        <b className="text-zinc-200"> 4</b> = camber peak at 40% chord; <b className="text-zinc-200">12</b> = max thickness 12% chord.
        Zero in the first digit (e.g. NACA 0012) means symmetric — no camber, no lift at zero angle of attack.
        Adding camber shifts the lift curve upward, producing more lift at the same angle without changing the rigging.</p>
      </PrimerCard>

      <PrimerCard title="REYNOLDS NUMBER — WHAT IT MEANS FOR THIS PROBLEM">
        <p>Re = V·c/ν — the ratio of inertial to viscous forces.
        At Re = {problem.Re.toLocaleString()}, the boundary layer is thicker relative to chord and more sensitive to surface geometry than at the high-Re conditions (Re &gt; 10⁶) in most published data.
        Running a simulation at the wrong Re and using those numbers directly is one of the most common mistakes in low-speed design.</p>
        <div className="bg-zinc-950 border border-zinc-800 rounded px-2 py-1.5 font-mono text-[10px] text-zinc-300">
          Re = V·c / ν &nbsp;·&nbsp; here Re ≈ {(problem.Re / 1e5).toFixed(1)}×10⁵
        </div>
      </PrimerCard>

      <PrimerCard title="LIFT AND DRAG — THE TARGET NUMBERS">
        <p><b className="text-zinc-200">CL (lift coefficient)</b> = L / (½ρV²c). It captures how hard the section is working aerodynamically, independent of size and speed. Camber and angle of attack are the primary levers.</p>
        <p><b className="text-zinc-200">CD (profile drag)</b> = skin friction + pressure drag from any separated region. At low Re, even a modest increase in camber can thicken the boundary layer and raise CD noticeably — so lifting CL often has a drag cost.</p>
        <p><b className="text-zinc-200">L/D</b> = CL/CD — the efficiency ratio. Maximising L/D means getting the most lift for the least drag, which directly determines range and endurance.</p>
      </PrimerCard>

      <PrimerCard title="THE DESIGN TRADE-OFF">
        <p>More camber → higher CL at fixed angle of attack. But more camber steepens the adverse pressure gradient on the upper surface, which at low Re can trigger earlier flow separation and raise CD.
        Thickness helps pressure recovery (which delays separation) but adds wetted area and form drag.
        The task is finding the combination of camber and thickness that clears the target without trading too much drag.</p>
        <div className="bg-zinc-950 border border-zinc-800 rounded px-2 py-1.5 text-[10px] text-zinc-500">
          ↑ camber → ↑ CL (wanted) · risk ↑ CD<br/>
          ↑ thickness → better separation resistance · ↑ wetted area<br/>
          Wrong Re → numbers that don't apply to this aircraft
        </div>
      </PrimerCard>

      {problem.hint && (
        <PrimerCard title="PROBLEM HINT">
          <p className="text-zinc-300">{problem.hint}</p>
        </PrimerCard>
      )}
    </div>
  )
}

const TOOLS = [
  { id: 'sliders',    label: 'SLIDERS' },
  { id: 'table',      label: 'TABLE' },
  { id: 'pareto',     label: 'PARETO' },
  { id: 'target',     label: 'TARGET' },
  { id: 'montecarlo', label: 'MC' },
]

const GUIDE_ITEMS = [
  {
    key: 'sliders',
    tag: 'SLIDERS',
    color: 'text-blue-400',
    tagColor: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
    icon: '⟷',
    title: 'Single-point simulation',
    desc: 'Pick a NACA code, set angle of attack and Reynolds number, and run one simulation. The 3-D wing updates and the tutor assesses your result automatically.',
  },
  {
    key: 'table',
    tag: 'TABLE',
    color: 'text-zinc-300',
    tagColor: 'bg-zinc-700/30 border-zinc-600/30 text-zinc-400',
    icon: '≡',
    title: 'Side-by-side comparison',
    desc: 'Queue several airfoils and run them all at the same condition. Results appear as a sortable table — good for narrowing a shortlist.',
  },
  {
    key: 'pareto',
    tag: 'PARETO',
    color: 'text-emerald-400',
    tagColor: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
    icon: '◌',
    title: 'L/D vs CL scatter',
    desc: 'Plots every run you\'ve done as a dot. Airfoils that dominate (high L/D and high CL) appear toward the top-right — use this to see where your search is heading.',
  },
  {
    key: 'target',
    tag: 'TARGET',
    color: 'text-amber-400',
    tagColor: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
    icon: '⊙',
    title: 'Goal-directed search',
    desc: 'Set a CL or L/D target and let the tool scan a range of airfoils for you. Useful once you know which direction to search.',
  },
  {
    key: 'mc',
    tag: 'MC',
    color: 'text-purple-400',
    tagColor: 'bg-purple-500/10 border-purple-500/30 text-purple-400',
    icon: '∿',
    title: 'Monte Carlo uncertainty',
    desc: 'Runs the simulation many times with small random perturbations to angle of attack and Re. Shows P10–P90 bands so you can see how sensitive your design is to real-world variability.',
  },
  {
    key: 'read',
    tag: 'READ',
    color: 'text-amber-300',
    tagColor: 'bg-amber-500/10 border-amber-500/30 text-amber-300',
    icon: '📖',
    title: 'Background reading',
    desc: 'Opens an aerodynamics primer — NACA digit meanings, Reynolds number, CL/CD definitions, and the camber–drag tradeoff. Tap again to hide.',
  },
  {
    key: 'tutor',
    tag: '✦ TUTOR',
    color: 'text-blue-300',
    tagColor: 'bg-blue-500/10 border-blue-500/30 text-blue-300',
    icon: '✦',
    title: 'AI Research Tutor',
    desc: 'Floating popup in the bottom-right corner. Ask physics questions, request an explanation of your last run, or type "run NACA 4412" to trigger a simulation directly from chat. Auto-opens after every slider run.',
  },
]

function GuidanceModal({ onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-zinc-950 border border-zinc-700 rounded-2xl w-full max-w-lg max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-4 h-4 bg-blue-500 rotate-45 rounded-sm" />
            <div>
              <div className="text-xs font-bold tracking-widest text-zinc-100">HOW IT WORKS</div>
              <div className="text-[10px] text-zinc-600 tracking-widest">TOOL REFERENCE</div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-600 hover:text-zinc-300 text-xl leading-none transition-colors"
          >
            ×
          </button>
        </div>

        {/* Items */}
        <div className="flex-1 overflow-y-auto px-6 py-4 flex flex-col gap-4">
          {GUIDE_ITEMS.map(item => (
            <div key={item.key} className="flex gap-4 items-start">
              <div className={`shrink-0 w-16 text-center border rounded-lg py-1 text-[10px] font-bold tracking-widest ${item.tagColor}`}>
                {item.tag}
              </div>
              <div className="flex-1 min-w-0">
                <div className={`text-xs font-bold mb-0.5 ${item.color}`}>{item.title}</div>
                <div className="text-[11px] text-zinc-500 leading-relaxed">{item.desc}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-zinc-800 shrink-0 flex items-center justify-between">
          <span className="text-[10px] text-zinc-600">Re-open anytime with the <b className="text-zinc-500">?</b> button</span>
          <button
            onClick={onClose}
            className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold tracking-widest px-5 py-2 rounded-lg transition-colors"
          >
            GOT IT →
          </button>
        </div>
      </div>
    </div>
  )
}

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
    sessionStats,
    results,
    allResults,
    addAiMessage,
    setAiAssessing,
  } = useStore()

  const [input, setInput] = useState('')
  const [isChatLoading, setIsChatLoading] = useState(false)
  const [readingOpen, setReadingOpen] = useState(false)
  const [guidanceOpen, setGuidanceOpen] = useState(() => {
    try { return !localStorage.getItem('al_guidance_seen') } catch { return true }
  })
  const chatEndRef = useRef(null)

  function closeGuidance() {
    try { localStorage.setItem('al_guidance_seen', '1') } catch {}
    setGuidanceOpen(false)
  }

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

  // Welcome hint when session starts
  const tutorWelcomeSent = useRef(false)
  useEffect(() => {
    if (!currentProblem || tutorWelcomeSent.current) return
    tutorWelcomeSent.current = true
    setAiAssessing(true)
    axios.post(`${API_URL}/tutor/hint`, {
      session_id: sessionId,
      problem_id: currentProblem.id,
      run_count: 0,
      recent_results: [],
      hint_type: 'welcome',
    }).then(res => {
      if (res.data.message) addAiMessage({ type: 'tutor', text: res.data.message })
    }).catch(() => { setAiAssessing(false) })
  }, [currentProblem])

  // Auto-assess after every slider run
  const lastAssessedRun = useRef(0)
  useEffect(() => {
    if (!currentProblem) return
    if (!results || sessionStats.experimentsRun === 0) return
    if (sessionStats.experimentsRun === lastAssessedRun.current) return
    lastAssessedRun.current = sessionStats.experimentsRun
    setAiAssessing(true)
    axios.post(`${API_URL}/tutor/assess`, {
      session_id: sessionId,
      problem_id: currentProblem.id,
      airfoil: results.airfoil || '????',
      alpha: results.alpha ?? currentProblem.design_alpha ?? 4,
      reynolds: results.reynolds ?? currentProblem.Re ?? 500000,
      CL: results.CL,
      CD: results.CD,
      L_D: results.L_D ?? null,
    }).then(res => {
      addAiMessage({
        type: 'assessment',
        text: res.data.message,
        compliance: res.data.compliance,
        at_design: res.data.at_design_condition,
        airfoil: results.airfoil || '????',
        alpha: results.alpha ?? currentProblem.design_alpha ?? 4,
        reynolds: results.reynolds ?? currentProblem.Re ?? 500000,
      })
    }).catch(() => { setAiAssessing(false) })
  }, [sessionStats.experimentsRun])

  // Progress hint every 3 runs while requirements still not fully met
  const lastHintRun = useRef(0)
  useEffect(() => {
    if (!currentProblem || sessionStats.experimentsRun === 0) return
    if (sessionStats.experimentsRun % 3 !== 0) return
    if (sessionStats.experimentsRun === lastHintRun.current) return
    const clMin = currentProblem.success_criteria?.cruise_CL_min
    const recentPassing = allResults.slice(-3).every(r =>
      (clMin == null || r.CL >= clMin)
    )
    if (recentPassing) return
    lastHintRun.current = sessionStats.experimentsRun
    const recent = allResults.slice(-3).map(r => ({
      airfoil: r.airfoil || '????',
      CL: r.CL,
      cl_meets: clMin == null || r.CL >= clMin,
      cd_meets: true,
    }))
    axios.post(`${API_URL}/tutor/hint`, {
      session_id: sessionId,
      problem_id: currentProblem.id,
      run_count: sessionStats.experimentsRun,
      recent_results: recent,
      hint_type: 'progress',
    }).then(res => {
      if (res.data.message) addAiMessage({ type: 'tutor', text: res.data.message })
    }).catch(() => {})
  }, [sessionStats.experimentsRun])

  function applySimResult(sim) {
    let statsResult
    if (Array.isArray(sim.polar_data)) {
      statsResult = sim.polar_data.reduce((best, pt) =>
        Math.abs(pt.alpha - (currentProblem?.design_alpha ?? 4)) < Math.abs(best.alpha - (currentProblem?.design_alpha ?? 4)) ? pt : best
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

  // Tutor popup handler — routes through FlowSense function-calling endpoint
  async function onTutorSendMessage(userText, history) {
    const conversationHistory = history
      .filter(m => m.type === 'user' || m.type === 'tutor')
      .map(m => ({ role: m.type === 'user' ? 'user' : 'assistant', content: m.text || '' }))

    const res = await axios.post(`${API_URL}/flowsense/message`, {
      problem_id: currentProblem.id,
      message: userText,
      conversation_history: conversationHistory,
      current_results: null,
      session_id: sessionId,
      participant_id: participantId,
    })

    let simData = null
    if (res.data.simulation_triggered && res.data.simulation_results) {
      simData = res.data.simulation_results
      applySimResult(simData)
      if (res.data.response?.includes('✓ BOTTLENECK SOLVED') && !solvedProblems.has(currentProblem.id)) {
        markSolved(currentProblem.id)
      }
    }
    return { text: res.data.response, simData }
  }

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
        addChatMessage({ role: 'assistant', content: res.data.response, chartData: res.data.simulation_results })
        applySimResult(res.data.simulation_results)
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
    {guidanceOpen && <GuidanceModal onClose={closeGuidance} />}
    {currentProblem && (
      <AIChatPopup
        sessionId={sessionId}
        runCount={sessionStats.experimentsRun}
        label="RESEARCH TUTOR"
        onSendMessage={onTutorSendMessage}
      />
    )}
    <div className="flex h-full">

      {/* Left: 3D viz + problem brief — desktop only */}
      <div className="hidden md:flex flex-1 border-r border-zinc-800 flex-col min-w-0">

        {/* Session header */}
        <div className="border-b border-zinc-800 px-4 py-3 flex items-center justify-between bg-zinc-950 shrink-0">
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
          <button
            onClick={() => setGuidanceOpen(true)}
            title="How it works"
            className="w-6 h-6 rounded-full border border-zinc-700 text-zinc-500 hover:text-zinc-200 hover:border-zinc-500 text-xs font-bold flex items-center justify-center transition-colors"
          >
            ?
          </button>
        </div>

        {/* 3D viz */}
        <div className="flex-1 overflow-hidden">
          <LeftPanel />
        </div>

        {/* Drag handle */}
        {currentProblem && (
          <div
            onMouseDown={onDragStart}
            className="h-1.5 bg-zinc-800 hover:bg-blue-500/50 cursor-row-resize shrink-0 transition-colors"
          />
        )}

        {/* Problem brief */}
        {currentProblem && (
          <div style={{ height: briefHeight }} className="bg-zinc-950 shrink-0 overflow-y-auto px-6 py-4 flex gap-8 items-start">
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

        {/* Mobile-only 3D view */}
        <div className="md:hidden h-48 shrink-0 border-b border-zinc-800">
          <LeftPanel />
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
          <button
            onClick={() => setReadingOpen(o => !o)}
            className={`px-3 py-2.5 text-xs font-bold tracking-widest transition-colors border-b-2 -mb-px ${
              readingOpen
                ? 'text-amber-400 border-amber-500 bg-zinc-800/50'
                : 'text-zinc-600 border-transparent hover:text-zinc-400'
            }`}
          >
            READ
          </button>
        </div>

        {/* Reading panel — slides in above the tool content */}
        {readingOpen && currentProblem && (
          <div className="border-b border-zinc-800 bg-zinc-950 overflow-y-auto shrink-0 max-h-[50vh]">
            <AerodynamicsBackground problem={currentProblem} />
          </div>
        )}

        {/* Tool content */}
        <div className="flex-1 overflow-hidden">
          {activeMode === 'sliders'    && <SliderMode />}
          {activeMode === 'table'      && <TableMode />}
          {activeMode === 'pareto'     && <ParetoMode />}
          {activeMode === 'target'     && <TargetMode />}
          {activeMode === 'montecarlo' && <MonteCarloMode />}
        </div>
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
