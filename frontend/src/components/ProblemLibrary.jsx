import useStore from '../store/useStore'

const DIFFICULTY_STYLES = {
  easy: 'text-green-400 border-green-400/30 bg-green-400/10',
  medium: 'text-orange-400 border-orange-400/30 bg-orange-400/10',
  hard: 'text-red-400 border-red-400/30 bg-red-400/10',
}

export default function ProblemLibrary() {
  const { problems, setCurrentProblem } = useStore()

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="border-b border-zinc-800 px-8 py-4 flex items-center gap-3">
        <div className="w-6 h-6 bg-blue-500 rotate-45 rounded-sm" />
        <div>
          <h1 className="text-sm font-bold tracking-widest text-zinc-100">FLOWSENSE</h1>
          <p className="text-xs text-zinc-500 tracking-widest">CFD BOTTLENECK CHALLENGES</p>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-8 py-10">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-zinc-100 mb-2">
            Break Through Your <span className="text-blue-400">Aerodynamic Wall</span>
          </h2>
          <p className="text-zinc-500 text-sm mb-10 max-w-lg">
            Real CFD bottlenecks. Surrogate-powered experimentation. Engineer-level insight. Like LeetCode — but for fluid dynamics.
          </p>

          {problems.length === 0 ? (
            <div className="text-zinc-600 text-sm">Loading problems...</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {problems.map((problem) => (
                <button
                  key={problem.id}
                  onClick={() => setCurrentProblem(problem)}
                  className="text-left bg-zinc-900 border border-zinc-800 rounded-lg p-6 hover:border-blue-500/50 hover:bg-zinc-900/80 transition-all duration-200 group"
                >
                  <div className="flex items-start justify-between mb-3">
                    <span className="text-xs text-blue-400 tracking-widest uppercase">
                      {problem.domain}
                    </span>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded border tracking-widest ${DIFFICULTY_STYLES[problem.difficulty]}`}>
                      {problem.difficulty.toUpperCase()}
                    </span>
                  </div>

                  <h3 className="text-base font-semibold text-zinc-100 mb-2 group-hover:text-blue-300 transition-colors">
                    {problem.title}
                  </h3>

                  <p className="text-xs text-zinc-500 leading-relaxed mb-4 line-clamp-3">
                    {problem.bottleneck}
                  </p>

                  <div className="flex flex-wrap gap-1 mb-4">
                    {problem.tags.map(tag => (
                      <span key={tag} className="text-xs text-zinc-600 border border-zinc-800 rounded px-2 py-0.5">
                        {tag}
                      </span>
                    ))}
                  </div>

                  <div className="pt-3 border-t border-zinc-800 flex justify-between items-center">
                    <span className="text-xs text-zinc-600">
                      Re = {problem.Re.toLocaleString()}
                    </span>
                    <span className="text-xs text-blue-400 group-hover:translate-x-1 transition-transform">
                      START →
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
