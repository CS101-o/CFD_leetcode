import { useEffect, useRef, useState } from 'react'
import axios from 'axios'
import useStore from '../store/useStore'

const API = import.meta.env.VITE_API_URL || '/api/v1'

function ComplianceBar({ label, value, target, meets, gapPct, isCD }) {
  const fill = Math.min(Math.abs(value) / Math.abs(target), 1.3)
  const fillPct = Math.min(fill / 1.3 * 100, 100)
  const budgetLinePct = (1 / 1.3) * 100
  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex justify-between items-baseline text-[10px]">
        <span className="text-zinc-400 font-mono font-bold">{label}</span>
        <span className={`font-mono font-bold ${meets ? 'text-emerald-400' : 'text-red-400'}`}>
          {typeof value === 'number' ? (label === 'CD' ? value.toFixed(5) : value.toFixed(4)) : value}
          {' '}{meets ? '✓' : '✗'}
          {' '}<span className="text-zinc-500 font-normal">({meets ? '+' : ''}{gapPct}%)</span>
        </span>
      </div>
      <div className="relative h-1.5 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${meets ? 'bg-emerald-500' : 'bg-red-500'}`}
          style={{ width: `${fillPct}%` }}
        />
        <div className="absolute top-0 bottom-0 w-px bg-zinc-400 opacity-60" style={{ left: `${budgetLinePct}%` }} />
      </div>
    </div>
  )
}

function MiniPolar({ data, yKey, color }) {
  const W = 240, H = 80, PL = 28, PB = 18, PT = 6, PR = 6
  const pts = data.filter(p => p[yKey] != null)
  if (pts.length < 2) return null
  const xs = pts.map(p => p.alpha), ys = pts.map(p => p[yKey])
  const x0 = Math.min(...xs), x1 = Math.max(...xs)
  const pad = (Math.max(...ys) - Math.min(...ys)) * 0.12 || 0.05
  const y0 = Math.min(...ys) - pad, y1 = Math.max(...ys) + pad
  const sx = a => PL + (a - x0) / (x1 - x0) * (W - PL - PR)
  const sy = v => PT + (1 - (v - y0) / (y1 - y0)) * (H - PT - PB)
  const line = pts.map(p => `${sx(p.alpha).toFixed(1)},${sy(p[yKey]).toFixed(1)}`).join(' ')
  const ticks = [Math.min(...ys), (Math.min(...ys) + Math.max(...ys)) / 2, Math.max(...ys)]
  return (
    <svg width={W} height={H} className="shrink-0">
      {ticks.map((v, i) => (
        <g key={i}>
          <line x1={PL} x2={W - PR} y1={sy(v)} y2={sy(v)} stroke="#27272a" strokeWidth={0.5} />
          <text x={PL - 3} y={sy(v) + 3} textAnchor="end" fontSize={7} fill="#52525b">{v.toFixed(2)}</text>
        </g>
      ))}
      <polyline points={line} fill="none" stroke={color} strokeWidth={1.5} />
      <text x={(W + PL) / 2} y={H - 2} textAnchor="middle" fontSize={7} fill="#52525b">α°</text>
    </svg>
  )
}

function SimResultCard({ simData, designAlpha }) {
  const polar = simData?.polar_data
  const single = simData?.results || simData
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden text-[10px]">
      <div className="px-3 py-1.5 bg-zinc-800/60 flex items-center justify-between">
        <span className="font-mono font-bold text-blue-400">NACA {simData?.airfoil || single?.airfoil}</span>
        {simData?.summary?.max_L_D && (
          <span className="text-zinc-400">peak L/D <b className="text-emerald-400">{simData.summary.max_L_D}</b></span>
        )}
        {single?.CL != null && !polar && (
          <span className="text-zinc-400 font-mono">CL {single.CL.toFixed(4)} · CD {single.CD?.toFixed(5)}</span>
        )}
      </div>
      {polar && polar.length > 1 && (
        <div className="flex gap-1 p-2 bg-zinc-950">
          <MiniPolar data={polar} yKey="CL"  color="#3b82f6" />
          <MiniPolar data={polar} yKey="L_D" color="#10b981" />
        </div>
      )}
    </div>
  )
}

function AssessmentBubble({ msg }) {
  const { compliance, text, airfoil, alpha, reynolds, at_design } = msg
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold text-blue-400 font-mono tracking-widest">NACA {airfoil}</span>
        <span className="text-[9px] text-zinc-600 font-mono">
          α={alpha}° · Re={(reynolds / 1e5).toFixed(0)}×10⁵
          {!at_design && <span className="text-amber-500"> ≠ design pt</span>}
        </span>
      </div>
      {compliance && Object.keys(compliance).length > 0 && (
        <div className="flex flex-col gap-2 bg-zinc-900 rounded-lg p-3 border border-zinc-800">
          {compliance.CL && (
            <ComplianceBar label="CL" value={compliance.CL.value} target={compliance.CL.target}
              meets={compliance.CL.meets} gapPct={compliance.CL.gap_pct} />
          )}
          {compliance.CD && (
            <ComplianceBar label="CD" value={compliance.CD.value} target={compliance.CD.budget}
              meets={compliance.CD.meets} gapPct={compliance.CD.gap_pct} isCD />
          )}
          {compliance.L_D && (
            <ComplianceBar label="L/D" value={compliance.L_D.value} target={compliance.L_D.target}
              meets={compliance.L_D.meets} gapPct={compliance.L_D.gap_pct} />
          )}
        </div>
      )}
      <p className="text-xs text-zinc-300 leading-relaxed">{text}</p>
    </div>
  )
}

/**
 * Props:
 *  sessionId   — required
 *  runCount    — number of runs so far (for context)
 *  label       — popup header label
 *  onSendMessage(text, history) — async fn → { text, simData? }
 *      If not provided, defaults to /module01/ask (tutor-only, no sim power)
 *  placeholder — input placeholder text
 */
export default function AIChatPopup({ sessionId, runCount, label, onSendMessage, placeholder }) {
  const resolvedLabel = label || 'FLIGHT TUTOR'
  const resolvedPlaceholder = placeholder || 'Ask about the physics…'
  const { aiMessages, aiChatOpen, aiAssessing, addAiMessage, setAiChatOpen } = useStore()
  const [draft, setDraft] = useState('')
  const [asking, setAsking] = useState(false)
  const scrollRef = useRef(null)

  useEffect(() => {
    if (aiChatOpen && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [aiMessages, aiChatOpen])

  async function sendMessage() {
    const q = draft.trim()
    if (!q || asking) return
    setDraft('')
    setAsking(true)
    addAiMessage({ type: 'user', text: q })

    try {
      let text, simData
      if (onSendMessage) {
        const result = await onSendMessage(q, aiMessages)
        text = result.text
        simData = result.simData || null
      } else {
        const res = await axios.post(`${API}/module01/ask`, {
          session_id: sessionId,
          question: q,
          run_count: runCount,
        })
        text = res.data.message
      }
      addAiMessage({ type: 'tutor', text, simData })
    } catch (err) {
      const detail = err.response?.data?.detail
      addAiMessage({ type: 'tutor', text: detail || 'Could not reach the tutor — try again.' })
    }
    setAsking(false)
  }

  const hasNew = aiMessages.length > 0

  if (!aiChatOpen) {
    return (
      <button
        onClick={() => setAiChatOpen(true)}
        className="fixed bottom-5 right-5 z-40 flex items-center gap-2 bg-zinc-900 border border-zinc-700 hover:border-blue-500 text-zinc-100 text-xs font-bold tracking-widest px-3 py-2.5 rounded-full shadow-xl transition-all"
      >
        <span className="text-base">✦</span>
        TUTOR
        {hasNew && <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />}
      </button>
    )
  }

  return (
    <div className="fixed bottom-5 right-5 z-40 flex flex-col w-80 max-h-[540px] bg-zinc-950 border border-zinc-700 rounded-xl shadow-2xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-zinc-800 shrink-0 bg-zinc-900">
        <div className="flex items-center gap-2">
          <span className="text-blue-400">✦</span>
          <span className="text-[11px] font-bold tracking-widest text-zinc-100">{resolvedLabel}</span>
          {aiAssessing && <span className="text-[10px] text-zinc-500 animate-pulse">thinking…</span>}
        </div>
        <button onClick={() => setAiChatOpen(false)} className="text-zinc-600 hover:text-zinc-300 text-lg leading-none transition-colors">×</button>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 flex flex-col gap-4 min-h-0">
        {aiMessages.length === 0 && !aiAssessing && (
          <div className="text-xs text-zinc-600 leading-relaxed">{resolvedPlaceholder}</div>
        )}

        {aiMessages.map((msg, i) => (
          <div key={i}>
            {msg.type === 'assessment' && <AssessmentBubble msg={msg} />}
            {msg.type === 'user' && (
              <div className="flex justify-end">
                <div className="bg-blue-600/20 border border-blue-500/30 rounded-lg px-3 py-2 text-xs text-zinc-200 max-w-[85%]">
                  {msg.text}
                </div>
              </div>
            )}
            {msg.type === 'tutor' && (
              <div className="flex flex-col gap-2">
                {msg.text && (
                  <div className="text-xs text-zinc-300 leading-relaxed border-l-2 border-zinc-700 pl-3 whitespace-pre-wrap">
                    {msg.text}
                  </div>
                )}
                {msg.simData && <SimResultCard simData={msg.simData} />}
              </div>
            )}
          </div>
        ))}

        {aiAssessing && (
          <div className="flex gap-1.5 items-center text-xs text-zinc-500 py-1">
            <span className="animate-bounce">·</span>
            <span className="animate-bounce" style={{ animationDelay: '0.15s' }}>·</span>
            <span className="animate-bounce" style={{ animationDelay: '0.3s' }}>·</span>
          </div>
        )}
      </div>

      <div className="border-t border-zinc-800 p-3 shrink-0">
        <div className="flex gap-2">
          <input
            value={draft}
            onChange={e => setDraft(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() } }}
            placeholder={onSendMessage ? 'Ask or request a simulation…' : 'Ask about the physics…'}
            className="flex-1 bg-zinc-900 border border-zinc-700 text-zinc-100 text-xs rounded-lg px-3 py-2 outline-none focus:border-blue-500 placeholder-zinc-600 min-w-0"
            disabled={asking}
          />
          <button
            onClick={sendMessage}
            disabled={!draft.trim() || asking}
            className="bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-white text-[10px] font-bold tracking-widest px-3 rounded-lg transition-colors shrink-0"
          >
            SEND
          </button>
        </div>
      </div>
    </div>
  )
}
