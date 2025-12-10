import React, { useState, useEffect, useRef } from 'react'
import useStore from '../store/useStore'
import axios from 'axios'

const API_URL = 'http://localhost:8000/api/v1'

function RightPanel() {
  const { chatMessages, addChatMessage, setResults, setLoading } = useStore()
  const [input, setInput] = useState('')
  const [isChatLoading, setIsChatLoading] = useState(false)
  const chatEndRef = useRef(null)

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(scrollToBottom, [chatMessages])

  // Show welcome message
  useEffect(() => {
    if (chatMessages.length === 0) {
      addChatMessage({
        role: 'assistant',
        content: 'Welcome! I\'m your AI CFD tutor. Try asking me to:\n\n• "simulate NACA 2412 at 8 degrees"\n• "run NACA 0012 at 5 degrees"'
      })
    }
  }, [])

  const handleSend = async () => {
    if (!input.trim()) return

    const userMessage = input.trim()
    setInput('')
    addChatMessage({ role: 'user', content: userMessage })
    setIsChatLoading(true)

    try {
      const response = await axios.post(`${API_URL}/chat/message`, {
        message: userMessage,
        current_results: null,
        conversation_history: chatMessages
      }, {
        headers: {
          'Content-Type': 'application/json'
        }
      })

      addChatMessage({
        role: 'assistant',
        content: response.data.response
      })

      if (response.data.simulation_triggered && response.data.simulation_results) {
        setResults(response.data.simulation_results)
      }
    } catch (error) {
      console.error('Chat API Error:', error.response?.data || error.message)
      addChatMessage({
        role: 'assistant',
        content: `Sorry, I encountered an error: ${error.response?.data?.detail || error.message}`
      })
    } finally {
      setIsChatLoading(false)
    }
  }

  return (
    <div className="w-full h-full bg-zinc-900 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-zinc-800">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <span>🤖</span> AI Tutor
        </h2>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {chatMessages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-3 ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-zinc-800 text-zinc-100'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}

        {isChatLoading && (
          <div className="flex justify-start">
            <div className="bg-zinc-800 rounded-lg p-3">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce delay-100" />
                <div className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce delay-200" />
              </div>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-zinc-800">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask a question..."
            className="flex-1 px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded-lg text-sm font-medium transition-colors"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}

export default RightPanel
