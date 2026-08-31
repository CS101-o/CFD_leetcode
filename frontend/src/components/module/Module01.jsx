import { useEffect, useRef, useState } from 'react'
import axios from 'axios'
import useStore from '../../store/useStore'
import LeftPanel from '../LeftPanel'
import SliderMode from '../modes/SliderMode'
import TableMode from '../modes/TableMode'
import ParetoMode from '../modes/ParetoMode'
import AIChatPopup from '../AIChatPopup'

const API = import.meta.env.VITE_API_URL || '/api/v1'

const STAGES = ['brief', 'requirements', 'estimate', 'design', 'review', 'report']
const STAGE_LABELS = { brief: 'BRIEF', requirements: 'REQUIREMENTS', estimate: 'ESTIMATE', design: 'DESIGN', review: 'REVIEW', report: 'REPORT' }

// The backend serves artifact pages at /a/{id}; in dev the vite proxy only
// covers /api, so point at the API origin when it is absolute.
function artifactHref(path) {
  if (API.startsWith('http')) return new URL(path, API).href
  return `${window.location.origin}${path}`
}

function StageRail({ stage }) {
  const idx = STAGES.indexOf(stage)
  return (
    <div className="flex items-center gap-1 px-4 py-2 border-b border-zinc-800 bg-zinc-950 overflow-x-auto shrink-0">
      {STAGES.map((s, i) => (
        <div key={s} className="flex items-center gap-1 shrink-0">
          {i > 0 && <div className={`w-4 h-px ${i <= idx ? 'bg-blue-500' : 'bg-zinc-800'}`} />}
          <span className={`text-[10px] font-bold tracking-widest px-1.5 py-0.5 rounded ${
            i === idx ? 'text-blue-400 bg-blue-500/10 border border-blue-500/40'
            : i < idx ? 'text-zinc-500' : 'text-zinc-700'
          }`}>
            {i + 1} {STAGE_LABELS[s]}
          </span>
        </div>
      ))}
    </div>
  )
}

function RequirementChips() {
  return (
    <div className="flex gap-2 flex-wrap">
      {['CL ≥ 0.87', 'CD ≤ 0.0100', 'Re 5×10⁵', 'α = 5°'].map(c => (
        <span key={c} className="text-[10px] font-mono font-bold text-amber-300 bg-amber-950/40 border border-amber-500/20 rounded px-2 py-0.5">
          {c}
        </span>
      ))}
    </div>
  )
}

function PrimerCard({ title, children }) {
  const [open, setOpen] = useState(false)
  return (
    <div className={`border rounded-xl overflow-hidden transition-colors ${open ? 'border-zinc-600' : 'border-zinc-800'}`}>
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-left bg-zinc-900 hover:bg-zinc-800/80 transition-colors"
      >
        <span className="text-xs font-bold tracking-widest text-zinc-300">{title}</span>
        <span className={`text-zinc-500 text-lg leading-none transition-transform ${open ? 'rotate-45' : ''}`}>+</span>
      </button>
      {open && (
        <div className="px-4 pb-4 pt-3 bg-zinc-900 text-xs text-zinc-400 leading-relaxed flex flex-col gap-3 border-t border-zinc-800">
          {children}
        </div>
      )}
    </div>
  )
}

function BackgroundReading() {
  return (
    <div className="mt-5 flex flex-col gap-2">
      <div className="text-[10px] text-zinc-600 tracking-widest mb-1">BACKGROUND READING — expand to prepare</div>

      <PrimerCard title="NACA 4-DIGIT AIRFOILS — READING THE CODE">
        <p>
          The NACA 4-digit series encodes an airfoil's shape in four digits. Take NACA 2412 as an example:
          the <b className="text-zinc-200">2</b> is the maximum camber as a percentage of chord (2%);
          the <b className="text-zinc-200">4</b> is the chordwise location of that maximum camber in tenths of chord (40%);
          the <b className="text-zinc-200">12</b> is the maximum thickness as a percentage of chord (12%).
        </p>
        <p>
          A <b className="text-zinc-200">symmetric</b> airfoil (NACA 0012) has zero camber — it generates no lift at zero angle of attack.
          Increasing the first digit <b className="text-zinc-200">adds camber</b>, shifting the lift curve upward so the section generates more lift at the same angle of attack without changing the rigging angle.
          The baseline NACA 2412 has 2% camber. Your task is to find how much camber (and what thickness) meets the new lift requirement without busting drag.
        </p>
        <div className="bg-zinc-950 border border-zinc-800 rounded px-3 py-2 font-mono text-[11px] text-zinc-300">
          NACA <span className="text-blue-400">X</span><span className="text-amber-400">X</span><span className="text-emerald-400">XX</span>
          &nbsp;→&nbsp;
          <span className="text-blue-400">camber%</span> · <span className="text-amber-400">camber position/10</span> · <span className="text-emerald-400">thickness%</span>
        </div>
      </PrimerCard>

      <PrimerCard title="REYNOLDS NUMBER — WHY LOW-Re IS DIFFERENT">
        <p>
          The Reynolds number Re = V·c/ν is the ratio of inertial to viscous forces in the flow.
          At SPARROW-7's cruise (V = 22 m/s, c = 0.34 m, ν ≈ 1.5 × 10⁻⁵ m²/s):
        </p>
        <div className="bg-zinc-950 border border-zinc-800 rounded px-3 py-2 font-mono text-[11px] text-zinc-300">
          Re = (22 × 0.34) / 1.5×10⁻⁵ ≈ 5 × 10⁵
        </div>
        <p>
          Re ≈ 5 × 10⁵ is considered <b className="text-zinc-200">low-Re</b>. In this regime viscous forces are significant,
          boundary layers are thicker relative to chord, and drag is more sensitive to surface geometry than at the
          high-Re conditions (Re &gt; 10⁶) used in most published airfoil data. Running a simulation at Re = 5 × 10⁶ and
          transferring those numbers to a 34 cm chord UAV is a common error — one with real consequences for the drag budget.
        </p>
      </PrimerCard>

      <PrimerCard title="LIFT AND DRAG COEFFICIENTS — THE TARGET NUMBERS">
        <p>
          <b className="text-zinc-200">CL (lift coefficient)</b> normalises lift force by dynamic pressure and chord:
          CL = L / (½ρV²c). It is dimensionless, so it characterises the section independently of aircraft size or speed.
          At the design condition, you need CL ≥ 0.87 to carry the extra weight. Camber is the primary lever — more camber → higher CL at a fixed angle of attack.
        </p>
        <p>
          <b className="text-zinc-200">CD (profile drag coefficient)</b> captures skin-friction drag (attached-flow viscous shear) and pressure drag (from any separated region).
          The budget is CD ≤ 0.0100 — if you exceed it, the energy model loses the 90-minute endurance commitment.
          In the low-Re regime, even a modest increase in camber can promote leading-edge adverse pressure gradients that raise CD significantly.
          This is the tension: the fix for lift can hurt drag.
        </p>
      </PrimerCard>

      <PrimerCard title="THE TRADE-OFF — WHY THIS ISN'T TRIVIAL">
        <p>
          More camber raises CL at a given angle of attack — exactly what the weight increase demands.
          But camber also steepens the adverse pressure gradient on the upper surface, which thickens the boundary layer
          and, at low Re, can trigger laminar separation earlier. The result: CD climbs.
        </p>
        <p>
          Thickness also matters. A thicker section has a more gradual pressure recovery, which can help attached flow — but adds wetted area and form drag.
          The sweet spot is some combination of camber and thickness that meets CL ≥ 0.87 without the drag penalty erasing the endurance margin.
          Your job in the design loop is to find that combination by running cases and reading the numbers against the requirements.
        </p>
        <div className="bg-zinc-950 border border-zinc-800 rounded px-3 py-2 text-[11px] text-zinc-400">
          <div className="font-bold text-zinc-300 mb-1">What to watch</div>
          <div>↑ camber → ↑ CL (good) but risk ↑ CD (bad)</div>
          <div>↑ thickness → better pressure recovery but ↑ wetted area</div>
          <div>Wrong Re → numbers that look good but don't apply to SPARROW-7</div>
        </div>
      </PrimerCard>
    </div>
  )
}

export default function Module01({ onExit }) {
  const {
    sessionId, participantId, setParticipantId,
    setCurrentProblem, sessionStats, results, allResults,
    addAiMessage, setAiAssessing,
  } = useStore()

  const [mod, setMod] = useState(null)
  const [stage, setStageRaw] = useState('brief')

  // Stage 1 — requirements
  const [reqAnswers, setReqAnswers] = useState({})
  const [reqResults, setReqResults] = useState(null)
  const [reqPassed, setReqPassed] = useState(false)

  // Stage 2 — estimate
  const [estimate, setEstimate] = useState(null)
  const [firstRunCL, setFirstRunCL] = useState(null)
  const mismatchLogged = useRef(false)

  // Stage 4 — checkpoint
  const [checkpointOpen, setCheckpointOpen] = useState(false)
  const [checkpointDone, setCheckpointDone] = useState(false)
  const [signOff, setSignOff] = useState(null)
  const [reasoning, setReasoning] = useState('')
  const [reveal, setReveal] = useState(null)
  const [checkpointError, setCheckpointError] = useState('')

  // Stage 5 — review
  const [finalAirfoil, setFinalAirfoil] = useState('')
  const [review, setReview] = useState({ justification: '', tradeoff: '', validate_next: '' })
  const [submitError, setSubmitError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [artifact, setArtifact] = useState(null)

  // Report — deferred signup
  const [email, setEmail] = useState('')
  const [claimState, setClaimState] = useState('') // '', 'saving', 'done', error text

  const [designTab, setDesignTab] = useState('sliders')

  function logEvent(event, data = {}) {
    axios.post(`${API}/module01/event`, { session_id: sessionId, event, data }).catch(() => {})
  }

  function setStage(next) {
    setStageRaw(next)
    logEvent('stage_enter', { stage: next })
  }

  useEffect(() => {
    axios.get(`${API}/module01`).then(res => setMod(res.data)).catch(() => {})
    if (!participantId) setParticipantId('anon')
    let returning = false
    try {
      returning = localStorage.getItem('al_m01_started') === '1'
      localStorage.setItem('al_m01_started', '1')
    } catch { /* private mode */ }
    logEvent('module_start', { returning })
    // Log session start with IP capture on the backend
    axios.post(`${API}/module01/start`, { session_id: sessionId }).catch(() => {})
  }, [])

  // Give the reused design-loop modes (sliders/table/pareto/3D view) the
  // module's operating conditions via the problem object they already read.
  useEffect(() => {
    if (!mod) return
    setCurrentProblem({
      id: mod.id,
      title: mod.title,
      difficulty: 'medium',
      starting_airfoil: `naca${mod.conditions.airfoil_baseline}`,
      design_alpha: mod.conditions.design_alpha,
      Re: mod.conditions.reynolds,
      mach: mod.conditions.mach,
      success_criteria: { cruise_CL_min: 0.87 },
      sender: mod.sender,
      mission_briefing: mod.brief,
      bottleneck: mod.brief,
    })
  }, [mod])

  // Capture the first run's CL to place beside the estimate
  useEffect(() => {
    if (stage !== 'design' || firstRunCL != null) return
    if (sessionStats.experimentsRun > 0 && results?.CL != null) {
      setFirstRunCL(results.CL)
    }
  }, [sessionStats.experimentsRun, results, stage, firstRunCL])

  const mismatch = estimate != null && firstRunCL != null
    && Math.abs(firstRunCL - estimate) > (mod?.prediction?.mismatch_threshold ?? 0.3)

  useEffect(() => {
    if (mismatch && !mismatchLogged.current) {
      mismatchLogged.current = true
      logEvent('estimate_mismatch_shown', { estimate, first_run_CL: firstRunCL })
    }
  }, [mismatch])

  // Welcome hint when first entering the design stage
  const welcomeSent = useRef(false)
  useEffect(() => {
    if (stage !== 'design' || welcomeSent.current) return
    welcomeSent.current = true
    setAiAssessing(true)
    axios.post(`${API}/module01/hint`, {
      session_id: sessionId,
      run_count: 0,
      recent_results: [],
      hint_type: 'welcome',
    }).then(res => {
      if (res.data.message) addAiMessage({ type: 'tutor', text: res.data.message })
    }).catch(() => {
      setAiAssessing(false)
    })
  }, [stage])

  // After every sim run in the design stage, ask the LLM to assess the result
  const lastAssessedRun = useRef(0)
  useEffect(() => {
    if (stage !== 'design') return
    if (!results || sessionStats.experimentsRun === 0) return
    if (sessionStats.experimentsRun === lastAssessedRun.current) return
    lastAssessedRun.current = sessionStats.experimentsRun
    setAiAssessing(true)
    axios.post(`${API}/module01/assess`, {
      session_id: sessionId,
      airfoil: results.airfoil || '????',
      alpha: results.alpha ?? 5,
      reynolds: results.reynolds ?? 500000,
      CL: results.CL,
      CD: results.CD,
      L_D: results.L_D ?? null,
    }).then(res => {
      addAiMessage({
        type: 'assessment',
        text: res.data.message,
        compliance: res.data.compliance,
        at_design: res.data.at_design_condition,
        airfoil: results.airfoil || '????',
        alpha: results.alpha ?? 5,
        reynolds: results.reynolds ?? 500000,
      })
    }).catch(() => {
      setAiAssessing(false)
    })
  }, [sessionStats.experimentsRun])

  // Proactive suggestion after every run (not just every 3)
  const lastHintRun = useRef(0)
  useEffect(() => {
    if (stage !== 'design' || sessionStats.experimentsRun === 0) return
    if (sessionStats.experimentsRun === lastHintRun.current) return
    const recentPassing = allResults.slice(-1).every(r => r.CL >= 0.87 && r.CD <= 0.0100)
    if (recentPassing) return
    lastHintRun.current = sessionStats.experimentsRun
    const recent = allResults.slice(-3).map(r => ({
      airfoil: r.airfoil || '????',
      CL: r.CL,
      CD: r.CD,
      cl_meets: r.CL >= 0.87,
      cd_meets: r.CD <= 0.0100,
    }))
    axios.post(`${API}/module01/hint`, {
      session_id: sessionId,
      run_count: sessionStats.experimentsRun,
      recent_results: recent,
      hint_type: 'progress',
    }).then(res => {
      if (res.data.message) addAiMessage({ type: 'tutor', text: res.data.message })
    }).catch(() => {})
  }, [sessionStats.experimentsRun])

  // Intern checkpoint fires after N runs
  useEffect(() => {
    if (stage !== 'design' || checkpointDone || checkpointOpen || !mod) return
    if (sessionStats.experimentsRun >= (mod.checkpoint.trigger_after_runs ?? 3)) {
      setCheckpointOpen(true)
    }
  }, [sessionStats.experimentsRun, stage, checkpointDone, checkpointOpen, mod])

  async function checkRequirements() {
    const answers = mod.requirements_questions.map(q => reqAnswers[q.id] ?? -1)
    if (answers.includes(-1)) return
    try {
      const res = await axios.post(`${API}/module01/requirements/check`, { session_id: sessionId, answers })
      setReqResults(res.data.results)
      if (res.data.all_correct) setReqPassed(true)
    } catch { /* transient */ }
  }

  async function submitEstimate(value) {
    setEstimate(value)
    axios.post(`${API}/module01/prediction`, { session_id: sessionId, estimate_CL: value }).catch(() => {})
    setStage('design')
  }

  async function submitCheckpoint() {
    if (signOff == null) { setCheckpointError('Pick a verdict: sign off or not.'); return }
    setCheckpointError('')
    try {
      const res = await axios.post(`${API}/module01/checkpoint`, {
        session_id: sessionId, would_sign_off: signOff, reasoning,
      })
      setReveal(res.data.reveal)
    } catch (err) {
      setCheckpointError(err.response?.data?.detail || 'Something went wrong — try again.')
    }
  }

  async function submitReview() {
    setSubmitError('')
    setSubmitting(true)
    try {
      const res = await axios.post(`${API}/module01/review/submit`, {
        session_id: sessionId,
        airfoil: finalAirfoil,
        alpha: mod.conditions.design_alpha,
        ...review,
      })
      setArtifact(res.data)
      setStage('report')
    } catch (err) {
      setSubmitError(err.response?.data?.detail || 'Submission failed — is the backend running?')
    }
    setSubmitting(false)
  }

  async function claimArtifact() {
    setClaimState('saving')
    try {
      await axios.post(`${API}/module01/claim`, { artifact_id: artifact.artifact_id, email })
      setClaimState('done')
    } catch (err) {
      setClaimState(err.response?.data?.detail || 'Could not save — check the address.')
    }
  }

  if (!mod) {
    return (
      <div className="flex h-screen items-center justify-center bg-zinc-950 text-zinc-500 text-xs tracking-widest">
        LOADING MODULE…
      </div>
    )
  }

  const cp = mod.checkpoint
  const minJust = mod.review_form.min_justification_chars
  const minField = mod.review_form.min_field_chars
  const reviewReady =
    finalAirfoil.replace(/\D/g, '').length === 4 &&
    review.justification.trim().length >= minJust &&
    review.tradeoff.trim().length >= minField &&
    review.validate_next.trim().length >= minField

  return (
    <div className="flex flex-col h-screen bg-zinc-950 text-zinc-100 overflow-hidden">
      {stage === 'design' && (
        <AIChatPopup sessionId={sessionId} runCount={sessionStats.experimentsRun} />
      )}

      {/* Header */}
      <div className="border-b border-zinc-800 px-4 py-2.5 flex items-center justify-between bg-zinc-950 shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-blue-500 rotate-45 rounded-sm" />
          <span className="text-[11px] font-bold tracking-widest">AIRFOILLEARNER</span>
          <span className="text-zinc-700 text-[11px]">·</span>
          <span className="text-[11px] text-zinc-500 tracking-widest hidden sm:inline">MODULE 01 — {mod.program.toUpperCase()}</span>
        </div>
        {onExit && (
          <button onClick={onExit} className="text-[10px] text-zinc-600 hover:text-zinc-400 tracking-widest transition-colors">
            HOME PAGE →
          </button>
        )}
      </div>

      <StageRail stage={stage} />

      {/* ── Stage: brief ── */}
      {stage === 'brief' && (
        <div className="flex-1 overflow-y-auto flex justify-center px-4 py-8">
          <div className="max-w-2xl w-full">
            <div className="text-xs text-zinc-500 tracking-widest mb-3">INTERNAL MEMO · {mod.title.toUpperCase()}</div>
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap font-mono">
              {mod.brief}
            </div>

            <BackgroundReading />

            <div className="mt-5 flex gap-3">
              <button
                onClick={() => { logEvent('brief_read'); setStage('requirements') }}
                className="flex-1 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold tracking-widest py-3 rounded-lg transition-colors"
              >
                EXTRACT THE REQUIREMENTS →
              </button>
              <button
                onClick={() => { logEvent('brief_skipped'); setStage('design') }}
                className="px-5 bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200 text-xs font-bold tracking-widest py-3 rounded-lg transition-colors"
              >
                SKIP TO DESIGN
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Stage: requirements extraction ── */}
      {stage === 'requirements' && (
        <div className="flex-1 overflow-y-auto flex justify-center px-4 py-8">
          <div className="max-w-2xl w-full">
            <div className="text-xs text-zinc-500 tracking-widest mb-1">STEP 2 — TRANSLATE THE MEMO INTO HARD NUMBERS</div>
            <p className="text-xs text-zinc-400 mb-5">Real briefs arrive as program language. Before you touch the tools, pin down what the Chief Engineer is actually asking for.</p>
            <div className="flex flex-col gap-4">
              {mod.requirements_questions.map((q, qi) => {
                const result = reqResults?.[qi]
                return (
                  <div key={q.id} className={`bg-zinc-900 border rounded-xl p-4 ${
                    result == null ? 'border-zinc-800' : result.correct ? 'border-emerald-600/50' : 'border-red-600/50'
                  }`}>
                    <div className="text-xs text-zinc-300 font-bold mb-2">{q.label}</div>
                    <div className="flex flex-col gap-1.5">
                      {q.options.map((opt, oi) => (
                        <label key={oi} className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer">
                          <input
                            type="radio"
                            name={q.id}
                            checked={reqAnswers[q.id] === oi}
                            onChange={() => { setReqAnswers(a => ({ ...a, [q.id]: oi })); setReqResults(null) }}
                            className="accent-blue-500"
                          />
                          {opt}
                        </label>
                      ))}
                    </div>
                    {result && !result.correct && (
                      <div className="mt-2 text-[11px] text-amber-300 bg-amber-950/30 border border-amber-500/20 rounded px-2 py-1.5">
                        {result.hint}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
            {!reqPassed ? (
              <button
                onClick={checkRequirements}
                disabled={Object.keys(reqAnswers).length < mod.requirements_questions.length}
                className="mt-5 w-full bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-white text-xs font-bold tracking-widest py-3 rounded-lg transition-colors"
              >
                CHECK MY REQUIREMENTS
              </button>
            ) : (
              <button
                onClick={() => setStage('estimate')}
                className="mt-5 w-full bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold tracking-widest py-3 rounded-lg transition-colors"
              >
                REQUIREMENTS CONFIRMED — CONTINUE →
              </button>
            )}
          </div>
        </div>
      )}

      {/* ── Stage: estimate (prediction gate) ── */}
      {stage === 'estimate' && (
        <div className="flex-1 overflow-y-auto flex justify-center px-4 py-8">
          <div className="max-w-xl w-full">
            <div className="text-xs text-zinc-500 tracking-widest mb-1">STEP 3 — ESTIMATE BEFORE YOU SIMULATE</div>
            <p className="text-xs text-zinc-400 mb-5">Engineers who skip the back-of-envelope step are the ones who ship bad results. Your estimate is recorded and shown beside your first computed number.</p>
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
              <p className="text-sm text-zinc-200 leading-relaxed mb-4">{mod.prediction.question}</p>
              <div className="flex gap-3">
                {mod.prediction.options.map(v => (
                  <button
                    key={v}
                    onClick={() => submitEstimate(v)}
                    className="flex-1 bg-zinc-800 hover:bg-blue-600 border border-zinc-700 hover:border-blue-500 text-zinc-100 font-mono font-bold text-lg py-3 rounded-lg transition-colors"
                  >
                    ≈ {v}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Stage: design loop ── */}
      {stage === 'design' && (
        <div className="flex flex-1 min-h-0">
          {/* Left: 3D view + status (desktop) */}
          <div className="hidden md:flex flex-1 border-r border-zinc-800 flex-col min-w-0">
            <div className="flex-1 overflow-hidden"><LeftPanel /></div>
            <div className="border-t border-zinc-800 bg-zinc-950 px-5 py-3 shrink-0 flex items-center justify-between gap-4">
              <RequirementChips />
              <div className="text-[10px] text-zinc-600 tracking-widest shrink-0">
                {sessionStats.experimentsRun} RUNS
              </div>
            </div>
          </div>

          {/* Right: tools */}
          <div className="flex-1 md:flex-none w-full md:w-[440px] bg-zinc-900 flex flex-col min-h-0">
            {/* Estimate vs first run */}
            {estimate != null && (
              <div className={`px-4 py-2 text-[11px] border-b shrink-0 ${
                mismatch ? 'bg-amber-950/40 border-amber-600/30 text-amber-200'
                         : 'bg-zinc-950 border-zinc-800 text-zinc-400'
              }`}>
                Your estimate: CL ≈ <b className="font-mono">{estimate}</b>
                {firstRunCL != null && <> · first computed: CL = <b className="font-mono">{firstRunCL.toFixed(3)}</b></>}
                {firstRunCL == null && <> · run the baseline to compare</>}
                {mismatch && <div className="mt-1">That's a large gap. Is the simulation wrong, or was the estimate wrong? Investigate before continuing.</div>}
              </div>
            )}

            <div className="border-b border-zinc-800 flex shrink-0">
              {[['sliders', 'RUN'], ['table', 'COMPARE'], ['pareto', 'TRADEOFF']].map(([id, label]) => (
                <button
                  key={id}
                  onClick={() => setDesignTab(id)}
                  className={`px-3 py-2.5 text-xs font-bold tracking-widest transition-colors border-b-2 -mb-px flex-1 ${
                    designTab === id ? 'text-blue-400 border-blue-500 bg-zinc-800/50'
                                     : 'text-zinc-600 border-transparent hover:text-zinc-400'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            <div className="flex-1 overflow-hidden">
              {designTab === 'sliders' && <SliderMode />}
              {designTab === 'table' && <TableMode />}
              {designTab === 'pareto' && <ParetoMode />}
            </div>

            <div className="border-t border-zinc-800 p-3 shrink-0">
              <button
                onClick={() => { setFinalAirfoil(results?.airfoil || ''); setStage('review') }}
                disabled={!checkpointDone}
                className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-white text-xs font-bold tracking-widest py-2.5 rounded-lg transition-colors"
              >
                {checkpointDone ? 'GO TO DESIGN REVIEW →' : `KEEP ITERATING — REVIEW UNLOCKS AFTER THE CHECKPOINT (${sessionStats.experimentsRun}/${cp.trigger_after_runs} RUNS)`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Intern checkpoint modal ── */}
      {checkpointOpen && (
        <div className="fixed inset-0 bg-black/85 z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-700 rounded-xl max-w-lg w-full max-h-[90vh] overflow-y-auto p-6">
            <div className="text-xs text-amber-400 tracking-widest font-bold mb-2">JUDGMENT CHECKPOINT</div>
            <div className="text-sm text-zinc-100 font-bold mb-2">{cp.title}</div>
            <p className="text-xs text-zinc-400 leading-relaxed mb-4">{cp.setup}</p>

            <div className="bg-zinc-950 border border-zinc-700 rounded-lg p-4 mb-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-blue-400 font-mono font-bold text-sm">NACA {cp.intern_result.airfoil}</span>
                <span className="text-[10px] text-zinc-500 font-mono">
                  α = {cp.intern_result.alpha}° · Re = {cp.intern_result.reynolds.toExponential(1).replace('e+6', '×10⁶')}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-3 text-center mb-3">
                <div><div className="text-lg font-bold text-zinc-100">{cp.intern_result.CL}</div><div className="text-[10px] text-zinc-500 tracking-widest">CL</div></div>
                <div><div className="text-lg font-bold text-emerald-400">{cp.intern_result.CD}</div><div className="text-[10px] text-zinc-500 tracking-widest">CD</div></div>
                <div><div className="text-lg font-bold text-zinc-100">{cp.intern_result.L_D}</div><div className="text-[10px] text-zinc-500 tracking-widest">L/D</div></div>
              </div>
              <p className="text-xs text-zinc-300 italic">"{cp.intern_result.claim}"</p>
            </div>

            {!reveal ? (
              <>
                <p className="text-xs text-zinc-300 mb-3">{cp.question}</p>
                <div className="flex gap-3 mb-3">
                  <button
                    onClick={() => setSignOff(true)}
                    className={`flex-1 text-xs font-bold tracking-widest py-2 rounded-lg border transition-colors ${
                      signOff === true ? 'bg-emerald-600 border-emerald-500 text-white' : 'bg-zinc-800 border-zinc-700 text-zinc-400 hover:text-zinc-200'
                    }`}
                  >
                    SIGN OFF
                  </button>
                  <button
                    onClick={() => setSignOff(false)}
                    className={`flex-1 text-xs font-bold tracking-widest py-2 rounded-lg border transition-colors ${
                      signOff === false ? 'bg-red-600 border-red-500 text-white' : 'bg-zinc-800 border-zinc-700 text-zinc-400 hover:text-zinc-200'
                    }`}
                  >
                    DON'T SIGN OFF
                  </button>
                </div>
                <textarea
                  value={reasoning}
                  onChange={e => setReasoning(e.target.value)}
                  placeholder="Your reasoning — what did you check, and what do you tell the intern?"
                  rows={4}
                  className="w-full bg-zinc-800 border border-zinc-700 text-zinc-100 text-xs rounded-lg px-3 py-2 outline-none focus:border-blue-500 placeholder-zinc-600 resize-none"
                />
                <div className="flex justify-between items-center mt-1 mb-3">
                  <span className="text-[10px] text-zinc-600">{reasoning.trim().length}/{cp.min_answer_chars} characters minimum</span>
                </div>
                {checkpointError && <div className="text-red-400 text-xs mb-2">{checkpointError}</div>}
                <button
                  onClick={submitCheckpoint}
                  disabled={reasoning.trim().length < cp.min_answer_chars || signOff == null}
                  className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-white text-xs font-bold tracking-widest py-2.5 rounded-lg transition-colors"
                >
                  SUBMIT MY CALL
                </button>
              </>
            ) : (
              <>
                <div className="bg-blue-950/40 border border-blue-500/30 rounded-lg p-4 text-xs text-zinc-200 leading-relaxed mb-4">
                  <div className="text-blue-400 tracking-widest font-bold text-[10px] mb-2">WHAT A REVIEWER WOULD HAVE CAUGHT</div>
                  {reveal}
                </div>
                <button
                  onClick={() => { setCheckpointOpen(false); setCheckpointDone(true) }}
                  className="w-full bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold tracking-widest py-2.5 rounded-lg transition-colors"
                >
                  BACK TO THE DESIGN LOOP →
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* ── Stage: design review ── */}
      {stage === 'review' && (
        <div className="flex-1 overflow-y-auto flex justify-center px-4 py-8">
          <div className="max-w-2xl w-full">
            <div className="text-xs text-zinc-500 tracking-widest mb-1">STEP 5 — DEFEND YOUR DESIGN</div>
            <p className="text-xs text-zinc-400 mb-5">This is the deliverable. Submission is blocked until every field has a real answer — a bare "submit" button is not how design freezes work.</p>

            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 flex flex-col gap-4">
              <div className="flex items-end gap-4">
                <div className="flex flex-col gap-1">
                  <label className="text-[10px] text-zinc-500 tracking-widest">FINAL SECTION (NACA 4-DIGIT)</label>
                  <input
                    value={finalAirfoil}
                    onChange={e => setFinalAirfoil(e.target.value.replace(/\D/g, '').slice(0, 4))}
                    placeholder="e.g. 3412"
                    maxLength={4}
                    className="bg-zinc-800 border border-zinc-700 text-zinc-100 font-mono text-sm rounded px-3 py-2 w-28 outline-none focus:border-blue-500"
                  />
                </div>
                <div className="text-[11px] text-zinc-500 pb-2">
                  verified at α = {mod.conditions.design_alpha}°, Re = {mod.conditions.reynolds.toLocaleString()} on submit
                </div>
              </div>

              {mod.review_form.fields.map(f => {
                const min = f.id === 'justification' ? minJust : minField
                const val = review[f.id]
                return (
                  <div key={f.id} className="flex flex-col gap-1">
                    <label className="text-xs text-zinc-300 font-bold">{f.label}</label>
                    <textarea
                      value={val}
                      onChange={e => setReview(r => ({ ...r, [f.id]: e.target.value }))}
                      placeholder={f.placeholder}
                      rows={3}
                      className="bg-zinc-800 border border-zinc-700 text-zinc-100 text-xs rounded-lg px-3 py-2 outline-none focus:border-blue-500 placeholder-zinc-600 resize-none leading-relaxed"
                    />
                    <span className={`text-[10px] ${val.trim().length >= min ? 'text-emerald-500' : 'text-zinc-600'}`}>
                      {val.trim().length}/{min} characters minimum
                    </span>
                  </div>
                )
              })}
            </div>

            {submitError && <div className="text-red-400 text-xs mt-3">{submitError}</div>}
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => setStage('design')}
                className="px-4 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-bold tracking-widest py-3 rounded-lg transition-colors"
              >
                ← BACK TO TOOLS
              </button>
              <button
                onClick={submitReview}
                disabled={!reviewReady || submitting}
                className="flex-1 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-white text-xs font-bold tracking-widest py-3 rounded-lg transition-colors"
              >
                {submitting ? 'VERIFYING DESIGN…' : 'SUBMIT TO DESIGN REVIEW →'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Stage: report / artifact ── */}
      {stage === 'report' && artifact && (
        <div className="flex-1 overflow-y-auto flex justify-center px-4 py-8">
          <div className="max-w-xl w-full">
            <div className="text-xs text-emerald-400 tracking-widest font-bold mb-1">MODULE COMPLETE</div>
            <div className="text-lg text-zinc-100 font-bold mb-4">Design submitted: NACA {artifact.design.airfoil}</div>

            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 mb-4">
              {[
                ['Cruise lift coefficient', `CL ≥ ${artifact.compliance.CL.target}`, artifact.compliance.CL.value, artifact.compliance.CL.meets, artifact.compliance.CL.margin_pct],
                ['Profile drag budget', `CD ≤ ${artifact.compliance.CD.budget}`, artifact.compliance.CD.value, artifact.compliance.CD.meets, artifact.compliance.CD.margin_pct],
              ].map(([label, target, value, meets, margin]) => (
                <div key={label} className="flex items-center justify-between py-2 border-b border-zinc-800 last:border-0 text-xs">
                  <span className="text-zinc-400">{label} <span className="text-zinc-600">({target})</span></span>
                  <span className="font-mono">
                    {value} · {margin}% margin ·{' '}
                    <b className={meets ? 'text-emerald-400' : 'text-red-400'}>{meets ? 'MEETS' : 'FAILS'}</b>
                  </span>
                </div>
              ))}
            </div>

            <a
              href={artifactHref(artifact.artifact_url)}
              target="_blank"
              rel="noreferrer"
              onClick={() => logEvent('artifact_viewed', { artifact_id: artifact.artifact_id })}
              className="block w-full text-center bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold tracking-widest py-3 rounded-lg transition-colors mb-4"
            >
              OPEN YOUR SHAREABLE DESIGN REPORT →
            </a>

            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
              <div className="text-xs text-zinc-300 font-bold mb-1">Keep your work</div>
              <p className="text-[11px] text-zinc-500 mb-3">Leave an email to attach this report to you — that's the whole signup. Anyone with the link can view the report either way.</p>
              {claimState === 'done' ? (
                <div className="text-emerald-400 text-xs font-bold">Saved — the report is yours.</div>
              ) : (
                <div className="flex gap-2">
                  <input
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    placeholder="you@university.edu"
                    className="flex-1 bg-zinc-800 border border-zinc-700 text-zinc-100 text-xs rounded-lg px-3 py-2 outline-none focus:border-blue-500 placeholder-zinc-600"
                  />
                  <button
                    onClick={claimArtifact}
                    disabled={!email.trim() || claimState === 'saving'}
                    className="bg-zinc-100 hover:bg-white disabled:bg-zinc-800 disabled:text-zinc-600 text-zinc-900 text-xs font-bold tracking-widest px-4 rounded-lg transition-colors"
                  >
                    SAVE
                  </button>
                </div>
              )}
              {claimState && claimState !== 'saving' && claimState !== 'done' && (
                <div className="text-red-400 text-[11px] mt-2">{claimState}</div>
              )}
            </div>

            <a
              href={artifactHref('/forage')}
              target="_blank"
              rel="noreferrer"
              onClick={() => logEvent('forage_link_clicked')}
              className="block text-center mt-4 text-[11px] text-zinc-500 hover:text-blue-400 tracking-widest transition-colors"
            >
              MODULE 02 IS IN DESIGN — SEE WHAT'S COMING →
            </a>
          </div>
        </div>
      )}
    </div>
  )
}
