import { useEffect, useState } from 'react'
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

// ── main ──────────────────────────────────────────────────────────────────────

export default function ProblemLibrary({ onGoToModule }) {
  const { problems, setProblems, setCurrentProblem, participantId, sessionId, solvedProblems } = useStore()
  const [hovered, setHovered]     = useState(null)
  const [coords, setCoords]       = useState(null)
  const [loadingCoords, setLoadingCoords] = useState(false)
  const [briefAccepted, setBriefAccepted] = useState(false)

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

      {/* ── Left: CFD panel — hidden on mobile ── */}
      <div className="hidden md:flex w-1/2 bg-zinc-950 flex-col border-r border-zinc-800 relative">

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
            </div>
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
          <span className="text-[11px] text-zinc-500 tracking-widest">
            {briefAccepted ? 'MISSION SELECT' : 'INCOMING BRIEF'}
          </span>
        </header>

        {!briefAccepted ? (
          /* ── STATE 1: Project brief only ── */
          <div className="flex-1 overflow-y-auto flex flex-col">
            {/* Classification strip */}
            <div className="flex justify-between px-6 py-1.5 bg-orange-950/20 border-b border-orange-500/15 shrink-0">
              <span className="text-[9px] font-mono tracking-[0.16em] text-orange-500">ENGINEERING USE ONLY</span>
              <span className="text-[9px] font-mono tracking-[0.12em] text-orange-900">REF: AE-2026-0047</span>
            </div>

            {/* From / To / Date */}
            <div className="px-6 py-4 flex flex-col gap-1.5 border-b border-zinc-800/50 shrink-0">
              {[
                ['FROM', 'Flight Test Directorate · Sparrow-7 Program', 'text-zinc-500'],
                ['TO',   'Wing Design Engineer', 'text-zinc-200'],
                ['DATE', '2026-08-31 · 14:03 UTC', 'text-zinc-600'],
              ].map(([label, val, col]) => (
                <div key={label} className="flex gap-3 items-baseline">
                  <span className="font-mono text-[9px] tracking-[0.12em] text-zinc-700 w-9">{label}</span>
                  <span className={`font-mono text-[10px] ${col}`}>{val}</span>
                </div>
              ))}
            </div>

            {/* Headline + body */}
            <div className="px-6 py-6 flex-1">
              <div className="flex items-center gap-2 mb-4">
                <span className="font-mono text-[9px] font-bold tracking-[0.16em] text-orange-500 border border-orange-500/35 bg-orange-500/8 px-2 py-0.5 rounded-[2px]">HIGH PRIORITY</span>
                <span className="font-mono text-[9px] tracking-[0.10em] text-zinc-700">WING SECTION REPLACEMENT</span>
              </div>

              <h2 className="font-mono text-xl font-bold text-zinc-100 leading-snug mb-5">
                Current wing is failing the<br />endurance target by 23%.
              </h2>

              <p className="text-[13px] text-zinc-400 leading-relaxed mb-6">
                NACA 2412 baseline delivers CL&nbsp;=&nbsp;0.63 at cruise — 23% short of the
                CL&nbsp;≥&nbsp;0.80 requirement at Re&nbsp;500,000. The Sparrow-7 program cannot
                meet its endurance target at current wing loading. We need a replacement
                section that closes the lift gap without exceeding the drag budget.
              </p>

              <p className="text-[13px] text-zinc-500 leading-relaxed mb-8">
                Your role is to identify a candidate airfoil and justify the choice
                through simulation. Use the tools on the left to explore the design
                space — the AI tutor will guide you through the tradeoffs.
              </p>

              {/* Metrics */}
              <div className="flex border border-zinc-800 rounded-lg overflow-hidden mb-8">
                {[
                  { label: 'CL REQUIRED', val: '≥ 0.80', hot: true },
                  { label: 'CD BUDGET',   val: '≤ 0.015', hot: false },
                  { label: 'REYNOLDS No.', val: '500,000', hot: false },
                ].map((m, i) => (
                  <div key={m.label} className={`flex-1 px-4 py-3 ${i < 2 ? 'border-r border-zinc-800' : ''}`}>
                    <div className="font-mono text-[8px] tracking-[0.14em] text-zinc-700 mb-1.5">{m.label}</div>
                    <div className={`font-mono text-base font-bold tabular-nums ${m.hot ? 'text-orange-500' : 'text-blue-400'}`}>{m.val}</div>
                  </div>
                ))}
              </div>

              <button
                onClick={() => setBriefAccepted(true)}
                className="w-full bg-blue-600 hover:bg-blue-500 text-white font-mono text-[11px] font-bold tracking-[0.15em] py-3.5 rounded-lg transition-colors"
              >
                ACCEPT BRIEF — SELECT A MISSION →
              </button>
            </div>
          </div>
        ) : (
          /* ── STATE 2: Mission list ── */
          <div className="flex-1 overflow-y-auto px-5 py-5">
            <p className="text-[10px] text-zinc-600 tracking-widest mb-4">SELECT A MISSION TO BEGIN</p>

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
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded border tracking-widest text-blue-300 border-blue-400/40 bg-blue-400/10">STARTER</span>
                  </div>
                  <div className="text-sm font-semibold text-zinc-100 mb-1.5 pl-2 group-hover:text-blue-200 transition-colors">
                    SPARROW-7 Wing Redesign
                  </div>
                  <div className="text-[12px] text-zinc-500 leading-relaxed mb-3 pl-2">
                    A structured design loop — build intuition for camber, Reynolds number, and the CL/CD tradeoff before tackling open-ended problems.
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
                  <div className="text-[12px] text-zinc-500 leading-relaxed mb-3 pl-2 line-clamp-2">
                    {problem.bottleneck.split('\n')[0]}
                  </div>
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
        )}
      </div>
    </div>
  )
}
