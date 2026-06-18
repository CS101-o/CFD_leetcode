import { useState } from 'react'
import axios from 'axios'
import useStore from '../../store/useStore'

const API = import.meta.env.VITE_API_URL || '/api/v1'

const DEFAULT_ROW = (airfoil = '', alpha = 4, reynolds = 500000) => ({
  airfoil, alpha, reynolds, CL: null, CD: null, L_D: null, error: null
})

export default function TableMode() {
  const { sessionId, participantId, addResult, incrementStats, currentProblem } = useStore()
  const startAirfoil = currentProblem?.starting_airfoil?.replace('naca', '') || '2412'
  const defaultRe = currentProblem?.Re || 500000
  const defaultAlpha = currentProblem?.design_alpha ?? 4

  const [rows, setRows] = useState([DEFAULT_ROW(startAirfoil, defaultAlpha, defaultRe)])
  const [loading, setLoading] = useState(false)

  function addRow() {
    setRows(r => [...r, DEFAULT_ROW('', defaultAlpha, defaultRe)])
  }

  function removeRow(i) {
    setRows(r => r.filter((_, idx) => idx !== i))
  }

  function updateRow(i, field, value) {
    setRows(r => r.map((row, idx) => idx === i ? { ...row, [field]: value } : row))
  }

  async function runAll() {
    const valid = rows.filter(r => r.airfoil.trim().length === 4)
    if (!valid.length) return
    setLoading(true)
    try {
      const res = await axios.post(`${API}/simulate/compare`, {
        entries: rows.map(r => ({
          airfoil: r.airfoil.trim(),
          alpha: Number(r.alpha),
          reynolds: Number(r.reynolds),
          mach: currentProblem?.mach ?? 0.0,
        })),
        session_id: sessionId,
        participant_id: participantId,
      })
      const results = res.data.results
      setRows(prev => prev.map((row, i) => {
        const r = results[i]
        if (r?.error) return { ...row, error: r.error, CL: null, CD: null, L_D: null }
        return { ...row, CL: r?.CL ?? null, CD: r?.CD ?? null, L_D: r?.L_D ?? null, error: null }
      }))
      results.forEach(r => {
        if (!r.error) {
          addResult(r)
          incrementStats(1)
        }
      })
    } catch {
      // silent — individual rows show errors
    }
    setLoading(false)
  }

  const best = rows.reduce((b, r) => (!b || (r.L_D && r.L_D > (b.L_D || 0)) ? r : b), null)

  return (
    <div className="p-5 flex flex-col gap-4 h-full overflow-y-auto">
      <div className="text-xs text-zinc-500 tracking-widest">DESIGN TABLE</div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-zinc-500 tracking-widest border-b border-zinc-800">
              <th className="text-left pb-2 pr-2">AIRFOIL</th>
              <th className="text-left pb-2 pr-2">AoA°</th>
              <th className="text-left pb-2 pr-2">Re</th>
              <th className="text-right pb-2 pr-2">CL</th>
              <th className="text-right pb-2 pr-2">CD</th>
              <th className="text-right pb-2 pr-2">L/D</th>
              <th className="pb-2"></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className={`border-b border-zinc-800/50 ${row.L_D === best?.L_D && row.L_D ? 'bg-blue-900/20' : ''}`}>
                <td className="py-1.5 pr-2">
                  <input
                    value={row.airfoil}
                    onChange={e => updateRow(i, 'airfoil', e.target.value.replace(/\D/g, '').slice(0, 4))}
                    placeholder="2412"
                    maxLength={4}
                    className="bg-zinc-800 border border-zinc-700 text-zinc-100 font-mono rounded px-2 py-1 w-16 outline-none focus:border-blue-500 text-xs"
                  />
                </td>
                <td className="py-1.5 pr-2">
                  <input
                    type="number" value={row.alpha} min={-10} max={20} step={0.5}
                    onChange={e => updateRow(i, 'alpha', e.target.value)}
                    className="bg-zinc-800 border border-zinc-700 text-zinc-100 rounded px-2 py-1 w-14 outline-none focus:border-blue-500 text-xs"
                  />
                </td>
                <td className="py-1.5 pr-2">
                  <input
                    type="number" value={row.reynolds} step={50000}
                    onChange={e => updateRow(i, 'reynolds', e.target.value)}
                    className="bg-zinc-800 border border-zinc-700 text-zinc-100 rounded px-2 py-1 w-24 outline-none focus:border-blue-500 text-xs"
                  />
                </td>
                <td className="text-right py-1.5 pr-2 text-zinc-300">{row.CL?.toFixed(4) ?? (row.error ? '—' : '')}</td>
                <td className="text-right py-1.5 pr-2 text-zinc-300">{row.CD?.toFixed(5) ?? ''}</td>
                <td className={`text-right py-1.5 pr-2 font-bold ${row.L_D === best?.L_D && row.L_D ? 'text-blue-400' : 'text-zinc-100'}`}>
                  {row.error ? <span className="text-red-400 font-normal text-xs">{row.error.slice(0, 12)}</span> : (row.L_D ?? '')}
                </td>
                <td className="py-1.5">
                  {rows.length > 1 && (
                    <button onClick={() => removeRow(i)} className="text-zinc-600 hover:text-red-400 text-xs transition-colors">✕</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex gap-3">
        <button
          onClick={addRow}
          className="text-xs text-zinc-400 border border-zinc-700 hover:border-zinc-500 px-3 py-1.5 rounded transition-colors"
        >
          + ADD ROW
        </button>
        <button
          onClick={runAll}
          disabled={loading}
          className="flex-1 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-white text-xs font-bold tracking-widest py-2 rounded-lg transition-colors"
        >
          {loading ? 'COMPUTING…' : 'RUN ALL →'}
        </button>
      </div>

      {best?.L_D && (
        <div className="text-xs text-zinc-500">
          Best L/D: <span className="text-blue-400 font-bold">{best.L_D}</span> — NACA {best.airfoil}
        </div>
      )}
    </div>
  )
}
