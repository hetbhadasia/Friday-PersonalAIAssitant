#!/usr/bin/env bash
# ==============================================================================
# F.R.I.D.A.Y. V2 — All-In-One Unified Launch Script (Frontend + Backend + Agent)
# ==============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Terminal Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${CYAN}${BOLD}"
echo "============================================================"
echo "    🤖 F.R.I.D.A.Y. V2 — Starting Full System Stack"
echo "============================================================"
echo -e "${NC}"

# 1. Check Python virtual environment
PYTHON_BIN=""
if [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_BIN="$(command -v python3)"
elif command -v python &>/dev/null; then
    PYTHON_BIN="$(command -v python)"
else
    echo -e "${RED}❌ Error: Python not found. Please set up your virtual environment.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Using Python:${NC} $PYTHON_BIN"

# 2. Check and clean up existing ports (8000, 8080, 5173) to avoid Errno 48
cleanup_ports() {
    local PORTS=(8000 8080 5173)
    for PORT in "${PORTS[@]}"; do
        PIDS=$(lsof -t -i :"$PORT" 2>/dev/null || true)
        if [ -n "$PIDS" ]; then
            echo -e "${YELLOW}⚠️  Port $PORT in use by PID(s): $PIDS. Freeing port...${NC}"
            kill -9 $PIDS 2>/dev/null || true
        fi
    done
}
cleanup_ports

# 3. Check frontend dependencies
if [ ! -d "$PROJECT_ROOT/frontend/node_modules" ]; then
    echo -e "${YELLOW}⚡ Installing frontend dependencies...${NC}"
    (cd "$PROJECT_ROOT/frontend" && npm install)
fi

# Track child PIDs for cleanup on exit
PIDS=()

shutdown() {
    echo -e "\n${YELLOW}🛑 Shutting down F.R.I.D.A.Y. V2 services...${NC}"
    for PID in "${PIDS[@]}"; do
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID" 2>/dev/null || true
        fi
    done
    cleanup_ports
    echo -e "${GREEN}✓ All services stopped. Goodbye!${NC}"
    exit 0
}

trap shutdown SIGINT SIGTERM EXIT

# 4. Start FastMCP Server (:8000)
echo -e "${BLUE}▶ Starting FastMCP Server on :8000...${NC}"
"$PYTHON_BIN" server.py &
PIDS+=($!)

# 5. Start Token & Health Server (:8080)
echo -e "${BLUE}▶ Starting Token & Health Server on :8080...${NC}"
"$PYTHON_BIN" token_server.py &
PIDS+=($!)

# Wait briefly for backend servers to bind
sleep 2

# 6. Start LiveKit Voice Agent
echo -e "${BLUE}▶ Starting LiveKit Voice Agent (agent_friday.py)...${NC}"
"$PYTHON_BIN" agent_friday.py dev &
PIDS+=($!)

# 7. Start Frontend (Vite on :5173)
echo -e "${BLUE}▶ Starting Frontend Web UI (:5173)...${NC}"
(cd "$PROJECT_ROOT/frontend" && npm run dev) &
PIDS+=($!)

sleep 2

echo -e "\n${GREEN}${BOLD}============================================================${NC}"
echo -e "${GREEN}${BOLD}🚀 All F.R.I.D.A.Y. services are running!${NC}"
echo -e "   • Frontend UI   : ${CYAN}${BOLD}http://localhost:5173${NC}"
echo -e "   • Token Server  : ${CYAN}http://localhost:8080${NC}"
echo -e "   • FastMCP SSE   : ${CYAN}http://localhost:8000/sse${NC}"
echo -e "   • Voice Agent   : ${CYAN}LiveKit Cloud worker active${NC}"
echo -e "${YELLOW}Press [CTRL+C] to stop all services cleanly.${NC}"
echo -e "${GREEN}${BOLD}============================================================${NC}\n"

# Keep script running and wait on all child processes
wait
