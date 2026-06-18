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

export default function ProblemLibrary() {
  const { problems, setProblems, setCurrentProblem, participantId, sessionId, solvedProblems } = useStore()
  const [hovered, setHovered]     = useState(null)
  const [coords, setCoords]       = useState(null)
  const [loadingCoords, setLoadingCoords] = useState(false)

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

      {/* ── Left: CFD panel ── */}
      <div className="w-1/2 bg-zinc-950 flex flex-col border-r border-zinc-800 relative">

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

      {/* ── Right: problem list ── */}
      <div className="w-1/2 flex flex-col bg-zinc-900 overflow-hidden">

        <header className="border-b border-zinc-800 px-6 py-4 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-5 h-5 bg-blue-500 rotate-45 rounded-sm" />
            <div>
              <h1 className="text-xs font-bold tracking-widest text-zinc-100">AIRFOILLEARNER</h1>
              <p className="text-xs text-zinc-600 tracking-widest">MISSION SELECT</p>
            </div>
          </div>
          <span className="text-xs text-zinc-700 tracking-widest">{participantId}</span>
        </header>

        <div className="border-b border-zinc-800 px-6 py-4 shrink-0">
          <p className="text-sm text-zinc-300 leading-relaxed mb-1">
            AirfoilLearner is a practice environment for aerodynamic design thinking.
          </p>
          <p className="text-sm text-zinc-500 leading-relaxed">
            Work through real engineering bottlenecks — simulate airfoils, reason about tradeoffs, and develop the intuition that bridges theory and design.
          </p>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-6">
          <p className="text-xs text-zinc-500 tracking-widest mb-5">SELECT A PROBLEM TO BEGIN</p>

          <div className="flex flex-col gap-3">
            {problems.map(problem => (
              <button
                key={problem.id}
                onMouseEnter={() => setHovered(problem)}
                onClick={() => handleSelect(problem)}
                className={`text-left rounded-lg p-4 border transition-all duration-150 group ${
                  hovered?.id === problem.id
                    ? 'border-blue-500/60 bg-zinc-800/80'
                    : 'border-zinc-800 bg-zinc-900 hover:border-zinc-700'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-zinc-500 tracking-widest">
                    {problem.role} · <span className="text-zinc-600">Brief from: {problem.sender}</span>
                  </span>
                  <div className="flex items-center gap-2">
                    {solvedProblems.has(problem.id) && (
                      <span className="text-xs font-bold text-green-400 tracking-widest">✓ SOLVED</span>
                    )}
                    <span className={`text-xs font-bold px-2 py-0.5 rounded border tracking-widest ${DIFFICULTY_STYLES[problem.difficulty]}`}>
                      {problem.difficulty.toUpperCase()}
                    </span>
                  </div>
                </div>

                <div className="text-sm font-semibold text-zinc-100 mb-2 group-hover:text-blue-300 transition-colors">
                  {problem.title}
                </div>

                <div className="text-sm text-zinc-500 leading-relaxed mb-3 line-clamp-2">
                  {problem.bottleneck.split('\n')[0]}
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-zinc-800">
                  <div className="flex gap-3 text-xs text-zinc-600">
                    <span>{problem.starting_airfoil.toUpperCase()}</span>
                    <span>Re {(problem.Re / 1e6).toFixed(1)}M</span>
                    <span>α {problem.design_alpha}°</span>
                  </div>
                  <span className={`text-xs font-bold tracking-widest transition-transform group-hover:translate-x-1 ${
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
