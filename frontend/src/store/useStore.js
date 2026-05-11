import { create } from 'zustand'

const useStore = create((set) => ({
  // Existing state
  results: null,
  chatMessages: [],
  isLoading: false,

  // FlowSense state
  currentProblem: null,
  problems: [],
  view: 'library', // 'library' | 'session'
  sessionStats: {
    experimentsRun: 0,
    casesTotal: 0,
    iterationCount: 0,
  },

  // Existing setters
  setResults: (results) => set({ results }),
  addChatMessage: (message) =>
    set((state) => ({ chatMessages: [...state.chatMessages, message] })),
  setLoading: (isLoading) => set({ isLoading }),

  // FlowSense setters
  setProblems: (problems) => set({ problems }),
  setCurrentProblem: (problem) => set({
    currentProblem: problem,
    view: 'session',
    chatMessages: [],
    results: null,
    sessionStats: { experimentsRun: 0, casesTotal: 0, iterationCount: 0 },
  }),
  setView: (view) => set({ view }),
  incrementStats: (cases = 0) => set((state) => ({
    sessionStats: {
      experimentsRun: state.sessionStats.experimentsRun + 1,
      casesTotal: state.sessionStats.casesTotal + cases,
      iterationCount: state.sessionStats.iterationCount + 1,
    }
  })),
  resetSession: () => set({
    currentProblem: null,
    view: 'library',
    chatMessages: [],
    results: null,
    sessionStats: { experimentsRun: 0, casesTotal: 0, iterationCount: 0 },
  }),
}))

export default useStore
