import { useState } from 'react'
import axios from 'axios'
import useStore from '../../store/useStore'

const API = import.meta.env.VITE_API_URL || '/api/v1'

// ── small helpers ─────────────────────────────────────────────────────────────

function Label({ children }) {
  return <div className="text-xs text-zinc-400 tracking-widest mb-1">{children}</div>
}

function NumInput({ label, value, onChange, min, max, step = 1, unit = '' }) {
  return (
    <div className="flex flex-col gap-1">
      <Label>{label}</Label>
      <div className="flex items-center gap-2">
        <input
          type="number" value={value} min={min} max={max} step={step}
          onChange={e => onChange(Number(e.target.value))}
          className="bg-zinc-800 border border-zinc-700 text-zinc-100 rounded px-2 py-1.5 text-sm w-28 outline-none focus:border-blue-500"
        />
        {unit && <span className="text-xs text-zinc-500">{unit}</span>}
      </div>
    </div>
  )
}

function Toggle({ label, checked, onChange }) {
  return (
    <label className="flex items-center gap-2 cursor-pointer select-none">
      <div
        onClick={() => onChange(!checked)}
        className={`w-8 h-4 rounded-full transition-colors relative ${checked ? 'bg-blue-600' : 'bg-zinc-700'}`}
      >
        <div className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform ${checked ? 'left-4.5 translate-x-0.5' : 'left-0.5'}`} />
      </div>
      <span className="text-xs text-zinc-300">{label}</span>
    </label>
  )
}

// ── distribution bar ──────────────────────────────────────────────────────────

function DistBar({ label, dist, target, color }) {
  if (!dist) return null
  const lo = dist.p10, hi = dist.p90, mid = dist.p50
  const range = hi - lo || 1
  const pct = v => Math.max(0, Math.min(100, ((v - lo) / range) * 100))

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex justify-between text-xs">
        <span className="text-zinc-400 tracking-widest">{label}</span>
        <span className="text-zinc-500">
          {dist.p10.toFixed(3)} <span className="text-zinc-600">—</span>{' '}
          <span style={{ color }} className="font-bold">{dist.p50.toFixed(3)}</span>{' '}
          <span className="text-zinc-600">—</span> {dist.p90.toFixed(3)}
        </span>
      </div>

      {/* bar */}
      <div className="relative h-5 bg-zinc-800 rounded overflow-hidden">
        {/* P25–P75 fill */}
        <div
          className="absolute h-full rounded opacity-40"
          style={{
            left: `${pct(dist.p25)}%`,
            width: `${pct(dist.p75) - pct(dist.p25)}%`,
            background: color,
          }}
        />
        {/* P10–P90 outline */}
        <div
          className="absolute h-full border-x-2 rounded"
          style={{
            left: `${pct(lo)}%`,
            width: `${pct(hi) - pct(lo)}%`,
            borderColor: color,
          }}
        />
        {/* median tick */}
        <div
          className="absolute top-0 h-full w-0.5"
          style={{ left: `${pct(mid)}%`, background: color }}
        />
        {/* target line */}
        {target != null && (
          <div
            className="absolute top-0 h-full w-0.5 bg-amber-400"
            style={{ left: `${pct(target)}%` }}
          />
        )}
      </div>

      <div className="flex justify-between text-xs text-zinc-600">
        <span>P10</span>
        <span className="text-amber-500 text-xs">{target != null ? `target: ${target}` : ''}</span>
        <span>P90</span>
      </div>
    </div>
  )
}

// ── sensitivity bars ──────────────────────────────────────────────────────────

function SensBar({ label, value }) {
  return (
    <div className="flex items-center gap-3">
      <div className="w-16 text-xs text-zinc-400 text-right capitalize">{label}</div>
      <div className="flex-1 bg-zinc-800 rounded h-3 overflow-hidden">
        <div
          className="h-full bg-purple-500 rounded"
          style={{ width: `${value}%` }}
        />
      </div>
      <div className="w-10 text-xs text-zinc-300 font-mono">{value.toFixed(1)}%</div>
    </div>
  )
}

// ── main component ────────────────────────────────────────────────────────────

export default function MonteCarloMode() {
  const { sessionId, participantId, currentProblem, addResult, incrementStats } = useStore()

  const criteria = currentProblem?.success_criteria || {}

  const [airfoil, setAirfoil] = useState(
    currentProblem?.starting_airfoil?.replace('naca', '') || '2412'
  )
  const [alpha, setAlpha]       = useState(currentProblem?.design_alpha ?? 4)
  const [reynolds, setReynolds] = useState(currentProblem?.Re ?? 1_000_000)
  const [mach, setMach]         = useState(currentProblem?.mach ?? 0.0)
  const [nSamples, setNSamples] = useState(300)
  const [pertPct, setPertPct]   = useState(1.0)
  const [pertCamber, setPertCamber]       = useState(true)
  const [pertThickness, setPertThickness] = useState(true)
  const [pertAlpha, setPertAlpha]         = useState(false)
  const [alphaStd, setAlphaStd] = useState(0.5)

  const [loading, setLoading] = useState(false)
  const [result, setResult]   = useState(null)
  const [error, setError]     = useState('')

  async function run() {
    if (!airfoil || airfoil.length !== 4) {
      setError('Enter a valid 4-digit NACA code'); return
    }
    setError(''); setLoading(true); setResult(null)
    try {
      const res = await axios.post(`${API}/simulate/montecarlo`, {
        airfoil,
        alpha,
        reynolds,
        mach,
        n_samples: nSamples,
        perturbation_pct: pertPct,
        perturb_camber: pertCamber,
        perturb_thickness: pertThickness,
        perturb_alpha: pertAlpha,
        alpha_std: alphaStd,
        session_id: sessionId,
        participant_id: participantId,
      })
      setResult(res.data)
      incrementStats(res.data.n_samples || nSamples)
      res.data.high_value_experiments?.forEach(e =>
        addResult({ airfoil: e.airfoil, alpha, reynolds, CL: e.CL, CD: e.CD, L_D: e.L_D })
      )
    } catch (e) {
      setError(e.response?.data?.detail || 'Simulation failed')
    }
    setLoading(false)
  }

  const dist = result?.distributions
  const sens = result?.sensitivity
  const hvx  = result?.high_value_experiments || []

  return (
    <div className="p-5 flex flex-col gap-5 h-full overflow-y-auto">
      <div className="text-xs text-zinc-500 tracking-widest">MONTE CARLO UNCERTAINTY</div>

      {/* ── inputs ── */}
      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-1">
          <Label>NACA 4-DIGIT</Label>
          <input
            value={airfoil}
            onChange={e => setAirfoil(e.target.value.replace(/\D/g, '').slice(0, 4))}
            maxLength={4} placeholder="e.g. 2412"
            className="bg-zinc-800 border border-zinc-700 text-zinc-100 font-mono text-sm rounded px-2 py-1.5 w-24 outline-none focus:border-blue-500"
          />
        </div>
        <NumInput label="AoA °" value={alpha} onChange={setAlpha} min={-10} max={20} step={0.5} />
        <NumInput label="REYNOLDS" value={reynolds} onChange={setReynolds} min={10000} max={10000000} step={50000} />
        <NumInput label="MACH" value={mach} onChange={setMach} min={0} max={0.8} step={0.01} />
      </div>

      {/* ── MC parameters ── */}
      <div className="border border-zinc-800 rounded-lg p-4 flex flex-col gap-3">
        <div className="text-xs text-zinc-500 tracking-widest">SIMULATION PARAMETERS</div>

        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1">
            <div className="flex justify-between text-xs text-zinc-400">
              <span>SAMPLES</span>
              <span className="text-blue-400 font-bold">{nSamples}</span>
            </div>
            <input type="range" min={50} max={2000} step={50} value={nSamples}
              onChange={e => setNSamples(Number(e.target.value))}
              className="accent-blue-500 w-full" />
            <div className="flex justify-between text-xs text-zinc-600"><span>50</span><span>2000</span></div>
          </div>

          <div className="flex flex-col gap-1">
            <div className="flex justify-between text-xs text-zinc-400">
              <span>PERTURBATION</span>
              <span className="text-blue-400 font-bold">{pertPct.toFixed(1)}% σ</span>
            </div>
            <input type="range" min={0.1} max={5} step={0.1} value={pertPct}
              onChange={e => setPertPct(Number(e.target.value))}
              className="accent-blue-500 w-full" />
            <div className="flex justify-between text-xs text-zinc-600"><span>0.1%</span><span>5%</span></div>
          </div>
        </div>

        <div className="flex flex-col gap-2 pt-1">
          <Label>PERTURB PARAMETERS</Label>
          <Toggle label="Camber"    checked={pertCamber}    onChange={setPertCamber} />
          <Toggle label="Thickness" checked={pertThickness} onChange={setPertThickness} />
          <Toggle label="Angle of Attack" checked={pertAlpha} onChange={setPertAlpha} />
          {pertAlpha && (
            <NumInput label="AoA STD DEV" value={alphaStd} onChange={setAlphaStd}
              min={0.1} max={5} step={0.1} unit="°" />
          )}
        </div>
      </div>

      <button
        onClick={run} disabled={loading}
        className="bg-purple-600 hover:bg-purple-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-white text-xs font-bold tracking-widest py-2.5 rounded-lg transition-colors"
      >
        {loading ? `RUNNING ${nSamples} SAMPLES…` : `RUN MONTE CARLO →`}
      </button>

      {error && <div className="text-red-400 text-xs">{error}</div>}

      {/* ── results ── */}
      {result && (
        <div className="flex flex-col gap-5">
          <div className="text-xs text-zinc-500">
            NACA {result.airfoil} · {result.n_samples} samples · {result.time_ms}ms
          </div>

          {/* distributions */}
          <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-4 flex flex-col gap-4">
            <div className="text-xs text-zinc-500 tracking-widest">UNCERTAINTY DISTRIBUTIONS</div>
            <DistBar
              label="CL" dist={dist.CL}
              target={criteria.cruise_CL_min ?? null}
              color="#3b82f6"
            />
            <DistBar
              label="L/D" dist={dist.L_D}
              target={criteria.target_LD ?? null}
              color="#10b981"
            />
            <div className="text-xs text-zinc-600 leading-relaxed pt-1">
              Bar = P10–P90 · Shaded = P25–P75 · Line = median · Amber = target
            </div>
          </div>

          {/* sensitivity */}
          {sens && Object.keys(sens).length > 0 && (
            <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-4 flex flex-col gap-3">
              <div className="text-xs text-zinc-500 tracking-widest">SENSITIVITY (% variance explained)</div>
              {Object.entries(sens)
                .sort((a, b) => b[1] - a[1])
                .map(([k, v]) => <SensBar key={k} label={k} value={v} />)}
              <div className="text-xs text-zinc-600 pt-1">
                Higher = changing this parameter has more impact on L/D.
              </div>
            </div>
          )}

          {/* high-value experiments */}
          {hvx.length > 0 && (
            <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-4 flex flex-col gap-3">
              <div className="text-xs text-zinc-500 tracking-widest">HIGH-VALUE NEXT EXPERIMENTS</div>
              <div className="text-xs text-zinc-500 mb-1">
                Nearby unexplored geometries ranked by predicted L/D.
              </div>
              {hvx.map((e, i) => (
                <div key={i}
                  className="flex items-center justify-between border border-zinc-700 rounded px-3 py-2 bg-zinc-900/40">
                  <span className="text-zinc-600 text-xs w-4">{i + 1}</span>
                  <span className="text-blue-400 font-mono font-bold text-sm w-14">
                    NACA {e.airfoil}
                  </span>
                  <div className="flex gap-4 text-xs flex-1 justify-end">
                    <span className="text-emerald-400 font-bold">L/D {e.L_D}</span>
                    <span className="text-zinc-400">CL {e.CL?.toFixed(4)}</span>
                    <span className="text-zinc-500">CD {e.CD?.toFixed(5)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
