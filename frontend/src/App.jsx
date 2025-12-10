import React from 'react'
import LeftPanel from './components/LeftPanel'
import RightPanel from './components/RightPanel'

function App() {
  return (
    <div className="w-screen h-screen flex bg-zinc-950 overflow-hidden">
      {/* LEFT: 3D Visualizer */}
      <div className="flex-1 h-full border-r border-zinc-800">
        <LeftPanel />
      </div>

      {/* RIGHT: Chatbot */}
      <div className="w-96 h-full">
        <RightPanel />
      </div>
    </div>
  )
}

export default App
