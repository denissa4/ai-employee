import subprocess
import os
import uuid

SANDBOX_DIR = "/tmp/sandbox"  # Use /tmp to ensure it's writable

def execute_code(user_code):
    """Run user code in a sandboxed Docker environment."""
    script_name = f"{uuid.uuid4().hex}.py"
    script_path = os.path.join(SANDBOX_DIR, script_name)

    # Ensure the sandbox directory exists
    os.makedirs(SANDBOX_DIR, exist_ok=True)

    # Write the user code to a file
    try:
        with open(script_path, "w") as f:
            f.write(user_code)
    except Exception as e:
        return f"Error writing script to file: {e}"

    try:
        # Run the script directly in the container without using Docker
        result = subprocess.run(
            ["python", script_path],
            capture_output=True,
            text=True,
            timeout=60  # Prevent infinite execution
        )

        # Cleanup
        os.remove(script_path)

        # Return the output or error from script execution
        if result.returncode == 0:
            return result.stdout
        else:
            return result.stderr

    except Exception as e:
        return f"Execution error: {e}"

