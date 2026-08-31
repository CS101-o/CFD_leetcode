import { create } from 'zustand'

// Persist the session id so return visits are attributable in the design log
function getSessionId() {
  try {
    let sid = localStorage.getItem('al_session_id')
    if (!sid) {
      sid = crypto.randomUUID()
      localStorage.setItem('al_session_id', sid)
    }
    return sid
  } catch {
    return crypto.randomUUID()
  }
}

const useStore = create((set) => ({
  results: null,
  polarData: null,
  chatMessages: [],
  isLoading: false,

  // Session identity
  participantId: '',
  sessionId: getSessionId(),

  // FlowSense state
  currentProblem: null,
  problems: [],
  view: 'library',
  activeMode: 'viz',
  allResults: [],     // every simulation run — feeds Pareto explorer

  sessionStats: {
    experimentsRun: 0,
    casesTotal: 0,
    iterationCount: 0,
  },

  solvedProblems: new Set(),

  // AI tutor chat (Module01 design loop)
  aiMessages: [],   // [{type:'assessment'|'user'|'tutor', text, compliance, airfoil, ts}]
  aiChatOpen: false,
  aiAssessing: false,

  setResults: (results) => set({ results }),
  setPolarData: (polarData) => set({ polarData }),
  addChatMessage: (message) =>
    set((state) => ({ chatMessages: [...state.chatMessages, message] })),
  setLoading: (isLoading) => set({ isLoading }),
  setParticipantId: (participantId) => set({ participantId }),
  setActiveMode: (activeMode) => set({ activeMode }),

  // Append a simulation result to the shared pool (used by Pareto)
  addResult: (result) => set((state) => ({ allResults: [...state.allResults, result] })),

  markSolved: (problemId) => set((state) => ({
    solvedProblems: new Set([...state.solvedProblems, problemId]),
  })),

  setProblems: (problems) => set({ problems }),
  setCurrentProblem: (problem) => set({
    currentProblem: problem,
    view: 'session',
    chatMessages: [],
    results: null,
    polarData: null,
    allResults: [],
    activeMode: 'sliders',
    aiMessages: [],
    aiChatOpen: false,
    aiAssessing: false,
    sessionStats: { experimentsRun: 0, casesTotal: 0, iterationCount: 0 },
  }),
  setView: (view) => set({ view }),
  incrementStats: (cases = 0) => set((state) => ({
    sessionStats: {
      experimentsRun: state.sessionStats.experimentsRun + 1,
      casesTotal: state.sessionStats.casesTotal + cases,
      iterationCount: state.sessionStats.iterationCount + 1,
    },
  })),
  resetSession: () => set({
    currentProblem: null,
    view: 'library',
    chatMessages: [],
    results: null,
    allResults: [],
    activeMode: 'viz',
    aiMessages: [],
    aiChatOpen: false,
    aiAssessing: false,
    sessionStats: { experimentsRun: 0, casesTotal: 0, iterationCount: 0 },
  }),

  addAiMessage: (msg) => set((state) => ({
    aiMessages: [...state.aiMessages, { ...msg, ts: Date.now() }],
    aiChatOpen: true,
    aiAssessing: false,
  })),
  setAiChatOpen: (open) => set({ aiChatOpen: open }),
  setAiAssessing: (v) => set({ aiAssessing: v }),
}))

export default useStore
