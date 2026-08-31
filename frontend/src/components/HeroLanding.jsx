import { useEffect, useRef } from 'react'

function naca2412(xn) {
  const x = Math.max(1e-4, Math.min(0.9999, xn))
  const t = 0.12, m = 0.02, p = 0.4
  const yt = 5*t*(0.2969*Math.sqrt(x)-0.126*x-0.3516*x*x+0.2843*x*x*x-0.1015*x*x*x*x)
  const yc = x<p ? m/p/p*(2*p*x-x*x) : m/(1-p)/(1-p)*((1-2*p)+2*p*x-x*x)
  const dyc = x<p ? 2*m/p/p*(p-x) : 2*m/(1-p)/(1-p)*(p-x)
  const th = Math.atan(dyc)
  return { top: yc + yt*Math.cos(th), bot: yc - yt*Math.cos(th) }
}

const N_STREAMS = 34, STEPS = 220, MARGIN = 0.014

function buildScene(W, H) {
  const chordPx = Math.min(W * 0.60, H * 0.85, 460)
  const x0 = (W - chordPx) / 2
  const cy = H * 0.50
  const streams = []

  for (let si = 0; si < N_STREAMS; si++) {
    const frac = si / (N_STREAMS - 1)
    const yn0 = -0.50 + frac * 1.00

    let inside = false
    for (let k = 1; k <= 30; k++) {
      const { top, bot } = naca2412(k / 30)
      if (yn0 > bot && yn0 < top) { inside = true; break }
    }
    if (inside) continue

    const pts = []
    for (let s = 0; s <= STEPS; s++) {
      const x = s / STEPS * W
      const xn = (x - x0) / chordPx
      let yn = yn0

      if (xn >= 0 && xn <= 1) {
        const { top, bot } = naca2412(xn)
        if (yn0 >= 0) {
          if (yn0 < top + MARGIN) yn = top + MARGIN + (top + MARGIN - yn0) * 0.6
        } else {
          if (yn0 > bot - MARGIN) yn = bot - MARGIN + (bot - MARGIN - yn0) * 0.6
        }
      } else if (xn < 0) {
        const dist = Math.sqrt(xn*xn + yn0*yn0)
        yn = yn0 - 0.018 * yn0 / (dist + 0.12)
      } else {
        yn = yn0 + (yn - yn0) * Math.exp(-(xn - 1) * 4)
      }

      pts.push({ x, y: cy - yn * chordPx })
    }
    streams.push({ pts, yn0 })
  }

  return { chordPx, x0, cy, streams }
}

function drawAirfoil(ctx, x0, cy, chordPx) {
  const N = 90
  ctx.beginPath()
  for (let i = 0; i <= N; i++) {
    const { top } = naca2412(i / N)
    i === 0
      ? ctx.moveTo(x0 + i/N * chordPx, cy - top * chordPx)
      : ctx.lineTo(x0 + i/N * chordPx, cy - top * chordPx)
  }
  for (let i = N; i >= 0; i--) {
    const { bot } = naca2412(i / N)
    ctx.lineTo(x0 + i/N * chordPx, cy - bot * chordPx)
  }
  ctx.closePath()

  const grd = ctx.createLinearGradient(x0, cy - chordPx*0.14, x0 + chordPx, cy + chordPx*0.06)
  grd.addColorStop(0, 'rgba(37,88,200,0.38)')
  grd.addColorStop(0.45, 'rgba(59,130,246,0.28)')
  grd.addColorStop(1, 'rgba(25,55,140,0.08)')
  ctx.fillStyle = grd; ctx.fill()
  ctx.strokeStyle = 'rgba(96,160,255,0.65)'; ctx.lineWidth = 1.5; ctx.stroke()

  // Leading-edge dot
  ctx.beginPath(); ctx.arc(x0, cy, 2.5, 0, Math.PI*2)
  ctx.fillStyle = 'rgba(147,197,253,0.8)'; ctx.fill()

  // Upper highlight
  ctx.beginPath()
  for (let i = 0; i <= 55; i++) {
    const { top } = naca2412(i / 90)
    const px = x0 + (i/90) * chordPx, py = cy - top * chordPx
    i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py)
  }
  ctx.strokeStyle = 'rgba(180,215,255,0.42)'; ctx.lineWidth = 2.5; ctx.stroke()
}

export default function HeroLanding({ onEnter }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    if (!document.getElementById('hero-fonts')) {
      const link = document.createElement('link')
      link.id = 'hero-fonts'; link.rel = 'stylesheet'
      link.href = 'https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;700&family=IBM+Plex+Sans:wght@300;400;500&display=swap'
      document.head.appendChild(link)
    }
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    let raf, scene, particles = []

    function setSize() {
      const dpr = devicePixelRatio || 1
      const { width, height } = canvas.getBoundingClientRect()
      canvas.width = width * dpr; canvas.height = height * dpr
      ctx.resetTransform(); ctx.scale(dpr, dpr)
      scene = buildScene(width, height)
      particles = []
      scene.streams.forEach((s, si) => {
        const n = 2 + Math.floor(Math.random() * 4)
        for (let p = 0; p < n; p++) {
          particles.push({
            si, progress: Math.random(),
            speed: 0.0006 + (1 - Math.abs(s.yn0) / 0.5) * 0.0010 + Math.random() * 0.0003,
          })
        }
      })
    }

    setSize()
    const ro = new ResizeObserver(() => { cancelAnimationFrame(raf); setSize(); loop() })
    ro.observe(canvas)

    function loop() {
      const W = canvas.offsetWidth, H = canvas.offsetHeight
      ctx.clearRect(0, 0, W, H)
      ctx.fillStyle = '#090C12'; ctx.fillRect(0, 0, W, H)

      const gr = ctx.createRadialGradient(W/2, H/2, 0, W/2, H/2, scene.chordPx * 0.9)
      gr.addColorStop(0, 'rgba(37,99,235,0.07)'); gr.addColorStop(1, 'transparent')
      ctx.fillStyle = gr; ctx.fillRect(0, 0, W, H)

      scene.streams.forEach(({ pts, yn0 }) => {
        const closeness = Math.max(0, 1 - Math.abs(yn0) / 0.48)
        ctx.beginPath()
        ctx.moveTo(pts[0].x, pts[0].y)
        for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y)
        ctx.strokeStyle = `rgba(59,107,255,${0.05 + closeness * 0.14})`
        ctx.lineWidth = 1; ctx.stroke()
      })

      drawAirfoil(ctx, scene.x0, scene.cy, scene.chordPx)

      particles.forEach(p => {
        const s = scene.streams[p.si]
        if (!s) return
        p.progress = (p.progress + p.speed) % 1
        const idx = Math.min(Math.floor(p.progress * s.pts.length), s.pts.length - 1)
        const pt = s.pts[idx]
        if (!pt) return
        const closeness = Math.max(0, 1 - Math.abs(s.yn0) / 0.28)
        ctx.beginPath()
        ctx.arc(pt.x, pt.y, 1.2 + closeness * 0.9, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(147,197,253,${0.2 + closeness * 0.75})`
        ctx.fill()
      })

      raf = requestAnimationFrame(loop)
    }

    loop()
    return () => { cancelAnimationFrame(raf); ro.disconnect() }
  }, [])

  const mono = '"IBM Plex Mono", "Courier New", monospace'
  const sans = '"IBM Plex Sans", system-ui, sans-serif'

  return (
    <div style={{ position: 'fixed', inset: 0, overflow: 'hidden', background: '#090C12' }}>
      <canvas ref={canvasRef} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', display: 'block', pointerEvents: 'none' }} />

      {/* Vignette */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        background: 'radial-gradient(ellipse 85% 75% at 50% 50%, transparent 30%, rgba(9,12,18,0.55) 100%)',
      }} />

      {/* Card */}
      <div style={{
        position: 'relative', zIndex: 10,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        width: '100%', height: '100%', padding: 'clamp(12px,3vw,24px)',
      }}>
        <div style={{
          maxWidth: 540, width: '100%',
          background: 'rgba(11,15,28,0.91)',
          backdropFilter: 'blur(20px) saturate(1.4)',
          border: '1px solid rgba(59,107,255,0.22)',
          borderRadius: 3,
          boxShadow: '0 0 80px rgba(37,99,235,0.10), 0 32px 64px rgba(0,0,0,0.72)',
          overflow: 'hidden',
        }}>

          {/* Classification strip */}
          <div style={{
            padding: '5px 20px', display: 'flex', justifyContent: 'space-between',
            background: 'rgba(249,115,22,0.09)', borderBottom: '1px solid rgba(249,115,22,0.17)',
            fontFamily: mono, fontSize: 9, letterSpacing: '0.17em',
          }}>
            <span style={{ color: '#F97316' }}>ENGINEERING USE ONLY</span>
            <span style={{ color: '#6B3210' }}>REF: AE-2026-0047</span>
          </div>

          {/* Meta */}
          <div style={{ padding: '14px 20px 12px', borderBottom: '1px solid rgba(26,36,60,0.9)', display: 'flex', flexDirection: 'column', gap: 4 }}>
            {[
              ['FROM', 'Flight Test Directorate · Sparrow-7 Program', '#536282'],
              ['TO',   'Wing Design Engineer', '#BECDE8'],
              ['DATE', '2026-08-31 · 14:03 UTC', '#536282'],
            ].map(([label, val, col]) => (
              <div key={label} style={{ display: 'flex', gap: 12, alignItems: 'baseline' }}>
                <span style={{ fontFamily: mono, fontSize: 9, letterSpacing: '0.12em', color: '#2A3A55', minWidth: 38 }}>{label}</span>
                <span style={{ fontFamily: mono, fontSize: 10, color: col }}>{val}</span>
              </div>
            ))}
          </div>

          {/* Headline block */}
          <div style={{ padding: '18px 20px 16px', borderBottom: '1px solid rgba(26,36,60,0.9)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 13 }}>
              <span style={{
                fontFamily: mono, fontSize: 9, fontWeight: 700, letterSpacing: '0.16em',
                color: '#F97316', border: '1px solid rgba(249,115,22,0.38)',
                padding: '2px 8px', borderRadius: 2, background: 'rgba(249,115,22,0.08)',
              }}>HIGH PRIORITY</span>
              <span style={{ fontFamily: mono, fontSize: 9, color: '#2A3A55', letterSpacing: '0.10em' }}>WING SECTION REPLACEMENT</span>
            </div>
            <div style={{
              fontFamily: mono, fontSize: 'clamp(16px,3.2vw,22px)', fontWeight: 700,
              color: '#E6EDF9', lineHeight: 1.28, letterSpacing: '-0.01em', marginBottom: 14,
            }}>
              Current wing is failing the<br />endurance target by 23%.
            </div>
            <div style={{ fontFamily: sans, fontSize: 13, color: '#6C80A4', lineHeight: 1.8, fontWeight: 300 }}>
              NACA 2412 baseline delivers CL&nbsp;=&nbsp;0.63 at cruise — 23% short of the required
              CL&nbsp;≥&nbsp;0.80 at Re&nbsp;500,000. The flight test window opens in 72&nbsp;hours.
              We need a replacement wing section that closes the lift gap without blowing the drag budget.
            </div>
          </div>

          {/* Metrics */}
          <div style={{ display: 'flex', borderBottom: '1px solid rgba(26,36,60,0.9)' }}>
            {[
              { label: 'CL REQUIRED', val: '≥ 0.80', hot: true },
              { label: 'CD BUDGET',   val: '≤ 0.015', hot: false },
              { label: 'REYNOLDS No.', val: '500,000', hot: false },
            ].map((m, i) => (
              <div key={m.label} style={{
                flex: 1, padding: '11px 16px',
                borderRight: i < 2 ? '1px solid rgba(26,36,60,0.9)' : 'none',
              }}>
                <div style={{ fontFamily: mono, fontSize: 8, letterSpacing: '0.14em', color: '#2A3A55', marginBottom: 5 }}>{m.label}</div>
                <div style={{ fontFamily: mono, fontSize: 15, fontWeight: 700, color: m.hot ? '#F97316' : '#4878D8', fontVariantNumeric: 'tabular-nums' }}>{m.val}</div>
              </div>
            ))}
          </div>

          {/* Footer / CTA */}
          <div style={{ padding: '14px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontFamily: mono, fontSize: 9, color: '#1A2338', letterSpacing: '0.12em' }}>AIRFOILLEARNER · V1.0</span>
            <CtaButton onClick={onEnter} mono={mono}>ACCEPT BRIEF →</CtaButton>
          </div>

        </div>
      </div>
    </div>
  )
}

function CtaButton({ onClick, mono, children }) {
  const base = { background: 'rgba(37,99,235,0.18)', borderColor: 'rgba(59,107,255,0.50)', color: '#BECDE8' }
  const hover = { background: 'rgba(37,99,235,0.34)', borderColor: 'rgba(99,150,255,0.85)', color: '#F0F6FF' }
  return (
    <button
      onClick={onClick}
      onMouseEnter={e => Object.assign(e.currentTarget.style, hover)}
      onMouseLeave={e => Object.assign(e.currentTarget.style, base)}
      style={{
        fontFamily: mono, fontSize: 11, fontWeight: 700, letterSpacing: '0.15em',
        ...base, border: '1px solid rgba(59,107,255,0.50)',
        padding: '10px 22px', borderRadius: 2, cursor: 'pointer',
        transition: 'background 0.15s, border-color 0.15s, color 0.15s',
      }}
    >
      {children}
    </button>
  )
}
