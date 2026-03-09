import sys
import time
import os

def main():
    print(f"[mock-agent] Started in {os.getcwd()}")
    print(f"[mock-agent] Arguments: {sys.argv}")
    
    # Read some input from stdin to simulate interaction
    try:
        # We only try to read once so we don't block forever if nothing is sent
        import select
        if sys.platform != "win32":
            r, _, _ = select.select([sys.stdin], [], [], 1.0)
            if r:
                line = sys.stdin.readline()
                print(f"[mock-agent] Received input length: {len(line)}")
        else:
            # Simple read on Windows, this might block if no input is provided,
            # but codexor writes the prompt immediately.
            line = sys.stdin.readline()
            print(f"[mock-agent] Received prompt.")
    except Exception as e:
        print(f"[mock-agent] Input error: {e}")

    # Simulate some work
    time.sleep(1)
    
    print("[mock-agent] Work completed.")
    print("ALL DONE")
    sys.exit(0)

if __name__ == "__main__":
    main()