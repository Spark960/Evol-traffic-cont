import subprocess
import time
import sys

def start_sims():
    print("🚀 Starting Twin Simulations...")
    
    # Start GA Mode on 5000
    ga_proc = subprocess.Popen([
        sys.executable, "main.py", "--mode", "ga", "--port", "5000"
    ])
    
    # Start Fixed Mode on 5001
    fixed_proc = subprocess.Popen([
        sys.executable, "main.py", "--mode", "fixed", "--port", "5001"
    ])

    print("✅ Both backends are live! Press Ctrl+C to stop both.")
    
    try:
        # Keep the script alive while processes run
        ga_proc.wait()
        fixed_proc.wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down simulations...")
        ga_proc.terminate()
        fixed_proc.terminate()

if __name__ == "__main__":
    start_sims()