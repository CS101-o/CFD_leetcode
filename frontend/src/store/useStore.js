import { create } from 'zustand'

const useStore = create((set) => ({
  results: null,
  chatMessages: [],
  isLoading: false,

  setResults: (results) => set({ results }),
  addChatMessage: (message) => set((state) => ({
    chatMessages: [...state.chatMessages, message]
  })),
  setLoading: (isLoading) => set({ isLoading }),
}))

export default useStore
