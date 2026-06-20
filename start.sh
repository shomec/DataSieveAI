#!/bin/bash

# Start FastAPI backend in the background
echo "Starting FastAPI Backend on port 8000..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start Streamlit frontend in the foreground
echo "Starting Streamlit Frontend on port 8501..."
streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0

# If Streamlit exits, kill the backend as well
echo "Streamlit exited, shutting down FastAPI..."
kill $BACKEND_PID
