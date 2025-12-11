import React, { useMemo } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, PerspectiveCamera, Line } from '@react-three/drei'
import * as THREE from 'three'
import useStore from '../store/useStore'

function Airfoil3D({ coordinates }) {
  // Convert 2D coordinates to 3D points for visualization
  const points = useMemo(() => {
    if (!coordinates || coordinates.length === 0) return []
    
    // Scale up the airfoil for better visibility
    const scale = 4
    return coordinates.map(([x, y]) => 
      new THREE.Vector3((x - 0.5) * scale, y * scale, 0)
    )
  }, [coordinates])

  if (points.length === 0) return null

  return (
    <group>
      {/* Airfoil outline */}
      <Line
        points={points}
        color="#3b82f6"
        lineWidth={3}
      />
      
      {/* Airfoil surface (filled) */}
      <mesh>
        <extrudeGeometry
          args={[
            new THREE.Shape(points.map(p => new THREE.Vector2(p.x, p.y))),
            { depth: 0.3, bevelEnabled: false }
          ]}
        />
        <meshStandardMaterial 
          color="#3b82f6" 
          metalness={0.3}
          roughness={0.4}
        />
      </mesh>
    </group>
  )
}

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
          <PerspectiveCamera makeDefault position={[0, 0, 8]} />
          <OrbitControls 
            enablePan={true}
            enableZoom={true}
            enableRotate={true}
          />
          
          {/* Lighting */}
          <ambientLight intensity={0.5} />
          <directionalLight position={[10, 10, 5]} intensity={1} />
          <directionalLight position={[-10, -10, -5]} intensity={0.5} />

          {/* Airfoil */}
          {results.coordinates && (
            <Airfoil3D coordinates={results.coordinates} />
          )}

          {/* Grid */}
          <gridHelper args={[10, 10]} />
        </Canvas>
      )}

      {/* Info overlay */}
      <div className="absolute top-4 left-4 bg-zinc-900/80 px-4 py-2 rounded-lg">
        <p className="text-xs text-zinc-400">
          {results ? 'Drag to rotate • Scroll to zoom' : '3D Visualizer'}
        </p>
      </div>

      {/* Results overlay */}
      {results && (
        <div className="absolute bottom-4 left-4 bg-zinc-900/90 px-4 py-3 rounded-lg space-y-1">
          <p className="text-xs text-zinc-500 font-semibold">Quick Stats</p>
          <p className="text-sm text-white">CL: {results.CL?.toFixed(4)}</p>
          <p className="text-sm text-white">CD: {results.CD?.toFixed(6)}</p>
          <p className="text-sm text-white">L/D: {results.L_D?.toFixed(1)}</p>
          <p className="text-xs text-zinc-400 mt-2">
            ⚡ {results.time_ms?.toFixed(1)}ms
          </p>
        </div>
      )}
    </div>
  )
}

export default LeftPanel