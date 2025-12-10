import React from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, PerspectiveCamera } from '@react-three/drei'
import useStore from '../store/useStore'

function LeftPanel() {
  const { results } = useStore()

  return (
    <div className="w-full h-full bg-zinc-950 relative">
      {!results ? (
        <div className="w-full h-full flex items-center justify-center">
          <div className="text-center">
            <div className="text-6xl mb-4">🚀</div>
            <h2 className="text-2xl font-bold text-white mb-2">Ready for CFD</h2>
            <p className="text-zinc-400">
              Ask the AI tutor to generate an airfoil →
            </p>
          </div>
        </div>
      ) : (
        <Canvas>
          <PerspectiveCamera makeDefault position={[0, 0, 5]} />
          <OrbitControls />
          <ambientLight intensity={0.5} />
          <directionalLight position={[10, 10, 5]} intensity={1} />

          {/* Simple 3D airfoil representation */}
          <mesh>
            <boxGeometry args={[2, 0.3, 1]} />
            <meshStandardMaterial color="#3b82f6" />
          </mesh>

          <gridHelper args={[10, 10]} />
        </Canvas>
      )}

      <div className="absolute top-4 left-4 bg-zinc-900/80 px-4 py-2 rounded-lg">
        <p className="text-xs text-zinc-400">
          {results ? 'Drag to rotate • Scroll to zoom' : '3D Visualizer'}
        </p>
      </div>
    </div>
  )
}

export default LeftPanel
