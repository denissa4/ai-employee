from flask import Flask, request, jsonify
import requests
from llama_index.core.tools import FunctionTool
from llama_index.core.agent import ReActAgent
from llama_index.llms.azure_openai import AzureOpenAI
import os

from llama_index.tools.azure_code_interpreter import AzureCodeInterpreterToolSpec


app = Flask(__name__)

# Configuration
SANDBOX_URL = "http://sandbox-container:5000/execute"  # Points to the sandbox container internally

llm = AzureOpenAI(
    model=os.getenv('MODEL_NAME', ''),
    deployment_name=os.getenv('MODEL_DEPLOYMENT_NAME', ''),
    api_key=os.getenv('MODEL_API_KEY', ''),
    azure_endpoint=os.getenv('MODEL_ENDPOINT', ''),
    api_version=os.getenv('MODEL_VERSION', ''),
)

azure_code_interpreter_spec = AzureCodeInterpreterToolSpec(
    pool_management_endpoint=os.getenv('POOL_MANAGEMENT_ENDPOINT', ''),
    local_save_path=".",
)

# Create the ReActAgent and inject the custom tool
agent = ReActAgent.from_tools(azure_code_interpreter_spec.to_tool_list(), llm=llm, verbose=True)

@app.route("/prompt", methods=["POST"])  # Changed endpoint from /execute to /prompt
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
    app.run(host="0.0.0.0", port=8000, debug=True)  # Flask server listens on port 5001
