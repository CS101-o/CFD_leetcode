# AirfoilLearner - System Architecture

## Overview
AirfoilLearner is a LeetCode-style educational platform for learning Computational Fluid Dynamics (CFD) with an integrated AI tutor. The platform provides interactive challenges, real-time simulations, and conversational AI guidance.

## System Architecture

### High-Level Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT (Browser)                         │
│  ┌────────────────┐  ┌──────────────┐  ┌─────────────────┐ │
│  │  React UI      │  │  Three.js    │  │   D3.js         │ │
│  │  Components    │  │  3D Viz      │  │   Charts        │ │
│  └────────────────┘  └──────────────┘  └─────────────────┘ │
│                          │                                   │
│                     WebSocket & REST API                     │
└──────────────────────────┼──────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────┐
│                     BACKEND (FastAPI)                        │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              API Gateway & Routing                       ││
│  └─────────────────────────────────────────────────────────┘│
│                           │                                  │
│  ┌──────────────┬─────────┴─────────┬──────────────────┐   │
│  │              │                   │                  │   │
│  │   Solver     │    Challenge      │    AI Tutor      │   │
│  │   Service    │    Service        │    Service       │   │
│  │              │                   │                  │   │
│  │  ┌────────┐  │  ┌─────────────┐ │  ┌────────────┐  │   │
│  │  │ XFoil  │  │  │ Validation  │ │  │ OpenAI/    │  │   │
│  │  └────────┘  │  │ Engine      │ │  │ Anthropic  │  │   │
│  │  ┌────────┐  │  └─────────────┘ │  │ API        │  │   │
│  │  │ PINN   │  │                   │  └────────────┘  │   │
│  │  │ Models │  │                   │                  │   │
│  │  └────────┘  │                   │                  │   │
│  └──────────────┴───────────────────┴──────────────────┘   │
│                           │                                  │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Database Layer (PostgreSQL)                 ││
│  │  - Users & Auth   - Challenges    - Solutions           ││
│  │  - Progress       - Leaderboards  - Simulations         ││
│  └─────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Frontend
- **React 18+** with TypeScript
- **Three.js** for 3D airfoil visualization
- **D3.js** for charts (pressure distribution, Cp plots)
- **TailwindCSS** for styling
- **React Query** for state management and API calls
- **Zustand** for lightweight global state
- **Socket.io-client** for real-time simulation updates

### Backend
- **FastAPI** (Python 3.10+)
- **XFoil** via subprocess wrapper
- **PyTorch** for PINN model inference
- **SQLAlchemy** ORM
- **PostgreSQL** database
- **Redis** for caching and job queuing
- **Celery** for async task processing (long simulations)
- **Socket.io** for WebSocket connections

### AI Integration
- **OpenAI API** (GPT-4) or **Anthropic API** (Claude)
- Custom prompt engineering for CFD tutoring
- RAG (Retrieval-Augmented Generation) with CFD knowledge base

### DevOps & Deployment
- **Docker** & Docker Compose for containerization
- **GitHub Actions** for CI/CD
- **AWS/GCP** for cloud hosting (recommended: AWS EC2 + S3)
- **Nginx** as reverse proxy
- **Let's Encrypt** for SSL

## Core Components

### 1. Solver Service
Handles CFD simulations with multiple backends:
- **XFoil**: Primary solver for 2D airfoil analysis (inviscid + viscous)
- **PINN Models**: ML-accelerated predictions for fast feedback
- **OpenFOAM** (future): Advanced 3D simulations

**Workflow:**
```
User Input → Geometry Generation → Mesh (XFoil handles internally)
          → Solver Execution → Post-processing → Results
```

### 2. Challenge System
LeetCode-style problem definitions:
- **Difficulty Levels**: Easy, Medium, Hard
- **Categories**: Inviscid flow, viscous effects, optimization, design
- **Validation**: Automated checking of Cl, Cd, Cm, etc.
- **Hints**: Progressive AI-powered hints

**Challenge Schema:**
```python
{
  "id": "naca-0012-stall",
  "title": "Predict Stall Angle for NACA 0012",
  "difficulty": "medium",
  "description": "...",
  "constraints": {
    "reynolds": 1e6,
    "mach": 0.0,
    "alpha_range": [-5, 20]
  },
  "validation": {
    "target_cl_max": 1.45,
    "tolerance": 0.05
  }
}
```

### 3. AI Tutor Service
Conversational AI with CFD domain expertise:
- **Context-aware**: Understands user's simulation state
- **Explanatory**: Explains physics concepts (boundary layers, separation, etc.)
- **Debugging**: Identifies common errors (convergence issues, unrealistic BCs)
- **Guidance**: Suggests next steps and learning resources

**Features:**
- Chat history persistence
- Code snippet generation (Python scripts for automation)
- Formula rendering (LaTeX)
- Interactive diagrams

### 4. User Progress Tracking
- **Profile**: Username, institution, skill level
- **Achievements**: Badges for completing challenges
- **Statistics**: Total simulations, accuracy, time spent
- **Leaderboards**: Global and category-specific

## Data Models

### User
```python
class User:
    id: UUID
    username: str
    email: str
    hashed_password: str
    institution: Optional[str]
    skill_level: Enum["beginner", "intermediate", "advanced"]
    created_at: datetime
    challenges_completed: List[UUID]
```

### Challenge
```python
class Challenge:
    id: UUID
    title: str
    difficulty: Enum["easy", "medium", "hard"]
    category: str
    description: str
    constraints: JSON
    validation_criteria: JSON
    hints: List[str]
    reference_solution: JSON
```

### Simulation
```python
class Simulation:
    id: UUID
    user_id: UUID
    challenge_id: Optional[UUID]
    airfoil_type: str
    parameters: JSON  # {alpha, Re, Ma, ...}
    solver_type: Enum["xfoil", "pinn", "openfoam"]
    status: Enum["queued", "running", "completed", "failed"]
    results: JSON  # {Cl, Cd, Cp_distribution, ...}
    created_at: datetime
    completed_at: Optional[datetime]
```

### ChatMessage
```python
class ChatMessage:
    id: UUID
    user_id: UUID
    simulation_id: Optional[UUID]
    role: Enum["user", "assistant"]
    content: str
    timestamp: datetime
```

## API Endpoints

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - Login with JWT
- `POST /auth/refresh` - Refresh token
- `GET /auth/me` - Get current user

### Challenges
- `GET /challenges` - List all challenges
- `GET /challenges/{id}` - Get challenge details
- `POST /challenges/{id}/submit` - Submit solution
- `GET /challenges/{id}/leaderboard` - Get leaderboard

### Simulations
- `POST /simulations` - Create new simulation
- `GET /simulations/{id}` - Get simulation results
- `GET /simulations/{id}/status` - Check simulation status (polling)
- `DELETE /simulations/{id}` - Cancel simulation

### Airfoils
- `GET /airfoils/presets` - List preset airfoils (NACA, etc.)
- `POST /airfoils/generate` - Generate custom airfoil geometry
- `GET /airfoils/{id}/coordinates` - Get airfoil coordinates

### AI Tutor
- `POST /chat` - Send message to AI tutor
- `GET /chat/history` - Get chat history
- `POST /chat/explain` - Explain specific CFD concept

### WebSocket Events
- `simulation:progress` - Real-time simulation progress
- `simulation:complete` - Simulation completed
- `chat:message` - AI tutor response

## Security Considerations
- **Authentication**: JWT with refresh tokens
- **Rate Limiting**: Prevent API abuse (max simulations per hour)
- **Input Validation**: Sanitize all user inputs (prevent code injection in XFoil)
- **Sandboxing**: Run solvers in isolated containers
- **API Key Management**: Secure storage for OpenAI/Anthropic keys

## Scalability Strategy
- **Horizontal Scaling**: Stateless API servers behind load balancer
- **Job Queue**: Celery with Redis for async task distribution
- **Caching**: Redis for frequently accessed data (preset airfoils, challenge definitions)
- **CDN**: Static assets (React build) served via CloudFront/CloudFlare
- **Database**: Read replicas for leaderboards/analytics

## MVP Feature Priority

### Phase 1 (February 2026 Demo)
✅ Core Features:
- User authentication (register/login)
- 5-10 preset challenges (NACA airfoils)
- XFoil integration (inviscid + viscous)
- Basic 3D airfoil visualization (Three.js)
- AI chat tutor (OpenAI/Anthropic API)
- Simple progress tracking

### Phase 2 (Post-Demo)
- PINN model integration
- Advanced visualizations (streamlines, vorticity)
- Community features (leaderboards, discussions)
- Challenge editor for instructors
- OpenFOAM integration

### Phase 3 (Future)
- Mobile app (React Native)
- Collaborative challenges
- Custom airfoil design tool
- Integration with university curricula

## Development Timeline (MVP)

**Weeks 1-2**: Backend architecture + XFoil integration
**Weeks 3-4**: Frontend UI + Three.js visualization
**Weeks 5-6**: Challenge system + validation
**Weeks 7-8**: AI tutor integration
**Weeks 9-10**: Testing + deployment + demo prep

## Success Metrics
- **Engagement**: Users complete ≥3 challenges
- **AI Tutor Usage**: ≥50% of users interact with chat
- **Accuracy**: XFoil results validated against known benchmarks
- **Performance**: Simulations complete in <30 seconds (XFoil)
- **Retention**: ≥30% weekly active users (post-launch)
