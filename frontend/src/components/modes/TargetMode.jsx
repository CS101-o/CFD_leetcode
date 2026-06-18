import { useState } from 'react'
import axios from 'axios'
import useStore from '../../store/useStore'

const API = import.meta.env.VITE_API_URL || '/api/v1'

function ResultRow({ r, rank }) {
  const bothMet = r.meets_LD && r.meets_CL
  return (
    <div className={`flex items-center gap-3 border rounded-lg px-3 py-2 ${bothMet ? 'border-green-500/40 bg-green-900/10' : 'border-zinc-800 bg-zinc-800/30'}`}>
      <span className="text-zinc-600 text-xs w-4">{rank}</span>
      <span className="text-blue-400 font-mono font-bold text-sm w-12">NACA {r.airfoil}</span>
      <div className="flex gap-3 flex-1 text-xs">
        <span className={r.meets_LD ? 'text-green-400' : 'text-zinc-400'}>
          L/D <span className="font-bold">{r.L_D}</span>
        </span>
        <span className={r.meets_CL ? 'text-green-400' : 'text-zinc-400'}>
          CL <span className="font-bold">{r.CL?.toFixed(4)}</span>
        </span>
        <span className="text-zinc-500">CD {r.CD?.toFixed(5)}</span>
      </div>
      {bothMet && <span className="text-green-400 text-xs font-bold">✓ MEETS TARGETS</span>}
    </div>
  )
}

export default function TargetMode() {
  const { sessionId, participantId, addResult, incrementStats, currentProblem } = useStore()

  const [targetLD, setTargetLD] = useState(currentProblem?.success_criteria?.target_LD ?? '')
  const [targetCL, setTargetCL] = useState(currentProblem?.success_criteria?.cruise_CL_min ?? '')
  const [alpha, setAlpha] = useState(currentProblem?.design_alpha ?? 4)
  const [reynolds, setReynolds] = useState(currentProblem?.Re ?? 1_000_000)
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)

  async function search() {
    setLoading(true)
    try {
      const res = await axios.post(`${API}/simulate/target`, {
        target_LD: targetLD !== '' ? Number(targetLD) : null,
        target_CL: targetCL !== '' ? Number(targetCL) : null,
        alpha: Number(alpha),
        reynolds: Number(reynolds),
        session_id: sessionId,
        participant_id: participantId,
      })
      setResults(res.data.results)
      res.data.results.forEach(r => {
        addResult({ ...r, alpha: Number(alpha), reynolds: Number(reynolds) })
        incrementStats(1)
      })
    } catch {
      // silent
    }
    setLoading(false)
  }

  const solved = results?.filter(r => r.meets_LD && r.meets_CL) || []

  return (
    <div className="p-5 flex flex-col gap-4 h-full overflow-y-auto">
      <div className="text-xs text-zinc-500 tracking-widest">TARGET SEARCH</div>
      <p className="text-xs text-zinc-500 leading-relaxed">
        Set your design targets. AirfoilLearner searches for airfoils that satisfy them.
      </p>

      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-zinc-400">TARGET L/D ≥</label>
          <input
            type="number" value={targetLD} onChange={e => setTargetLD(e.target.value)}
            placeholder="e.g. 90"
            className="bg-zinc-800 border border-zinc-700 text-zinc-100 rounded px-3 py-2 text-sm outline-none focus:border-blue-500"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-zinc-400">TARGET CL ≥</label>
          <input
            type="number" step="0.01" value={targetCL} onChange={e => setTargetCL(e.target.value)}
            placeholder="e.g. 0.6"
            className="bg-zinc-800 border border-zinc-700 text-zinc-100 rounded px-3 py-2 text-sm outline-none focus:border-blue-500"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-zinc-400">AT AoA°</label>
          <input
            type="number" value={alpha} step={0.5} onChange={e => setAlpha(e.target.value)}
            className="bg-zinc-800 border border-zinc-700 text-zinc-100 rounded px-3 py-2 text-sm outline-none focus:border-blue-500"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-zinc-400">REYNOLDS</label>
          <input
            type="number" value={reynolds} step={50000} onChange={e => setReynolds(e.target.value)}
            className="bg-zinc-800 border border-zinc-700 text-zinc-100 rounded px-3 py-2 text-sm outline-none focus:border-blue-500"
          />
        </div>
      </div>

      <button
        onClick={search}
        disabled={loading || (!targetLD && !targetCL)}
        className="bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-white text-xs font-bold tracking-widest py-2.5 rounded-lg transition-colors"
      >
        {loading ? 'SEARCHING…' : 'FIND BEST AIRFOIL →'}
      </button>

      {results && (
        <div className="flex flex-col gap-2">
          <div className="text-xs text-zinc-500 tracking-widest">
            {solved.length > 0
              ? <span className="text-green-400">{solved.length} AIRFOIL{solved.length > 1 ? 'S' : ''} MEET ALL TARGETS</span>
              : 'NO EXACT MATCH — CLOSEST RESULTS'}
          </div>
          {results.map((r, i) => <ResultRow key={i} r={r} rank={i + 1} />)}
        </div>
      )}
    </div>
  )
}
