#!/bin/bash

# Development startup script
# Starts both the FastAPI backend (port 8001) and Next.js frontend (port 3000)

echo "🚀 Starting 6th Degree AI development servers..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Start FastAPI backend
echo -e "${BLUE}[1/2]${NC} Starting FastAPI backend on http://localhost:8001..."
python3 -m uvicorn api_server:app --port 8001 --reload &
API_PID=$!
echo -e "${GREEN}✓${NC} API server starting (PID: $API_PID)"
echo ""

# Wait for API to be ready
echo "⏳ Waiting for API server..."
sleep 3
echo ""

# Start Next.js frontend
echo -e "${BLUE}[2/2]${NC} Starting Next.js frontend on http://localhost:3000..."
cd ~/Downloads/code
npm run dev &
NEXT_PID=$!
echo -e "${GREEN}✓${NC} Next.js starting (PID: $NEXT_PID)"
echo ""

echo -e "${GREEN}✅ All servers started!${NC}"
echo ""
echo "📡 Services:"
echo "   • API Backend:  http://localhost:8001"
echo "   • Next.js App:  http://localhost:3000"
echo ""
echo "📝 Logs:"
echo "   • API logs will appear below"
echo "   • Next.js logs in separate terminal"
echo ""
echo "🛑 To stop: Press Ctrl+C or run: kill $API_PID $NEXT_PID"
echo ""

# Keep script running and show API logs
wait $API_PID
