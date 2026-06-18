import React, { useMemo } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, PerspectiveCamera, Line } from '@react-three/drei'
import * as THREE from 'three'
import useStore from '../store/useStore'

// ── 3-D airfoil ──────────────────────────────────────────────────────────────

function Airfoil3D({ coordinates }) {
  const points = useMemo(() => {
    if (!coordinates?.length) return []
    const scale = 4
    return coordinates.map(([x, y]) =>
      new THREE.Vector3((x - 0.5) * scale, y * scale, 0)
    )
  }, [coordinates])

  if (!points.length) return null
  return (
    <group>
      <Line points={points} color="#3b82f6" lineWidth={3} />
      <mesh>
        <extrudeGeometry
          args={[
            new THREE.Shape(points.map(p => new THREE.Vector2(p.x, p.y))),
            { depth: 0.3, bevelEnabled: false },
          ]}
        />
        <meshStandardMaterial color="#3b82f6" metalness={0.3} roughness={0.4} />
      </mesh>
    </group>
  )
}

// ── SVG polar chart (one metric vs α) ────────────────────────────────────────

function PolarChart({ data, yKey, label, color, designAlpha }) {
  const W = 260, H = 130, PAD = { top: 12, right: 12, bottom: 28, left: 40 }
  const iW = W - PAD.left - PAD.right
  const iH = H - PAD.top - PAD.bottom

  const xs = data.map(d => d.alpha)
  const ys = data.map(d => d[yKey]).filter(v => v != null)
  const xMin = Math.min(...xs), xMax = Math.max(...xs)
  const yMin = Math.min(...ys), yMax = Math.max(...ys)
  const yPad = (yMax - yMin) * 0.08 || 1

  const sx = a => PAD.left + ((a - xMin) / (xMax - xMin || 1)) * iW
  const sy = v => PAD.top + (1 - (v - (yMin - yPad)) / ((yMax + yPad) - (yMin - yPad))) * iH

  const pts = data
    .filter(d => d[yKey] != null)
    .map(d => `${sx(d.alpha)},${sy(d[yKey])}`)
    .join(' ')

  const yTicks = 4
  const tickStep = ((yMax + yPad) - (yMin - yPad)) / yTicks

  return (
    <svg width={W} height={H} className="overflow-visible">
      {/* grid lines */}
      {Array.from({ length: yTicks + 1 }, (_, i) => {
        const v = (yMin - yPad) + i * tickStep
        const y = sy(v)
        return (
          <g key={i}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y} y2={y}
              stroke="#3f3f46" strokeWidth={0.5} />
            <text x={PAD.left - 4} y={y + 3.5} textAnchor="end"
              fontSize={8} fill="#71717a">{v.toFixed(1)}</text>
          </g>
        )
      })}

      {/* x axis ticks */}
      {xs.filter((_, i) => i % Math.ceil(xs.length / 5) === 0).map(a => (
        <g key={a}>
          <line x1={sx(a)} x2={sx(a)} y1={PAD.top} y2={H - PAD.bottom + 3}
            stroke="#3f3f46" strokeWidth={0.5} />
          <text x={sx(a)} y={H - PAD.bottom + 12} textAnchor="middle"
            fontSize={8} fill="#71717a">{a}°</text>
        </g>
      ))}

      {/* design alpha marker */}
      {designAlpha != null && (
        <line x1={sx(designAlpha)} x2={sx(designAlpha)}
          y1={PAD.top} y2={H - PAD.bottom}
          stroke="#f59e0b" strokeWidth={1} strokeDasharray="3,3" />
      )}

      {/* curve */}
      <polyline points={pts} fill="none" stroke={color} strokeWidth={2} />

      {/* axis labels */}
      <text x={W / 2} y={H} textAnchor="middle" fontSize={9} fill="#a1a1aa">α (°)</text>
      <text x={10} y={H / 2} textAnchor="middle" fontSize={9} fill="#a1a1aa"
        transform={`rotate(-90,10,${H / 2})`}>{label}</text>
    </svg>
  )
}

// ── main panel ───────────────────────────────────────────────────────────────

export default function LeftPanel() {
  const { results, polarData, currentProblem } = useStore()
  const designAlpha = currentProblem?.design_alpha ?? null
  const hasPolar = Array.isArray(polarData) && polarData.length > 0
  const hasCoords = results?.coordinates?.length > 0

  return (
    <div className="w-full h-full bg-zinc-950 flex flex-col relative overflow-hidden">

      {/* 3-D airfoil pane */}
      <div className="relative flex-1 shrink-0">
        {!hasCoords ? (
          <div className="w-full h-full flex items-center justify-center">
            <div className="text-center">
              <div className="text-5xl mb-3">✈</div>
              <p className="text-zinc-500 text-xs tracking-widest">RUN A SIMULATION TO SEE THE AIRFOIL</p>
            </div>
          </div>
        ) : (
          <Canvas>
            <PerspectiveCamera makeDefault position={[0, 0, 8]} />
            <OrbitControls enablePan enableZoom enableRotate />
            <ambientLight intensity={0.5} />
            <directionalLight position={[10, 10, 5]} intensity={1} />
            <directionalLight position={[-10, -10, -5]} intensity={0.5} />
            <Airfoil3D coordinates={results.coordinates} />
            <gridHelper args={[10, 10]} />
          </Canvas>
        )}

        {/* stats overlay */}
        {results && (
          <div className="absolute bottom-3 left-3 bg-zinc-900/90 px-3 py-2 rounded-lg space-y-0.5 pointer-events-none">
            <p className="text-xs text-zinc-500 font-semibold tracking-widest">
              {results.airfoil ? `NACA ${results.airfoil}` : 'RESULT'}
            </p>
            <p className="text-sm text-white">L/D <span className="text-blue-400 font-bold">{results.L_D?.toFixed(1)}</span></p>
            <p className="text-xs text-zinc-300">CL {results.CL?.toFixed(4)} · CD {results.CD?.toFixed(5)}</p>
          </div>
        )}

        <div className="absolute top-3 right-3 bg-zinc-900/70 px-2 py-1 rounded text-xs text-zinc-500">
          {hasCoords ? 'drag · scroll' : '3D VIZ'}
        </div>
      </div>

    </div>
  )
}
