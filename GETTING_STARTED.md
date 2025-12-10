# Getting Started with AirfoilLearner

This guide will help you set up and run AirfoilLearner on your local machine.

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

### Required
- **Python 3.10 or higher** ([Download](https://www.python.org/downloads/))
- **Node.js 18 or higher** ([Download](https://nodejs.org/))
- **PostgreSQL 14 or higher** ([Download](https://www.postgresql.org/download/))
- **Git** ([Download](https://git-scm.com/downloads))

### Optional (but recommended)
- **Docker & Docker Compose** ([Download](https://www.docker.com/get-started)) - For easy deployment
- **Redis** ([Installation Guide](https://redis.io/docs/getting-started/)) - For caching and background jobs

---

## 🛠️ Installation Methods

Choose one of the following installation methods:

### Option 1: Docker (Recommended for Beginners)

**Easiest way to get started!**

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/AirfoilLearner.git
cd AirfoilLearner

# 2. Create .env file with your API keys
cp backend/.env.example backend/.env
# Edit backend/.env and add your ANTHROPIC_API_KEY or OPENAI_API_KEY

# 3. Start all services
docker-compose up -d

# 4. Wait for services to be ready (30-60 seconds)
docker-compose logs -f

# 5. Initialize database
docker-compose exec backend python -m app.scripts.init_db
docker-compose exec backend python -m app.scripts.seed_challenges
```

**Access the application:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

**Stop services:**
```bash
docker-compose down
```

---

### Option 2: Local Development Setup

**Best for active development and debugging**

#### Step 1: Install XFoil

**macOS:**
```bash
brew install xfoil
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install xfoil
```

**Windows:**
1. Download XFoil from [MIT website](https://web.mit.edu/drela/Public/web/xfoil/)
2. Extract to `C:\xfoil`
3. Add `C:\xfoil\bin` to your PATH environment variable

**Verify installation:**
```bash
xfoil
# Should show XFoil prompt. Type 'quit' to exit.
```

#### Step 2: Set Up PostgreSQL

**Create database:**
```bash
# Login to PostgreSQL
psql postgres

# Create user and database
CREATE USER airfoil_user WITH PASSWORD 'your_password_here';
CREATE DATABASE airfoil_db OWNER airfoil_user;
GRANT ALL PRIVILEGES ON DATABASE airfoil_db TO airfoil_user;
\q
```

#### Step 3: Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
```

**Edit `backend/.env`** with your configuration:
```bash
# Database
DATABASE_URL=postgresql+asyncpg://airfoil_user:your_password_here@localhost:5432/airfoil_db
DATABASE_URL_SYNC=postgresql://airfoil_user:your_password_here@localhost:5432/airfoil_db

# Security (generate a random secret key)
SECRET_KEY=your-secret-key-here

# AI Provider (choose one)
ANTHROPIC_API_KEY=sk-ant-...  # Get from https://console.anthropic.com/
# OR
OPENAI_API_KEY=sk-...  # Get from https://platform.openai.com/

AI_PROVIDER=anthropic  # or "openai"
AI_MODEL=claude-3-5-sonnet-20241022  # or "gpt-4"

# XFoil
XFOIL_PATH=xfoil  # or full path if not in PATH
```

**Initialize database:**
```bash
python -m app.scripts.init_db
python -m app.scripts.seed_challenges
```

**Run backend server:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at http://localhost:8000

#### Step 4: Frontend Setup

```bash
# Navigate to frontend directory (in a new terminal)
cd frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env
```

**Edit `frontend/.env`:**
```bash
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

**Run frontend server:**
```bash
npm run dev
```

Frontend will be available at http://localhost:5173

---

## ✅ Verify Installation

### 1. Test Backend API

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "ai_provider": "anthropic",
  "xfoil_available": true
}
```

### 2. Test XFoil Integration

```bash
cd backend
python -m app.utils.xfoil_wrapper
```

You should see output like:
```
Running XFoil analysis for NACA 0012 at α=5°, Re=1e6...
Results:
  Converged: True
  CL: 0.5470
  CD: 0.008200
  CM: 0.0000
  L/D: 66.71
```

### 3. Test AI Tutor

```bash
cd backend
python -m app.services.ai_tutor_service
```

This will test the AI tutor with sample queries.

### 4. Open Frontend

Navigate to http://localhost:5173 in your browser. You should see:
- AirfoilLearner landing page
- Navigation menu
- Challenge list (if seeded successfully)

---

## 🎓 Your First Simulation

### Using the API (via curl or Postman)

```bash
# 1. Register a user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "securepassword123"
  }'

# 2. Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "securepassword123"
  }'
# Save the returned access_token

# 3. Run a simulation
curl -X POST http://localhost:8000/api/v1/simulations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "airfoil_type": "naca_4digit",
    "airfoil_designation": "0012",
    "alpha": 5.0,
    "reynolds": 1e6,
    "solver_type": "xfoil",
    "viscous": true
  }'
# Save the returned simulation_id

# 4. Check simulation results
curl http://localhost:8000/api/v1/simulations/{simulation_id} \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Using the Frontend

1. **Navigate to http://localhost:5173**
2. **Register/Login** (top-right corner)
3. **Go to Playground** (main simulation interface)
4. **Select airfoil**: Choose "NACA 0012" from dropdown
5. **Set parameters**:
   - Angle of attack: 5°
   - Reynolds number: 1,000,000
   - Mach number: 0.0
6. **Click "Run Simulation"**
7. **View results**: CL, CD, CM, and Cp distribution chart

---

## 🎯 Try Your First Challenge

1. **Navigate to Challenges page** (http://localhost:5173/challenges)
2. **Select "First Flight: NACA 0012 Lift Prediction"** (Easy difficulty)
3. **Read the challenge description** carefully
4. **Set up the simulation** according to constraints
5. **Run the simulation**
6. **Submit your solution**
7. **Get immediate feedback** on whether you met the criteria

**Need help?** Click the **"AI Tutor"** button to chat with the AI assistant!

---

## 🐛 Troubleshooting

### Backend won't start

**Error: `ModuleNotFoundError: No module named 'app'`**
```bash
# Make sure you're in the backend directory
cd backend
# Make sure virtual environment is activated
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
```

**Error: `Connection refused` (database)**
```bash
# Check if PostgreSQL is running
# macOS:
brew services list
brew services start postgresql

# Ubuntu:
sudo systemctl status postgresql
sudo systemctl start postgresql

# Verify database exists
psql -U airfoil_user -d airfoil_db -h localhost
```

### XFoil not found

**Error: `XFoil not found at xfoil`**
```bash
# Verify XFoil is installed
which xfoil  # macOS/Linux
where xfoil  # Windows

# If not in PATH, update .env with full path
XFOIL_PATH=/usr/local/bin/xfoil
```

### Frontend can't connect to backend

**Error: `Network Error` or `CORS error`**

1. **Check backend is running**: http://localhost:8000/health
2. **Verify CORS settings** in `backend/app/core/config.py`:
   ```python
   CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]
   ```
3. **Check frontend .env**:
   ```bash
   VITE_API_URL=http://localhost:8000
   ```

### AI Tutor not working

**Error: `401 Unauthorized` or `Invalid API key`**

1. **Verify API key** in `backend/.env`:
   ```bash
   # For Anthropic Claude
   ANTHROPIC_API_KEY=sk-ant-...
   AI_PROVIDER=anthropic

   # For OpenAI GPT
   OPENAI_API_KEY=sk-...
   AI_PROVIDER=openai
   ```

2. **Get API keys**:
   - Anthropic: https://console.anthropic.com/
   - OpenAI: https://platform.openai.com/api-keys

### Database migration issues

**Error: `Table already exists`**
```bash
# Drop and recreate database
psql postgres
DROP DATABASE airfoil_db;
CREATE DATABASE airfoil_db OWNER airfoil_user;
\q

# Re-initialize
cd backend
python -m app.scripts.init_db
python -m app.scripts.seed_challenges
```

---

## 📚 Next Steps

### For Users
1. **Complete Easy challenges** to learn CFD basics
2. **Experiment in Playground** with different airfoils and conditions
3. **Chat with AI Tutor** to deepen understanding
4. **Tackle Medium/Hard challenges** for advanced topics

### For Developers
1. **Read [ARCHITECTURE.md](ARCHITECTURE.md)** to understand the system design
2. **Explore API docs** at http://localhost:8000/docs
3. **Check [CONTRIBUTING.md](CONTRIBUTING.md)** for development guidelines
4. **Create new challenges** by adding JSON files to `shared/challenges/`

---

## 🆘 Getting Help

- **Documentation**: Check [README.md](README.md) and [ARCHITECTURE.md](ARCHITECTURE.md)
- **Issues**: Report bugs on [GitHub Issues](https://github.com/yourusername/AirfoilLearner/issues)
- **Discussions**: Ask questions in [GitHub Discussions](https://github.com/yourusername/AirfoilLearner/discussions)

---

## 🎉 Success!

If you've made it this far, congratulations! You now have:
- ✅ AirfoilLearner running locally
- ✅ XFoil integrated for CFD simulations
- ✅ AI tutor ready to help
- ✅ Challenge system seeded and functional

**Ready to learn CFD?** Head to http://localhost:5173 and start your journey!

---

*Happy learning! 🚀*
