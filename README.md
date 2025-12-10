# AirfoilLearner 🛩️

**LeetCode for CFD** - An interactive learning platform for Computational Fluid Dynamics with an AI-powered tutor.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18-blue.svg)](https://reactjs.org/)

---

## 🚨 **CURRENT STATUS** (December 2024)

### ✅ What's Running Right Now

**Backend** (http://localhost:8000):
- FastAPI server ✅
- PostgreSQL database with 3 challenges ✅
- Redis cache ✅
- Health check endpoint ✅

**Frontend** (http://localhost:5173):
- Beautiful 3D UI with cyberpunk design ✅
- Interactive 3D NACA 0012 airfoil ✅
- Parameter controls (α, Reynolds) ✅
- AI chatbot interface ✅
- Metrics dashboard ✅

### ⚠️ What's NOT Working (Uses Mock Data)

**No Real CFD Yet:**
- Clicking "Run Simulation" shows **FAKE** results
- 3D airfoil is just geometry (no flow calculation)
- AI chatbot returns **canned responses**
- Challenge validation not implemented

**Critical Missing Pieces:**
1. XFoil integration (highest priority)
2. Backend API routes (commented out in code)
3. Real AI tutor connection
4. User authentication

### 🎯 What You Can Do Right Now

1. **Explore the UI**: Navigate the beautiful interface
2. **Adjust Parameters**: Move sliders and see values update
3. **View 3D Airfoil**: Drag to rotate, scroll to zoom
4. **Test Chatbot UI**: Type messages (gets mock responses)
5. **See Metrics Display**: Run simulation to see fake CL/CD/L_D

### 🚀 Next Immediate Steps

See [Current Status & Implementation Roadmap](#-current-status--implementation-roadmap) below for detailed development plan.

---

## 🎯 Overview

AirfoilLearner democratizes CFD education by combining:
- **Interactive Challenges**: LeetCode-style problems with progressive difficulty
- **Real CFD Solvers**: XFoil integration for accurate airfoil analysis
- **AI Tutor**: Conversational assistant powered by Claude/GPT-4 for personalized guidance
- **3D Visualization**: Beautiful airfoil geometry and flow visualization using Three.js
- **ML Acceleration**: Physics-Informed Neural Networks (PINNs) for fast predictions

**Target Audience**: Students, engineers, and enthusiasts learning aerodynamics and CFD.

---

## ✨ Key Features

### 🎓 Educational Focus
- **Progressive Challenges**: From basic lift prediction to complex optimization
- **Immediate Feedback**: Automated validation of simulation results
- **Conceptual Learning**: AI tutor explains *why*, not just *what*
- **Real-World Context**: Connect simulations to aircraft, wind turbines, etc.

### 🔬 Technical Capabilities
- **Industry-Standard Solvers**: XFoil (inviscid + viscous analysis)
- **Multiple Airfoil Types**: NACA 4-digit, 5-digit, custom geometries
- **Comprehensive Results**: Cl, Cd, Cm, pressure distributions, transition points
- **Polar Sweeps**: Automated angle-of-attack sweeps for complete airfoil characterization

### 🤖 AI-Powered Tutoring
- **Context-Aware**: Understands your simulation state and challenge
- **Socratic Teaching**: Asks questions to guide learning
- **Debugging Help**: Identifies common errors (convergence issues, unrealistic BCs)
- **Concept Explanations**: Boundary layers, stall, separation, Reynolds effects, etc.

### 📊 Visualizations
- **3D Airfoil Geometry**: Interactive Three.js rendering
- **Pressure Distributions**: D3.js charts of Cp vs x/c
- **Lift/Drag Curves**: Polar plots (Cl vs α, Cl vs Cd)
- **Streamlines** (coming soon): Flow field visualization

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│         React Frontend (TypeScript)          │
│   Three.js 3D Viz | D3.js Charts | TailwindCSS  │
└─────────────────┬───────────────────────────┘
                  │ REST API + WebSocket
┌─────────────────┴───────────────────────────┐
│         FastAPI Backend (Python)             │
│  ┌──────────┬──────────┬──────────────────┐ │
│  │  XFoil   │   PINN   │   AI Tutor       │ │
│  │  Solver  │  Models  │  (Claude/GPT)    │ │
│  └──────────┴──────────┴──────────────────┘ │
└─────────────────┬───────────────────────────┘
                  │
        ┌─────────┴─────────┐
        │   PostgreSQL DB    │
        │   (Users, Sims,    │
        │    Challenges)     │
        └───────────────────┘
```

**Tech Stack**:
- **Backend**: FastAPI, SQLAlchemy, XFoil, PyTorch (for PINNs)
- **Frontend**: React 18, TypeScript, Three.js, D3.js, TailwindCSS
- **AI**: OpenAI API / Anthropic Claude API
- **Database**: PostgreSQL
- **Caching**: Redis
- **Deployment**: Docker, Docker Compose

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **PostgreSQL 14+**
- **XFoil** ([installation guide](#xfoil-installation))
- **Redis** (optional, for production)

### Backend Setup

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your database credentials and API keys

# 5. Initialize database
python -m app.scripts.init_db

# 6. Seed challenges
python -m app.scripts.seed_challenges

# 7. Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at `http://localhost:8000`

### Frontend Setup

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Set up environment variables
cp .env.example .env
# Edit .env with API URL

# 4. Run development server
npm run dev
```

Frontend will be available at `http://localhost:5173`

### Docker Setup (Recommended for Production)

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## 🔧 XFoil Installation

### macOS
```bash
brew install xfoil
```

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install xfoil
```

### Windows
1. Download XFoil from [MIT website](https://web.mit.edu/drela/Public/web/xfoil/)
2. Extract to `C:\xfoil`
3. Add to PATH: `C:\xfoil\bin`

### Verify Installation
```bash
xfoil
# Should open XFoil prompt. Type 'quit' to exit.
```

---

## 📚 Challenge Categories

### Easy (100-150 points)
- **First Flight**: Basic lift prediction for NACA 0012
- **Symmetric vs Cambered**: Compare symmetric and cambered airfoils
- **Reynolds Effects**: Observe how Re affects performance

### Medium (200-300 points)
- **Stall Prediction**: Find CLmax and stall angle
- **Drag Analysis**: Understand drag components
- **Moment Coefficient**: Learn about pitching moments

### Hard (400-500 points)
- **Drag Optimization**: Minimize CD for target CL
- **Multi-Point Design**: Optimize across multiple conditions
- **Custom Airfoil**: Design airfoil from scratch

---

## 🤖 AI Tutor Capabilities

The AI tutor can help you with:

1. **Concept Explanations**
   ```
   User: "What is boundary layer separation?"
   AI: "Great question! Boundary layer separation occurs when..."
   ```

2. **Debugging Simulations**
   ```
   User: "My simulation won't converge at α=20°"
   AI: "High angles like 20° often cause convergence issues because..."
   ```

3. **Challenge Hints**
   ```
   User: "I'm stuck on the stall prediction challenge"
   AI: "Let's think about what happens to the Cp distribution as α increases..."
   ```

4. **Result Analysis**
   ```
   User: "Why is my CD so high?"
   AI: "Let's examine your results. I see you're using Re=1e5, which is quite low..."
   ```

---

## 📖 API Documentation

Once the backend is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Key Endpoints

#### Authentication
- `POST /api/v1/auth/register` - Create account
- `POST /api/v1/auth/login` - Login (returns JWT)

#### Challenges
- `GET /api/v1/challenges` - List all challenges
- `GET /api/v1/challenges/{id}` - Get challenge details
- `POST /api/v1/challenges/{id}/submit` - Submit solution

#### Simulations
- `POST /api/v1/simulations` - Create simulation
- `GET /api/v1/simulations/{id}` - Get results
- `GET /api/v1/simulations/{id}/status` - Check status

#### AI Tutor
- `POST /api/v1/chat` - Send message to AI tutor
- `GET /api/v1/chat/history` - Get conversation history

---

## 🧪 Testing XFoil Integration

```bash
cd backend
python -m app.utils.xfoil_wrapper
```

This will run a test simulation for NACA 0012 and display results.

---

## 🎨 Frontend Structure

```
frontend/src/
├── components/
│   ├── airfoil/          # Airfoil selection and display
│   ├── challenge/        # Challenge list and details
│   ├── chat/             # AI chat interface
│   ├── visualization/    # Charts and 3D views
│   └── common/           # Reusable components
├── pages/
│   ├── Home.tsx          # Landing page
│   ├── Playground.tsx    # Main simulation interface
│   └── Challenges.tsx    # Challenge browser
├── hooks/                # Custom React hooks
├── services/             # API client functions
└── store/                # Zustand state management
```

---

## 🔬 Research Contributions

This platform integrates cutting-edge research:

1. **Physics-Informed Neural Networks (PINNs)**: ML-accelerated airfoil predictions
2. **Neural Operators**: Fast surrogate models for CFD (collaboration with U of Toronto)
3. **Conversational AI for STEM Education**: Novel application of LLMs in engineering education

**Academic Context**:
- Part of Computer Science degree at University of Manchester
- Collaboration with University of Toronto researchers
- Target: Demo by February 2026

---

## 📊 Current Status & Implementation Roadmap

### ✅ **COMPLETED** (December 2024)

#### Backend Infrastructure
- ✅ FastAPI server running on port 8000
- ✅ PostgreSQL database initialized with tables (users, simulations, challenges, submissions, chat_messages)
- ✅ Redis cache running in Docker
- ✅ Database seeded with 3 challenges (Easy, Medium, Hard)
- ✅ Health check endpoint (`/health`)
- ✅ Environment configuration with .env

#### Frontend Application
- ✅ **React + Vite** development environment
- ✅ **3-Panel Cyberpunk UI Layout**:
  - Left Panel: Challenge brief, parameter controls, presets
  - Center Canvas: Interactive 3D airfoil with Three.js
  - Right Panel: Live metrics + AI chatbot
- ✅ **3D Visualization**: NACA 0012 airfoil using analytical formula
  - Interactive orbital camera (drag to rotate, scroll to zoom)
  - Metallic blue shader with glow effects
  - Grid floor for spatial reference
- ✅ **Simulation Controls**: Sliders for α (-5° to 20°) and Reynolds (500k to 5M)
- ✅ **AI Chatbot Interface**:
  - Chat history display
  - Quick prompt suggestions
  - Message input with send button
- ✅ **Metrics Dashboard**: CL, CD, L/D ratio display cards
- ✅ **Glassmorphism Design**: Backdrop blur, neon accents, custom scrollbars
- ✅ **State Management**: Zustand store for global state
- ✅ **Mock API**: Simulated 2-second delay with fake CFD results

### 🚧 **IN PROGRESS / NEXT STEPS**

#### Critical Path to MVP (Priority 1)

**1. XFoil Integration** ⚠️ HIGHEST PRIORITY
- [ ] Install XFoil on system (`brew install xfoil` on macOS)
- [ ] Create `/backend/app/utils/xfoil_wrapper.py`:
  ```python
  # Python wrapper to call XFoil subprocess
  # Generate airfoil coordinates
  # Run panel method analysis
  # Parse output files for CL, CD, Cp distribution
  ```
- [ ] Create `/backend/app/services/simulation_service.py`:
  ```python
  # Handle simulation requests
  # Call xfoil_wrapper
  # Store results in database
  # Return formatted response
  ```
- [ ] Implement backend API endpoint: `POST /api/v1/simulations`
- [ ] Test XFoil with NACA 0012 at α=5°, Re=1e6
- [ ] Handle convergence failures gracefully

**2. Backend API Routes** (Depends on XFoil)
- [ ] Uncomment routers in `/backend/app/main.py` (lines 73-77)
- [ ] Implement `/backend/app/api/endpoints/simulations.py`:
  - `POST /simulations` - Create new simulation
  - `GET /simulations/{id}` - Get results
  - `GET /simulations/{id}/status` - Check if running/complete
- [ ] Implement `/backend/app/api/endpoints/challenges.py`:
  - `GET /challenges` - List all challenges
  - `GET /challenges/{id}` - Get challenge details
  - `POST /challenges/{id}/submit` - Validate solution
- [ ] Implement `/backend/app/api/endpoints/chat.py`:
  - `POST /chat` - Send message to AI tutor (Anthropic/OpenAI)

**3. Frontend-Backend Integration**
- [ ] Update `/frontend/src/services/api.js`:
  - Replace mock `simulationAPI.run()` with real axios call
  - Replace mock `challengesAPI.getAll()` with real API
  - Replace mock `chatAPI.sendMessage()` with real AI API
- [ ] Add error handling for failed simulations
- [ ] Add loading states with progress indicators
- [ ] Test end-to-end flow: UI → API → XFoil → Results → UI

**4. AI Tutor Integration**
- [ ] Add Anthropic API key to `.env`
- [ ] Implement `/backend/app/services/ai_tutor_service.py`:
  ```python
  # System prompt: "You are a CFD tutor..."
  # Context injection: current simulation params, results
  # Streaming responses (optional)
  ```
- [ ] Connect chatbot UI to real AI responses
- [ ] Add conversation history persistence

### 🎯 **MVP Features** (Phase 1 - Target: February 2026)

**Essential for Demo:**
- [ ] User authentication (register, login, JWT tokens)
- [ ] Challenge validation (check if CL, CD meet criteria)
- [ ] Progress tracking (completed challenges, scores)
- [ ] Cp distribution charts (D3.js/Recharts)
- [ ] Polar plots (CL vs α, Cl vs Cd)
- [ ] 10-15 pre-built challenges
- [ ] Leaderboard (top scorers per challenge)

**Nice-to-Have for Demo:**
- [ ] Animated particle streamlines around airfoil
- [ ] Flow velocity color mapping
- [ ] Confetti animation on challenge completion
- [ ] Sound effects (optional)
- [ ] Screenshot/export results feature

### 🚀 **Post-MVP Enhancements** (Phase 2)

**Advanced CFD Features:**
- [ ] Multiple airfoil types (NACA 5-digit, custom coordinates)
- [ ] Viscous/inviscid toggle
- [ ] Transition prediction (XFoil Ncrit parameter)
- [ ] Flap deflection simulation
- [ ] Multi-element airfoils (slat + main + flap)

**PINN Integration:**
- [ ] Train PyTorch model on XFoil dataset
- [ ] Fast prediction mode (<100ms vs XFoil's ~5s)
- [ ] Uncertainty quantification
- [ ] Active learning (suggest new training points)

**Visualization Upgrades:**
- [ ] 3D streamlines using particle systems
- [ ] Pressure heatmap on airfoil surface
- [ ] Boundary layer thickness visualization
- [ ] Vorticity contours
- [ ] Animation of flow evolution

**Educational Features:**
- [ ] Tutorial mode with step-by-step guidance
- [ ] Concept library (boundary layer, stall, etc.)
- [ ] Video explanations embedded in challenges
- [ ] Code snippets for custom analysis
- [ ] Export simulation data (CSV, JSON)

### 🌟 **Long-Term Vision** (Phase 3)

**Platform Expansion:**
- [ ] OpenFOAM integration for 3D CFD
- [ ] Wing/fuselage simulations
- [ ] Wind turbine blade design
- [ ] Propeller analysis
- [ ] Integration with university curricula

**Community Features:**
- [ ] User-created challenges
- [ ] Peer review system
- [ ] Discussion forums
- [ ] Challenge marketplace
- [ ] Instructor dashboard for course management

**Advanced ML:**
- [ ] Neural operators for instant field predictions
- [ ] Generative design (AI suggests optimal airfoils)
- [ ] Sensitivity analysis (automatic parameter sweeps)
- [ ] Multi-objective optimization (Pareto fronts)

### 🐛 **Known Issues & Limitations**

**Current Limitations:**
- ⚠️ No real CFD - frontend uses mock data
- ⚠️ 3D airfoil is just geometry, no flow field
- ⚠️ AI chatbot returns canned responses
- ⚠️ Backend API routes not implemented yet
- ⚠️ No user authentication
- ⚠️ Database has no real user data
- ⚠️ XFoil not installed/integrated

**Technical Debt:**
- Frontend uses older Tailwind CSS (needs @tailwindcss/postcss)
- Python 3.9 instead of 3.10+ (some type hints won't work)
- No error boundaries in React
- No loading skeletons for better UX
- Mock data has hardcoded values

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Areas for Contribution**:
- New challenge definitions
- Frontend components
- Visualization improvements
- Documentation
- Bug fixes

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- **XFoil**: Mark Drela (MIT) - Industry-standard airfoil analysis tool
- **AeroPython**: Lorena Barba (GWU) - Educational inspiration
- **SimScale**: UI/UX inspiration for browser-based CFD
- **ChatCFD**: Research inspiration for AI-assisted CFD

---

## 📧 Contact

**Kaan Oktem**
- University: University of Manchester (Computer Science, graduating June 2026)
- GitHub: [Your GitHub]
- Email: [Your Email]

**Collaboration**:
- Open to collaborations with educators and researchers
- Interested in integrating this with university CFD courses
- Looking for feedback from CFD professionals

---

## 🌟 Why AirfoilLearner?

Traditional CFD learning is hard:
- ❌ Expensive commercial software (ANSYS, STAR-CCM+)
- ❌ Steep learning curves (CAD, meshing, solvers)
- ❌ Limited feedback and guidance
- ❌ No progressive skill building

**AirfoilLearner solves this:**
- ✅ Free and open-source
- ✅ Browser-based, no installation
- ✅ AI tutor provides instant help
- ✅ Gamified learning with challenges
- ✅ Focus on concepts, not software complexity

**Our Mission**: Make CFD education accessible to everyone, everywhere.

---

*Built with ❤️ for the CFD and education communities*
