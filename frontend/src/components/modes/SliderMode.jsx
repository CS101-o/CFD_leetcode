import { useState } from 'react'
import axios from 'axios'
import useStore from '../../store/useStore'

const API = import.meta.env.VITE_API_URL || '/api/v1'

const RE_OPTIONS = [50000, 100000, 500000, 1000000, 1500000, 3000000]

function Stat({ label, value, highlight }) {
  return (
    <div className="flex flex-col items-center">
      <div className={`text-lg font-bold ${highlight ? 'text-blue-400' : 'text-zinc-100'}`}>
        {value ?? '—'}
      </div>
      <div className="text-xs text-zinc-500 tracking-widest">{label}</div>
    </div>
  )
}

export default function SliderMode() {
  const { sessionId, participantId, setResults, addResult, incrementStats, currentProblem } = useStore()

  const [airfoil, setAirfoil] = useState(
    currentProblem?.starting_airfoil?.replace('naca', '') || '2412'
  )
  const [alpha, setAlpha] = useState(currentProblem?.design_alpha ?? 4)
  const [reIdx, setReIdx] = useState(
    Math.max(0, RE_OPTIONS.indexOf(currentProblem?.Re ?? 500000))
  )
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  async function run() {
    const code = airfoil.replace(/\D/g, '').slice(0, 4).padEnd(4, '0')
    if (code.length !== 4) { setError('Enter a valid 4-digit NACA code'); return }
    setError('')
    setLoading(true)
    try {
      const res = await axios.post(`${API}/simulate/single`, {
        airfoil: code,
        alpha,
        reynolds: RE_OPTIONS[reIdx],
        mach: currentProblem?.mach ?? 0.0,
        session_id: sessionId,
        participant_id: participantId,
        mode: 'sliders',
      })
      setResult(res.data)
      setResults({ ...res.data, CL: res.data.CL, CD: res.data.CD, L_D: res.data.L_D, coordinates: res.data.coordinates })
      addResult({ airfoil: code, alpha, reynolds: RE_OPTIONS[reIdx], ...res.data })
      incrementStats(1)
    } catch {
      setError('Simulation failed. Check airfoil code.')
    }
    setLoading(false)
  }

  return (
    <div className="p-5 flex flex-col gap-5 h-full overflow-y-auto">
      <div className="text-xs text-zinc-500 tracking-widest">PARAMETER SLIDERS</div>

      {/* NACA input */}
      <div className="flex flex-col gap-1">
        <label className="text-xs text-zinc-400">NACA 4-DIGIT</label>
        <input
          value={airfoil}
          onChange={e => setAirfoil(e.target.value.replace(/\D/g, '').slice(0, 4))}
          placeholder="e.g. 2412"
          maxLength={4}
          className="bg-zinc-800 border border-zinc-700 text-zinc-100 font-mono text-sm rounded px-3 py-2 w-28 outline-none focus:border-blue-500"
        />
      </div>

      {/* AoA slider */}
      <div className="flex flex-col gap-2">
        <div className="flex justify-between text-xs text-zinc-400">
          <span>ANGLE OF ATTACK</span>
          <span className="text-blue-400 font-bold">{alpha}°</span>
        </div>
        <input
          type="range" min={-10} max={20} step={0.5} value={alpha}
          onChange={e => setAlpha(Number(e.target.value))}
          className="accent-blue-500 w-full"
        />
        <div className="flex justify-between text-xs text-zinc-600">
          <span>−10°</span><span>20°</span>
        </div>
      </div>

      {/* Reynolds */}
      <div className="flex flex-col gap-2">
        <div className="flex justify-between text-xs text-zinc-400">
          <span>REYNOLDS NUMBER</span>
          <span className="text-blue-400 font-bold">{(RE_OPTIONS[reIdx] / 1e6).toFixed(2)}×10⁶</span>
        </div>
        <input
          type="range" min={0} max={RE_OPTIONS.length - 1} step={1} value={reIdx}
          onChange={e => setReIdx(Number(e.target.value))}
          className="accent-blue-500 w-full"
        />
        <div className="flex justify-between text-xs text-zinc-600">
          <span>50k</span><span>3M</span>
        </div>
      </div>

      <button
        onClick={run}
        disabled={loading}
        className="bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-white text-xs font-bold tracking-widest py-2.5 rounded-lg transition-colors"
      >
        {loading ? 'COMPUTING…' : 'RUN SIMULATION →'}
      </button>

      {error && <div className="text-red-400 text-xs">{error}</div>}

      {result && (
        <div className="bg-zinc-800/60 border border-zinc-700 rounded-lg p-4">
          <div className="text-xs text-zinc-500 tracking-widest mb-3">RESULTS — NACA {result.airfoil}</div>
          <div className="grid grid-cols-3 gap-4">
            <Stat label="L/D" value={result.L_D} highlight />
            <Stat label="CL" value={result.CL?.toFixed(4)} />
            <Stat label="CD" value={result.CD?.toFixed(5)} />
          </div>
        </div>
      )}
    </div>
  )
}
