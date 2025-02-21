import os
import logging
import requests
import asyncio
from flask import Flask, request, jsonify
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.azure_openai import AzureOpenAI
# Import custom tools
from tools.direct_line import chat_with_bot

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

def send_direct_line_message(direct_line_secret: str, message: str):
    """Sends a message to an Azure Direct Line bot and returns its response."""
    try:
        return asyncio.run(chat_with_bot(direct_line_secret, message))
    except Exception as e:
        return f"Error communicating with bot: {e}"

# Direct Line tool - sends message to given bot and returns response
direct_line_tool = FunctionTool.from_defaults(
    name="send_direct_line_message",
    fn=send_direct_line_message,
    description="""Sends a message to an Azure Direct Line bot and retrieves the response.
    The direct_line_secret should be provided as an environment variable using os.getenv().
    The message should be a string to send to the bot.
    The bots response will be the information returned from this tool."""
)

# Create the ReActAgent and inject the custom tool
agent = ReActAgent.from_tools([execute_tool], llm=llm, verbose=True)

@app.route("/prompt", methods=["POST"])
def prompt():
    """Handles messages from Azure Bot, processes with LLM, and responds."""
    try:
        data = request.json
        prompt = data.get("prompt")
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400
        logging.info(f"USER PROMPT: {prompt}")
        # Query the agent to generate and execute Python code
        response = agent.chat(prompt)
        if not isinstance(response, (dict, list)):  # If not JSON-compatible, convert to string
            response = str(response)
        return jsonify({"response": response}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
