import uvicorn
import os
import sys

# Ensure backend module is found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("🚀 Starting BLDC AI Simulator...")
    print("Backend API + Frontend Serving")
    # Using port 8001 to avoid conflict with existing Flask app on 8000
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8001, reload=True)
