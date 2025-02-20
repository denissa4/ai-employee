import os
import requests
from flask import Flask, request, jsonify
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.azure_openai import AzureOpenAI

app = Flask(__name__)

SANDBOX_URL = os.getenv('SANDBOX_ENDPOINT', '')

llm = AzureOpenAI(
    model=os.getenv('MODEL_NAME', ''),
    deployment_name=os.getenv('MODEL_DEPLOYMENT_NAME', ''),
    api_key=os.getenv('MODEL_API_KEY', ''),
    azure_endpoint=os.getenv('MODEL_ENDPOINT', ''),
    api_version=os.getenv('MODEL_VERSION', ''),
)

def execute_python_code(code: str):
    """Sends Python code to the sandbox container for execution and returns the output."""
    try:
        response = requests.post(SANDBOX_URL, json={"code": code}, timeout=5)
        return response.json().get("output", "No output received")
    except Exception as e:
        return f"Execution error: {e}"

# Wrap function in a ReAct-compatible tool
execute_tool = FunctionTool.from_defaults(
    name="execute_python",
    fn=execute_python_code,
    description="Executes Python code in a sandbox container and returns the output.",
)

# Create the ReActAgent and inject the custom tool
agent = ReActAgent.from_tools([execute_tool], llm=llm, verbose=True)

@app.route("/prompt", methods=["POST"])
def prompt():
    """Receives a prompt, generates Python code with LLM, and executes it in the sandbox."""
    try:
        data = request.json
        prompt = data.get("prompt")
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        # Query the agent to generate and execute Python code
        response = agent.chat(prompt)
        if not isinstance(response, (dict, list)):  # If not JSON-compatible, convert to string
            response = str(response)
        return jsonify({"response": response}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
