#!/bin/bash
# Script to start both LangGraph server and plot server

echo "Starting plot server on http://localhost:8001..."
python serve_plots.py &
PLOT_SERVER_PID=$!

echo "Plot server PID: $PLOT_SERVER_PID"
echo ""

echo "Starting LangGraph server..."
langgraph dev

# When LangGraph server stops, also stop the plot server
echo "Stopping plot server..."
kill $PLOT_SERVER_PID 2>/dev/null

echo "All servers stopped."