# AirfoilLearner - Quick Start Guide

## 🚀 Running the Application (Current State)

### Both Servers Are Already Running!

**Backend**: http://localhost:8000
- Status: ✅ Running
- Database: ✅ Connected
- Features: Health check, database with challenges

**Frontend**: http://localhost:5173  
- Status: ✅ Running
- Features: 3D UI, mock simulations, chatbot interface

---

## 🎮 What You Can Do Right Now

### 1. Open the Frontend
```
Click: http://localhost:5173
```

### 2. Explore the Interface

**Left Panel:**
- Read the challenge description
- Move the α (angle of attack) slider: -5° to 20°
- Move the Reynolds number slider: 500k to 5M
- Click preset buttons: Baseline, High Lift, Low Drag

**Center Canvas:**
- **Drag** with mouse to rotate the 3D airfoil
- **Scroll** to zoom in/out
- Admire the metallic blue shader

**Right Panel:**
- View metrics (after running simulation)
- Chat with AI tutor (mock responses)
- Try quick prompt buttons

### 3. Run a Simulation
1. Set α = 5°, Reynolds = 1M (or any values)
2. Click **"Run Simulation"** (pulsing blue button)
3. Wait 2 seconds (loading overlay)
4. See **FAKE** results appear:
   - CL ≈ 0.547
   - CD ≈ 0.0082  
   - L/D ≈ 66.7

⚠️ **Remember**: These are NOT real CFD results - just mock data!

### 4. Chat with AI
1. Type "Why is my drag high?" in the chat input
2. Click **Send** or press Enter
3. Get a canned response (not real AI yet)
4. See message history build up

---

## ⚠️ Important: What's Real vs Mock

| Feature | Status | Details |
|---------|--------|---------|
| UI/UX | ✅ **REAL** | Fully functional interface |
| 3D Airfoil | ✅ **REAL** | Correct NACA 0012 geometry |
| Database | ✅ **REAL** | PostgreSQL with 3 challenges |
| CFD Results | ❌ **FAKE** | Random numbers, not real simulation |
| AI Chatbot | ❌ **FAKE** | Canned responses, not real AI |
| User Auth | ❌ **NOT IMPLEMENTED** | No login system yet |

---

## 🛠️ If Something Breaks

### Frontend Won't Load
```bash
cd /Users/kaanoktem/CFDLeetcode/frontend
npm run dev
```
Then open: http://localhost:5173

### Backend Down
```bash
cd /Users/kaanoktem/CFDLeetcode/backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Database Issues
```bash
# Check Docker containers
docker ps

# Restart database
docker restart airfoil_postgres
```

### Check Logs
```bash
# Backend logs
tail -f /Users/kaanoktem/CFDLeetcode/backend/logs.txt

# Frontend dev server
# Look at terminal where `npm run dev` is running
```

---

## 📖 Understanding the Codebase

### Key Files

**Frontend:**
```
frontend/src/
├── App.jsx                      # Main layout (3 panels)
├── components/
│   ├── Navbar.jsx              # Top navigation
│   ├── LeftPanel.jsx           # Challenge + controls
│   ├── CenterCanvas.jsx        # 3D viewer
│   ├── Airfoil3D.jsx           # NACA geometry
│   └── RightPanel.jsx          # Metrics + chat
├── services/api.js             # Mock API calls
└── store/useStore.js           # Global state
```

**Backend:**
```
backend/
├── app/
│   ├── main.py                 # FastAPI app (routes commented out!)
│   ├── core/
│   │   ├── config.py          # Environment variables
│   │   └── database.py        # DB connection
│   ├── models/                # SQLAlchemy models
│   └── scripts/
│       ├── init_db.py         # Create tables
│       └── seed_challenges.py # Load challenges
└── .env                       # Configuration
```

### Where to Add Real CFD

**Step 1**: Create XFoil wrapper
```python
# backend/app/utils/xfoil_wrapper.py
def run_xfoil(airfoil, alpha, reynolds):
    # Call XFoil subprocess
    # Parse output
    # Return CL, CD, Cp
    pass
```

**Step 2**: Create simulation service
```python
# backend/app/services/simulation_service.py
from app.utils.xfoil_wrapper import run_xfoil

async def run_simulation(params):
    result = run_xfoil(...)
    # Save to database
    return result
```

**Step 3**: Implement API endpoint
```python
# backend/app/api/endpoints/simulations.py
@router.post("/simulations")
async def create_simulation(params: SimulationParams):
    result = await simulation_service.run_simulation(params)
    return result
```

**Step 4**: Update frontend
```javascript
// frontend/src/services/api.js
export const simulationAPI = {
  run: async (params) => {
    const response = await axios.post('/api/v1/simulations', params);
    return response.data;  // Real results!
  }
};
```

---

## 🎯 Development Priorities

### Week 1: XFoil Integration
1. Install XFoil: `brew install xfoil`
2. Create Python wrapper
3. Test with NACA 0012
4. Implement backend endpoint
5. Connect frontend

### Week 2: AI Tutor
1. Add Anthropic API key
2. Implement chat service
3. Connect to frontend
4. Test conversations

### Week 3: Challenge Validation
1. Implement validation logic
2. Test with seeded challenges
3. Add success/failure feedback
4. Track user progress

### Week 4: Polish & Demo Prep
1. Add loading states
2. Error handling
3. Charts (Cp distribution)
4. Prepare demo script

---

## 📊 Database Quick Reference

### View Challenges
```bash
cd backend
source venv/bin/activate
python
```
```python
from app.core.database import SessionLocal
from app.models.challenge import Challenge

db = SessionLocal()
challenges = db.query(Challenge).all()
for c in challenges:
    print(f"{c.title} - {c.difficulty}")
```

### Challenges Already Seeded

1. **First Flight: NACA 0012 Lift Prediction** (Easy)
   - Goal: CL between 0.50 and 0.60
   - Params: α=5°, Re=1e6

2. **Danger Zone: Predicting Airfoil Stall** (Medium)
   - Goal: Find CLmax and stall angle
   - Params: Sweep α from 0° to 20°

3. **Efficiency Challenge: Minimize Drag** (Hard)
   - Goal: CL=0.8, minimize CD
   - Params: Choose airfoil, α, Re

---

## 💡 Tips

**For Development:**
- Both servers have hot reload enabled
- Change React components → instant update
- Change Python files → uvicorn reloads

**For Demo:**
- Zoom in on 3D airfoil for dramatic effect
- Show challenge objectives checklist
- Demonstrate parameter sliders
- Show "Run Simulation" animation
- Emphasize the cyberpunk aesthetic

**For Testing:**
- Use realistic values: α ∈ [0°, 15°], Re ∈ [1e5, 1e7]
- Avoid extreme angles (α > 20°) - might break XFoil
- Test with different NACA airfoils: 0012, 2412, 4412

---

## 🆘 Getting Help

**Documentation:**
- Main README: `README.md`
- Architecture: `ARCHITECTURE.md`
- Implementation Status: `IMPLEMENTATION_STATUS.md`

**Check Status:**
```bash
# Backend health
curl http://localhost:8000/health

# Frontend running
curl http://localhost:5173
```

**Common Issues:**
- Port 8000 busy? Another uvicorn running
- Port 5173 busy? Another Vite dev server
- Database error? Check Docker: `docker ps`
- Import error? Activate venv: `source venv/bin/activate`

---

**You're all set! Open http://localhost:5173 and explore the beautiful UI!** 🚀
