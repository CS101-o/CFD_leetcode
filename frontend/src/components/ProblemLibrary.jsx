import { useEffect, useRef, useState } from 'react'
import axios from 'axios'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, PerspectiveCamera, Line } from '@react-three/drei'
import * as THREE from 'three'
import useStore from '../store/useStore'

const API_URL = import.meta.env.VITE_API_URL || '/api/v1'

const DIFFICULTY_STYLES = {
  easy:   'text-green-400 border-green-400/30 bg-green-400/10',
  medium: 'text-orange-400 border-orange-400/30 bg-orange-400/10',
  hard:   'text-red-400 border-red-400/30 bg-red-400/10',
}

// ── 3-D airfoil preview ───────────────────────────────────────────────────────

function AirfoilMesh({ coordinates }) {
  if (!coordinates?.length) return null
  const scale = 5
  const points = coordinates.map(([x, y]) =>
    new THREE.Vector3((x - 0.5) * scale, y * scale, 0)
  )
  return (
    <group>
      <Line points={points} color="#3b82f6" lineWidth={2} />
      <mesh>
        <extrudeGeometry args={[
          new THREE.Shape(points.map(p => new THREE.Vector2(p.x, p.y))),
          { depth: 0.4, bevelEnabled: false },
        ]} />
        <meshStandardMaterial color="#1d4ed8" metalness={0.4} roughness={0.3} />
      </mesh>
    </group>
  )
}

// ── metric badge ──────────────────────────────────────────────────────────────

function MetricRow({ label, current, target, passing }) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-zinc-500 w-8">{label}</span>
      <span className={`font-mono font-bold ${passing ? 'text-green-400' : 'text-red-400'}`}>
        {current ?? '—'}
      </span>
      <span className="text-zinc-600 mx-1">→</span>
      <span className="text-zinc-400 font-mono">{target}</span>
      <span className="ml-1">{passing ? '✓' : '✗'}</span>
    </div>
  )
}

// ── waitlist + feedback, main page ─────────────────────────────────────────────

function WaitlistBox() {
  const [email, setEmail] = useState('')
  const [state, setState] = useState('') // '' | 'saving' | 'done' | error text

  function submit() {
    setState('saving')
    axios.post(`${API_URL}/module01/waitlist`, { email: email.trim(), source: 'main_page' })
      .then(() => setState('done'))
      .catch(err => setState(err.response?.data?.detail || 'Could not join. Check the address.'))
  }

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
      <div className="text-xs font-bold text-zinc-200 mb-1">Join the waitlist</div>
      <p className="text-[11px] text-zinc-500 leading-relaxed mb-3">
        Hear about new problems when they ship. No spam, unsubscribe anytime.
      </p>
      {state === 'done' ? (
        <div className="text-emerald-400 text-xs font-bold">You're on the list.</div>
      ) : (
        <div className="flex gap-2">
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="flex-1 min-w-0 bg-zinc-800 border border-zinc-700 text-zinc-100 text-xs rounded-lg px-3 py-2 outline-none focus:border-blue-500 placeholder-zinc-600"
          />
          <button
            onClick={submit}
            disabled={!email.trim() || state === 'saving'}
            className="shrink-0 bg-zinc-100 hover:bg-white disabled:bg-zinc-800 disabled:text-zinc-600 text-zinc-900 text-xs font-bold tracking-widest px-4 rounded-lg transition-colors"
          >
            JOIN
          </button>
        </div>
      )}
      {state && state !== 'saving' && state !== 'done' && (
        <div className="text-red-400 text-[11px] mt-2">{state}</div>
      )}
    </div>
  )
}

function FeedbackBox() {
  const [message, setMessage] = useState('')
  const [email, setEmail] = useState('')
  const [state, setState] = useState('')

  function submit() {
    setState('saving')
    axios.post(`${API_URL}/module01/feedback`, { message: message.trim(), email: email.trim(), source: 'main_page' })
      .then(() => setState('done'))
      .catch(err => setState(err.response?.data?.detail || 'Could not send. Try again.'))
  }

  if (state === 'done') {
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <div className="text-xs font-bold text-zinc-200 mb-1">Give feedback</div>
        <div className="text-emerald-400 text-xs font-bold">Got it. Thanks.</div>
      </div>
    )
  }

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
      <div className="text-xs font-bold text-zinc-200 mb-1">Give feedback, or suggest a problem</div>
      <p className="text-[11px] text-zinc-500 leading-relaxed mb-3">
        What's missing, broken, or confusing, or an aerodynamic design problem you wish existed here.
        We read all of it, or email{' '}
        <a href="mailto:kaan.oktem@airfoillearner.com" className="text-blue-500 hover:text-blue-400 underline underline-offset-2">
          kaan.oktem@airfoillearner.com
        </a>{' '}
        directly.
      </p>
      <textarea
        value={message}
        onChange={e => setMessage(e.target.value)}
        placeholder="e.g. a problem idea, or what would make this better"
        rows={3}
        className="w-full bg-zinc-800 border border-zinc-700 text-zinc-100 text-xs rounded-lg px-3 py-2 outline-none focus:border-blue-500 placeholder-zinc-600 resize-none mb-2"
      />
      <div className="flex gap-2">
        <input
          type="email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          placeholder="email (optional, if you want a reply)"
          className="flex-1 min-w-0 bg-zinc-800 border border-zinc-700 text-zinc-100 text-xs rounded-lg px-3 py-2 outline-none focus:border-blue-500 placeholder-zinc-600"
        />
        <button
          onClick={submit}
          disabled={message.trim().length < 3 || state === 'saving'}
          className="shrink-0 bg-zinc-100 hover:bg-white disabled:bg-zinc-800 disabled:text-zinc-600 text-zinc-900 text-xs font-bold tracking-widest px-4 rounded-lg transition-colors"
        >
          SEND
        </button>
      </div>
      {state && state !== 'saving' && (
        <div className="text-red-400 text-[11px] mt-2">{state}</div>
      )}
    </div>
  )
}

function BugReportBox() {
  const [message, setMessage] = useState('')
  const [email, setEmail] = useState('')
  const [state, setState] = useState('')

  function submit() {
    setState('saving')
    axios.post(`${API_URL}/module01/feedback`, { message: message.trim(), email: email.trim(), source: 'bug_report' })
      .then(() => setState('done'))
      .catch(err => setState(err.response?.data?.detail || 'Could not send. Try again.'))
  }

  if (state === 'done') {
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <div className="text-xs font-bold text-zinc-200 mb-1">Report a bug</div>
        <div className="text-emerald-400 text-xs font-bold">Got it. Thanks for flagging it.</div>
      </div>
    )
  }

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
      <div className="text-xs font-bold text-zinc-200 mb-1">Report a bug</div>
      <p className="text-[11px] text-zinc-500 leading-relaxed mb-3">
        Something broken or behaving wrong? What happened, and what did you expect instead?
      </p>
      <textarea
        value={message}
        onChange={e => setMessage(e.target.value)}
        placeholder="e.g. clicked START on rung 3 and the page went blank"
        rows={3}
        className="w-full bg-zinc-800 border border-zinc-700 text-zinc-100 text-xs rounded-lg px-3 py-2 outline-none focus:border-blue-500 placeholder-zinc-600 resize-none mb-2"
      />
      <div className="flex gap-2">
        <input
          type="email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          placeholder="email (optional, if you want a reply)"
          className="flex-1 min-w-0 bg-zinc-800 border border-zinc-700 text-zinc-100 text-xs rounded-lg px-3 py-2 outline-none focus:border-blue-500 placeholder-zinc-600"
        />
        <button
          onClick={submit}
          disabled={message.trim().length < 3 || state === 'saving'}
          className="shrink-0 bg-zinc-100 hover:bg-white disabled:bg-zinc-800 disabled:text-zinc-600 text-zinc-900 text-xs font-bold tracking-widest px-4 rounded-lg transition-colors"
        >
          SEND
        </button>
      </div>
      {state && state !== 'saving' && (
        <div className="text-red-400 text-[11px] mt-2">{state}</div>
      )}
    </div>
  )
}

// ── mission popup ───────────────────────────────────────────────────────────────

function MissionModal({ onClose }) {
  return (
    <div className="fixed inset-0 z-40 flex items-start justify-start p-4 md:p-6 bg-black/70 backdrop-blur-sm overflow-y-auto">
      <div className="bg-zinc-950 border border-blue-500/30 rounded-xl max-w-md w-full my-auto md:my-0 max-h-[85vh] overflow-y-auto shadow-2xl">
        <div className="flex items-center justify-between px-5 pt-5 sticky top-0 bg-zinc-950">
          <div className="text-[10px] font-bold text-blue-400 tracking-widest">OUR MISSION</div>
          <button
            onClick={onClose}
            className="text-zinc-600 hover:text-zinc-300 text-lg leading-none transition-colors"
          >
            ×
          </button>
        </div>
        <div className="px-5 pt-3 pb-5 flex flex-col gap-4">
          <p className="text-[13px] text-zinc-300 leading-relaxed">
            Our mission is to adapt the LeetCode philosophy to aerodynamic design, challenging your
            aerodynamic design knowledge so you learn by solving problems. We host simulations so
            learners can practise real problems and get feedback in seconds. Have an idea for one?
            Suggest it and we'll build it. Longer term, we want anyone to be able to design and add
            their own LeetCode-style aerodynamic design problems to the platform, growing a curated
            community around that same philosophy.
          </p>

          <div className="border-t border-zinc-800 pt-4">
            <div className="text-[10px] font-bold text-zinc-500 tracking-widest mb-2">WHAT'S HERE NOW</div>
            <p className="text-[12px] text-zinc-400 leading-relaxed">
              Two problem formats. <span className="text-zinc-300 font-semibold">Sandbox problems</span> are
              short, one concept at a time, solved in minutes, free-form or from the library below.{' '}
              <span className="text-zinc-300 font-semibold">Guided modules</span> are a longer structured
              track with requirements, a design loop, and a reviewed final submission. Module 01 is the
              first sample of that format.
            </p>
          </div>

          <WaitlistBox />
          <FeedbackBox />
          <BugReportBox />
        </div>
      </div>
    </div>
  )
}

// ── main ──────────────────────────────────────────────────────────────────────

export default function ProblemLibrary({ onGoToModule }) {
  const { problems, setProblems, setCurrentProblem, participantId, sessionId, solvedProblems } = useStore()
  const [hovered, setHovered]     = useState(null)
  const [coords, setCoords]       = useState(null)
  const [loadingCoords, setLoadingCoords] = useState(false)
  const [missionOpen, setMissionOpen] = useState(false)
  const missionAutoQueued = useRef(false)

  function closeMission() {
    try { localStorage.setItem('al_mission_seen', '1') } catch {}
    setMissionOpen(false)
  }

  // First-ever visit: let the airfoil visual land and hold its "wow" moment
  // for a beat before the popup covers it, instead of opening immediately.
  useEffect(() => {
    if (missionAutoQueued.current) return
    if (!coords || loadingCoords) return
    let seen = true
    try { seen = !!localStorage.getItem('al_mission_seen') } catch { /* private mode */ }
    if (seen) return
    missionAutoQueued.current = true
    const t = setTimeout(() => setMissionOpen(true), 3000)
    return () => clearTimeout(t)
  }, [coords, loadingCoords])

  useEffect(() => {
    if (problems.length === 0) {
      axios.get(`${API_URL}/flowsense/problems`)
        .then(res => {
          const ps = res.data.problems
          setProblems(ps)
          setHovered(ps[0])
        })
        .catch(err => console.error('Failed to load problems:', err))
    } else if (!hovered) {
      setHovered(problems[0])
    }
  }, [])

  useEffect(() => {
    if (!hovered) return
    setLoadingCoords(true)
    const airfoil = hovered.starting_airfoil.replace('naca', '')
    axios.post(`${API_URL}/simulate/single`, {
      airfoil,
      alpha: hovered.design_alpha ?? 4,
      reynolds: hovered.Re,
      mach: hovered.mach ?? 0,
    })
      .then(res => setCoords(res.data.coordinates))
      .catch(() => setCoords(null))
      .finally(() => setLoadingCoords(false))
  }, [hovered?.id])

  function handleSelect(problem) {
    axios.post(`${API_URL}/flowsense/session/start`, {
      problem_id: problem.id,
      session_id: sessionId,
      participant_id: participantId,
    }).catch(err => console.error('session/start failed:', err))
    setCurrentProblem(problem)
  }

  const criteria = hovered?.success_criteria || {}

  return (
    <div className="flex h-full overflow-hidden">
      {missionOpen && <MissionModal onClose={closeMission} />}

      {/* ── Left: 3D preview panel — hidden on mobile ── */}
      <div className="hidden md:flex w-1/2 bg-zinc-950 flex-col border-r border-zinc-800 relative">

        {/* Mission trigger */}
        <button
          onClick={() => setMissionOpen(true)}
          className="absolute top-4 left-4 z-10 flex items-center gap-1.5 bg-zinc-900/90 hover:bg-zinc-800 border border-blue-500/40 text-blue-400 text-[10px] font-bold tracking-widest px-3 py-1.5 rounded-lg backdrop-blur-sm transition-colors"
        >
          ✦ OUR MISSION
        </button>

        {/* 3D canvas */}
        <div className="flex-1">
          {coords ? (
            <Canvas>
              <PerspectiveCamera makeDefault position={[0, 0, 9]} />
              <OrbitControls enablePan={false} enableZoom autoRotate autoRotateSpeed={0.6} />
              <ambientLight intensity={0.5} />
              <directionalLight position={[10, 10, 5]} intensity={1} />
              <directionalLight position={[-10, -10, -5]} intensity={0.4} />
              <AirfoilMesh coordinates={coords} />
              <gridHelper args={[12, 12, '#27272a', '#18181b']} />
            </Canvas>
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <div className="text-zinc-700 text-xs tracking-widest">
                {loadingCoords ? 'LOADING AIRFOIL…' : 'HOVER A PROBLEM'}
              </div>
            </div>
          )}
        </div>

        {/* Problem info overlay */}
        {hovered && (
          <div className="absolute bottom-0 left-0 right-0 bg-zinc-950/90 border-t border-zinc-800 px-6 py-4 backdrop-blur-sm">
            <div className="text-xs text-blue-400 tracking-widest mb-1 font-bold">
              {hovered.starting_airfoil.toUpperCase()} · Re {hovered.Re.toLocaleString()} · Mach {hovered.mach}
            </div>
            <div className="text-sm font-semibold text-zinc-100 mb-3">{hovered.title}</div>
            <div className="flex flex-col gap-1.5">
              <div className="text-xs text-zinc-600 tracking-widest mb-0.5">CURRENT → TARGET</div>
              {'target_LD' in criteria && (
                <MetricRow label="L/D" current="failing" target={`> ${criteria.target_LD}`} passing={false} />
              )}
              {'cruise_CL_min' in criteria && (
                <MetricRow label="CL" current="failing" target={`> ${criteria.cruise_CL_min}`} passing={false} />
              )}
              {'stall_angle_improvement' in criteria && (
                <MetricRow label="Stall" current="abrupt" target={`+${criteria.stall_angle_improvement}° softer`} passing={false} />
              )}
              {'cd_spike_ratio' in criteria && (
                <MetricRow label="CD" current="attached" target={`≥ ${criteria.cd_spike_ratio}× baseline`} passing={false} />
              )}
            </div>
            {hovered.assumes_you_know && (
              <div className="text-[11px] text-zinc-500 mt-3 pt-3 border-t border-zinc-800">
                <span className="text-zinc-600">Assumes you know:</span> {hovered.assumes_you_know}
              </div>
            )}
            {hovered.further_reading && (
              <a href={hovered.further_reading} target="_blank" rel="noreferrer" className="block text-[11px] text-blue-500 hover:text-blue-400 mt-2 underline underline-offset-2">
                Further reading →
              </a>
            )}
          </div>
        )}
      </div>

      {/* ── Right panel ── */}
      <div className="w-full md:w-1/2 flex flex-col bg-zinc-950 overflow-hidden">

        {/* Header */}
        <header className="border-b border-zinc-800/60 px-6 py-3 flex items-center gap-3 shrink-0">
          <div className="w-4 h-4 bg-blue-500 rotate-45 rounded-sm" />
          <span className="text-[11px] font-bold tracking-widest text-zinc-100">AIRFOILLEARNER</span>
          <span className="text-zinc-700 text-[11px]">·</span>
          <span className="text-[11px] text-zinc-500 tracking-widest">SANDBOX</span>
          {/* Left panel (and its mission trigger) is desktop-only — give mobile a way in too */}
          <button
            onClick={() => setMissionOpen(true)}
            className="md:hidden ml-auto flex items-center gap-1 text-blue-400 text-[10px] font-bold tracking-widest px-2.5 py-1 border border-blue-500/40 rounded-lg"
          >
            ✦ MISSION
          </button>
        </header>

        {/* ── Mission list, sandbox-forward: no gate, no click-through ── */}
        <div className="flex-1 overflow-y-auto px-5 py-5">
          <div className="mb-5">
            <h1 className="text-base font-bold text-zinc-100 leading-snug mb-3">
              Practise aerodynamic design, not just read about it.
            </h1>

            <p className="text-[12px] text-zinc-500 leading-relaxed">
              Run experiments on airfoil geometries and get results in seconds instead of solver-hours,
              so you can iterate, fail fast, and build design intuition. Pick any problem below to start free-form,
              or use Module 01 for a structured track.
            </p>
            <p className="text-[11px] text-zinc-600 mt-2">
              Airfoil problems for now. Fundamentals live in textbooks:{' '}
              <a href="https://github.com/barbagroup/CFDPython" target="_blank" rel="noreferrer" className="text-blue-500 hover:text-blue-400 underline underline-offset-2">
                we'll point you at the good ones
              </a>.
            </p>
          </div>

          <p className="text-[10px] text-zinc-600 tracking-widest mb-4">SELECT A PROBLEM TO BEGIN</p>

            <div className="flex flex-col gap-2.5">
              {/* Module 01 */}
              {onGoToModule && (
                <button
                  onClick={onGoToModule}
                  className="text-left rounded-lg p-4 border border-blue-500/50 bg-blue-950/25 hover:border-blue-400 hover:bg-blue-950/35 transition-all duration-150 group relative overflow-hidden"
                >
                  <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-blue-500" />
                  <div className="flex items-center justify-between mb-2 pl-2">
                    <span className="text-[10px] text-blue-400 tracking-widest font-bold font-mono">MODULE 01 · GUIDED TRACK</span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded border tracking-widest text-blue-300 border-blue-400/40 bg-blue-400/10">LONG FORM</span>
                  </div>
                  <div className="text-sm font-semibold text-zinc-100 mb-1.5 pl-2 group-hover:text-blue-200 transition-colors">
                    SPARROW-7 Wing Redesign
                  </div>
                  <div className="text-[12px] text-zinc-500 leading-relaxed mb-3 pl-2">
                    A structured design loop that builds intuition for camber, Reynolds number, and the CL/CD tradeoff before tackling open-ended problems.
                  </div>
                  <div className="flex items-center justify-between pt-2.5 border-t border-blue-900/40 pl-2">
                    <div className="flex gap-3 text-[11px] text-zinc-600 font-mono">
                      <span>NACA 2412</span><span>Re 5×10⁵</span>
                    </div>
                    <span className="text-[11px] font-bold tracking-widest text-blue-400 group-hover:translate-x-1 transition-transform">
                      START MODULE →
                    </span>
                  </div>
                </button>
              )}

              {problems.map(problem => (
                <button
                  key={problem.id}
                  onMouseEnter={() => setHovered(problem)}
                  onClick={() => handleSelect(problem)}
                  className={`text-left rounded-lg p-4 border transition-all duration-150 group relative overflow-hidden ${
                    hovered?.id === problem.id
                      ? 'border-blue-500/50 bg-zinc-800/60'
                      : 'border-zinc-800 bg-zinc-900/60 hover:border-zinc-700 hover:bg-zinc-800/40'
                  }`}
                >
                  <div className={`absolute left-0 top-0 bottom-0 w-0.5 transition-all duration-150 ${
                    hovered?.id === problem.id ? 'bg-blue-500/80' : 'bg-transparent'
                  }`} />
                  <div className="flex items-center justify-between mb-2 pl-2">
                    <span className="text-[10px] text-zinc-600 tracking-widest font-mono">
                      {problem.role} · <span className="text-zinc-700">{problem.sender}</span>
                    </span>
                    <div className="flex items-center gap-2">
                      {solvedProblems.has(problem.id) && (
                        <span className="text-[10px] font-bold text-green-400 tracking-widest">✓ SOLVED</span>
                      )}
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded border tracking-widest ${DIFFICULTY_STYLES[problem.difficulty]}`}>
                        {problem.difficulty.toUpperCase()}
                      </span>
                    </div>
                  </div>
                  <div className={`text-sm font-semibold mb-1.5 pl-2 transition-colors ${
                    hovered?.id === problem.id ? 'text-blue-200' : 'text-zinc-100'
                  }`}>
                    {problem.title}
                  </div>
                  <div className="text-[12px] text-zinc-500 leading-relaxed mb-2 pl-2 line-clamp-2">
                    {problem.bottleneck.split('\n')[0]}
                  </div>
                  {(problem.concept_tags?.length > 0) && (
                    <div className="flex gap-1.5 flex-wrap mb-2 pl-2">
                      {problem.concept_tags.map(t => (
                        <span key={t} className="text-[9px] font-mono text-zinc-500 border border-zinc-700 rounded px-1.5 py-0.5">
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                  {problem.assumes_you_know && (
                    <div className="text-[10px] text-zinc-600 italic mb-2 pl-2">
                      Assumes you know: {problem.assumes_you_know}
                    </div>
                  )}
                  <div className="flex items-center justify-between pt-2 border-t border-zinc-800 pl-2">
                    <div className="flex gap-3 text-[11px] text-zinc-600 font-mono">
                      <span>{problem.starting_airfoil.toUpperCase()}</span>
                      <span>Re {(problem.Re / 1e6).toFixed(1)}M</span>
                      <span>α {problem.design_alpha}°</span>
                    </div>
                    <span className={`text-[11px] font-bold tracking-widest transition-transform group-hover:translate-x-1 ${
                      hovered?.id === problem.id ? 'text-blue-400' : 'text-zinc-600'
                    }`}>
                      START →
                    </span>
                  </div>
                </button>
              ))}
            </div>
        </div>
      </div>
    </div>
  )
}
