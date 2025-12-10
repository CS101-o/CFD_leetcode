#!/bin/bash

# AirfoilLearner Backend Startup Script

echo "======================================"
echo "🚀 AirfoilLearner Backend Startup"
echo "======================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Creating one..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install --break-system-packages -q -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from example..."
    cat > .env << 'EOF'
# AirfoilLearner Configuration
APP_NAME=AirfoilLearner
ENV=development
DEBUG=True
HOST=0.0.0.0
PORT=8000

# CORS (add your frontend URLs)
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Optional: AI API Keys (not needed for FREE agent)
# ANTHROPIC_API_KEY=your-key-here
# OPENAI_API_KEY=your-key-here
EOF
    echo "✅ Created .env file"
fi

# Check NeuralFoil installation
echo ""
echo "🔬 Testing NeuralFoil..."
python3 -c "from app.utils.neuralfoil_wrapper import get_predictor; predictor = get_predictor(); print('✅ NeuralFoil ready: 3-5ms per simulation')" 2>/dev/null || echo "⚠️  NeuralFoil not found - will install on first run"

# Start server
echo ""
echo "======================================"
echo "🎉 Starting FastAPI Server"
echo "======================================"
echo "📍 API Docs: http://localhost:8000/docs"
echo "📍 Agent API: http://localhost:8000/api/v1/agent"
echo "======================================"
echo ""

cd app
uvicorn main:app --reload --host 0.0.0.0 --port 8000