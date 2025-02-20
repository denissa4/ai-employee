import os
import logging
import requests
from flask import Flask, request, jsonify
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.azure_openai import AzureOpenAI
from botbuilder.schema import Activity
from botbuilder.core import TurnContext
from botbuilder.integration.aiohttp import BotFrameworkHttpAdapter
from bot import EmployeeBot

app = Flask(__name__)

# Load environment variables
SANDBOX_URL = os.getenv('SANDBOX_ENDPOINT', '')

llm = AzureOpenAI(
    model=os.getenv('MODEL_NAME', ''),
    deployment_name=os.getenv('MODEL_DEPLOYMENT_NAME', ''),
    api_key=os.getenv('MODEL_API_KEY', ''),
    azure_endpoint=os.getenv('MODEL_ENDPOINT', ''),
    api_version=os.getenv('MODEL_VERSION', ''),
)

# Function to execute Python code in a sandbox
def execute_python_code(code: str):
    try:
        response = requests.post(SANDBOX_URL, json={"code": code}, timeout=120)
        return response.json().get("output", "No output received")
    except Exception as e:
        return f"Execution error: {e}"

# Create ReAct-compatible tool
execute_tool = FunctionTool.from_defaults(
    name="execute_python",
    fn=execute_python_code,
    description="Executes Python code in a sandbox container and returns the output.",
)

# Create the ReActAgent and inject the custom tool
agent = ReActAgent.from_tools([execute_tool], llm=llm, verbose=True)

# Initialize Azure Bot Framework Adapter & Bot
adapter = BotFrameworkHttpAdapter()
bot = EmployeeBot(agent)  # Pass the agent to EmployeeBot

@app.route("/api/messages", methods=["POST"])
def messages():
    """Handles messages from Azure Bot, processes with LLM, and responds."""
    try:
        body = request.json
        activity = Activity().deserialize(body)
        auth_header = request.headers.get("Authorization", "")

        async def call_bot(turn_context: TurnContext):
            await bot.on_turn(turn_context)

        adapter.process_activity(activity, auth_header, call_bot)

        return jsonify({"status": "message processed"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
