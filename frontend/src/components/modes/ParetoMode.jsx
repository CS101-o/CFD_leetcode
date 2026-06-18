import { useMemo } from 'react'
import useStore from '../../store/useStore'

const W = 420
const H = 280
const PAD = { top: 20, right: 20, bottom: 40, left: 50 }

function scaleX(val, min, max) {
  return PAD.left + ((val - min) / (max - min)) * (W - PAD.left - PAD.right)
}
function scaleY(val, min, max) {
  return H - PAD.bottom - ((val - min) / (max - min)) * (H - PAD.top - PAD.bottom)
}

function isParetoOptimal(points) {
  return points.map((p, i) => {
    const dominated = points.some(
      (q, j) => i !== j && q.L_D >= p.L_D && q.CL >= p.CL && (q.L_D > p.L_D || q.CL > p.CL)
    )
    return !dominated
  })
}

export default function ParetoMode() {
  const { allResults } = useStore()

  const points = useMemo(() =>
    allResults.filter(r => r.L_D != null && r.CL != null),
    [allResults]
  )

  const pareto = useMemo(() => isParetoOptimal(points), [points])

  if (points.length === 0) {
    return (
      <div className="p-5 flex flex-col gap-3">
        <div className="text-xs text-zinc-500 tracking-widest">PARETO EXPLORER</div>
        <div className="flex-1 flex items-center justify-center text-zinc-600 text-xs text-center py-16">
          Run simulations in Sliders or Table mode.<br />Results appear here automatically.
        </div>
      </div>
    )
  }

  const ldMin = Math.min(...points.map(p => p.L_D)) * 0.9
  const ldMax = Math.max(...points.map(p => p.L_D)) * 1.1
  const clMin = Math.min(...points.map(p => p.CL)) * 0.9
  const clMax = Math.max(...points.map(p => p.CL)) * 1.1

  return (
    <div className="p-5 flex flex-col gap-3 h-full overflow-y-auto">
      <div className="text-xs text-zinc-500 tracking-widest">PARETO EXPLORER — L/D vs CL</div>
      <div className="text-xs text-zinc-600">{points.length} design{points.length !== 1 ? 's' : ''} · blue = Pareto optimal</div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
        <svg width="100%" viewBox={`0 0 ${W} ${H}`} className="block">
          {/* Grid lines */}
          {[0.25, 0.5, 0.75].map(t => (
            <g key={t}>
              <line
                x1={PAD.left} y1={PAD.top + t * (H - PAD.top - PAD.bottom)}
                x2={W - PAD.right} y2={PAD.top + t * (H - PAD.top - PAD.bottom)}
                stroke="#27272a" strokeWidth="1"
              />
              <line
                x1={PAD.left + t * (W - PAD.left - PAD.right)} y1={PAD.top}
                x2={PAD.left + t * (W - PAD.left - PAD.right)} y2={H - PAD.bottom}
                stroke="#27272a" strokeWidth="1"
              />
            </g>
          ))}

          {/* Axis labels */}
          <text x={W / 2} y={H - 6} textAnchor="middle" fill="#52525b" fontSize="10">L/D</text>
          <text x={12} y={H / 2} textAnchor="middle" fill="#52525b" fontSize="10"
            transform={`rotate(-90, 12, ${H / 2})`}>CL</text>

          {/* Points */}
          {points.map((p, i) => {
            const cx = scaleX(p.L_D, ldMin, ldMax)
            const cy = scaleY(p.CL, clMin, clMax)
            const isOptimal = pareto[i]
            return (
              <g key={i}>
                <circle
                  cx={cx} cy={cy} r={isOptimal ? 6 : 4}
                  fill={isOptimal ? '#3b82f6' : '#52525b'}
                  fillOpacity={isOptimal ? 0.9 : 0.6}
                  stroke={isOptimal ? '#93c5fd' : 'none'}
                  strokeWidth="1"
                />
                {isOptimal && (
                  <text x={cx + 8} y={cy + 4} fill="#93c5fd" fontSize="9">{p.airfoil}</text>
                )}
              </g>
            )
          })}

          {/* Axis ticks */}
          {[ldMin, (ldMin + ldMax) / 2, ldMax].map((v, i) => (
            <text
              key={i}
              x={scaleX(v, ldMin, ldMax)} y={H - PAD.bottom + 14}
              textAnchor="middle" fill="#52525b" fontSize="9"
            >{v.toFixed(1)}</text>
          ))}
          {[clMin, (clMin + clMax) / 2, clMax].map((v, i) => (
            <text
              key={i}
              x={PAD.left - 6} y={scaleY(v, clMin, clMax) + 4}
              textAnchor="end" fill="#52525b" fontSize="9"
            >{v.toFixed(2)}</text>
          ))}
        </svg>
      </div>

      {/* Pareto table */}
      <div className="text-xs text-zinc-500 tracking-widest mt-1">PARETO FRONT</div>
      <div className="space-y-1">
        {points
          .filter((_, i) => pareto[i])
          .sort((a, b) => b.L_D - a.L_D)
          .map((p, i) => (
            <div key={i} className="flex justify-between bg-zinc-800/40 border border-zinc-800 rounded px-3 py-1.5">
              <span className="text-blue-400 font-mono font-bold">NACA {p.airfoil}</span>
              <span className="text-zinc-400">L/D <span className="text-zinc-100">{p.L_D}</span></span>
              <span className="text-zinc-400">CL <span className="text-zinc-100">{p.CL?.toFixed(4)}</span></span>
              <span className="text-zinc-400">α <span className="text-zinc-100">{p.alpha}°</span></span>
            </div>
          ))}
      </div>
    </div>
  )
}
