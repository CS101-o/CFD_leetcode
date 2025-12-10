# AirfoilLearner - Project Structure

```
CFDLeetcode/
├── backend/                      # FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── dependencies.py  # Dependency injection (auth, db, etc.)
│   │   │   └── endpoints/
│   │   │       ├── __init__.py
│   │   │       ├── auth.py      # Authentication endpoints
│   │   │       ├── challenges.py
│   │   │       ├── simulations.py
│   │   │       ├── airfoils.py
│   │   │       └── chat.py      # AI tutor endpoints
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py        # Settings (env vars, API keys)
│   │   │   ├── security.py      # JWT, password hashing
│   │   │   └── database.py      # Database connection
│   │   ├── models/               # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── challenge.py
│   │   │   ├── simulation.py
│   │   │   └── chat.py
│   │   ├── schemas/              # Pydantic schemas (request/response)
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── challenge.py
│   │   │   ├── simulation.py
│   │   │   └── chat.py
│   │   ├── services/             # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── solver_service.py     # XFoil, PINN orchestration
│   │   │   ├── challenge_service.py  # Challenge validation
│   │   │   ├── ai_tutor_service.py   # AI chat integration
│   │   │   ├── airfoil_service.py    # Geometry generation
│   │   │   └── user_service.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── xfoil_wrapper.py      # XFoil subprocess wrapper
│   │       ├── naca_generator.py     # NACA airfoil equations
│   │       └── validators.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_xfoil.py
│   │   ├── test_challenges.py
│   │   └── test_api.py
│   ├── scripts/
│   │   ├── init_db.py           # Database initialization
│   │   └── seed_challenges.py   # Load preset challenges
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/                     # React frontend
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── components/
│   │   │   ├── airfoil/
│   │   │   │   ├── AirfoilSelector.tsx
│   │   │   │   ├── AirfoilCanvas.tsx      # Three.js 3D view
│   │   │   │   └── ParameterControls.tsx  # Alpha, Re, Ma sliders
│   │   │   ├── challenge/
│   │   │   │   ├── ChallengeList.tsx
│   │   │   │   ├── ChallengeDetail.tsx
│   │   │   │   └── Leaderboard.tsx
│   │   │   ├── chat/
│   │   │   │   ├── ChatInterface.tsx
│   │   │   │   ├── MessageBubble.tsx
│   │   │   │   └── LatexRenderer.tsx     # For formulas
│   │   │   ├── visualization/
│   │   │   │   ├── PressureChart.tsx     # D3.js Cp plot
│   │   │   │   ├── StreamlineView.tsx    # Future: streamlines
│   │   │   │   └── ResultsPanel.tsx      # Cl, Cd, Cm display
│   │   │   ├── layout/
│   │   │   │   ├── Navbar.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   └── Footer.tsx
│   │   │   └── common/
│   │   │       ├── Button.tsx
│   │   │       ├── Card.tsx
│   │   │       └── Loader.tsx
│   │   ├── pages/
│   │   │   ├── Home.tsx
│   │   │   ├── Playground.tsx         # Main simulation interface
│   │   │   ├── Challenges.tsx
│   │   │   ├── Profile.tsx
│   │   │   └── Login.tsx
│   │   ├── hooks/
│   │   │   ├── useSimulation.ts       # Simulation API calls
│   │   │   ├── useChat.ts             # AI chat hook
│   │   │   └── useAuth.ts
│   │   ├── services/
│   │   │   ├── api.ts                 # Axios instance
│   │   │   ├── simulationService.ts
│   │   │   ├── challengeService.ts
│   │   │   └── chatService.ts
│   │   ├── store/
│   │   │   ├── authStore.ts           # Zustand store
│   │   │   └── simulationStore.ts
│   │   ├── types/
│   │   │   ├── simulation.ts
│   │   │   ├── challenge.ts
│   │   │   └── airfoil.ts
│   │   ├── utils/
│   │   │   ├── formatters.ts
│   │   │   └── constants.ts
│   │   └── styles/
│   │       └── globals.css
│   ├── public/
│   │   ├── airfoil-presets/          # JSON files for presets
│   │   └── images/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
├── shared/                          # Shared resources
│   ├── challenges/
│   │   ├── easy/
│   │   │   ├── naca0012-basic.json
│   │   │   └── symmetric-cl.json
│   │   ├── medium/
│   │   │   ├── stall-prediction.json
│   │   │   └── drag-minimization.json
│   │   └── hard/
│   │       └── multi-element-airfoil.json
│   ├── airfoils/
│   │   └── presets.json            # NACA 0012, 2412, 4412, etc.
│   └── docs/
│       ├── API.md                  # API documentation
│       └── CFD_CONCEPTS.md         # Knowledge base for AI tutor
│
├── docker-compose.yml
├── .gitignore
├── README.md
├── ARCHITECTURE.md
└── LICENSE
```

## Key Design Decisions

### Backend Structure
- **Services Layer**: Business logic separated from API routes (clean architecture)
- **Dependency Injection**: FastAPI's dependency system for auth, db sessions
- **Async/Await**: Leverage FastAPI's async capabilities for I/O-bound operations
- **Pydantic Schemas**: Separate schemas for request validation and response serialization

### Frontend Structure
- **Component-Based**: Reusable, atomic components
- **Custom Hooks**: Encapsulate API logic and state management
- **Zustand**: Lightweight alternative to Redux for global state
- **React Query**: Server state management with caching

### Shared Resources
- **Challenge Definitions**: JSON format for easy editing by instructors
- **Airfoil Presets**: Standardized format for geometry data
- **Documentation**: Single source of truth for CFD concepts (used by AI tutor)

## File Naming Conventions
- **Python**: `snake_case.py`
- **React Components**: `PascalCase.tsx`
- **Hooks**: `useCamelCase.ts`
- **Utilities**: `camelCase.ts`
- **Types**: `camelCase.ts`

## Next Steps
1. Set up backend dependencies (FastAPI, SQLAlchemy, etc.)
2. Implement XFoil wrapper
3. Create database models and migrations
4. Build React app scaffold with Vite
5. Implement Three.js airfoil visualization
