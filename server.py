import os
import logging
import requests
import asyncio
from flask import Flask, request, jsonify
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.azure_openai import AzureOpenAI
# Import custom tools
from tools.direct_line import send_and_receive_message

DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

azure_loggers = [
    'azure',
    'azure.core',
    'azure.identity',
    'azure.storage',
    'azure.storage.blob',
    'azure.storage.common',
]

for logger in azure_loggers:
    l = logging.getLogger(logger)
    l.setLevel(logging.ERROR)

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

def send_direct_line_message(dl_lantern: str, message: str):
    """Sends a message to an Azure Direct Line bot and returns its response."""
    try:
        return asyncio.run(send_and_receive_message(dl_lantern, message))
    except Exception as e:
        return f"Error communicating with bot: {e}"

# Direct Line tool - sends message to given bot and returns response
direct_line_tool = FunctionTool.from_defaults(
    name="send_direct_line_message",
    fn=send_direct_line_message,
    description="""Sends a message to an Azure Direct Line bot and retrieves the response.
    The dl_lantern argument should be os.getenv() with one of the following variables:
    * 'RAISE_TALKS' - for talking about startups and entrepreneurship
    * 'NLSQL' - for getting information from a database using natural language
    make the best choice for the variable based on the users question.
    The message should be a string to send to the bot.
    The bots response will be the information returned from this tool."""
)

# Create the ReActAgent and inject the custom tool
agent = ReActAgent.from_tools([execute_tool, direct_line_tool], llm=llm, verbose=True)

if DEBUG:
    logging.info("AGENT CREATED AND READY TO CHAT")

@app.route("/prompt", methods=["POST"])
def prompt():
    """Handles messages from Azure Bot, processes with LLM, and responds."""
    try:
        data = request.json
        prompt = data.get("prompt")
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400
        if DEBUG:
            logging.info(f"USER PROMPT: {prompt}")
        # Query the agent to generate and execute Python code
        response = agent.chat(prompt)
        if not isinstance(response, (dict, list)):  # If not JSON-compatible, convert to string
            response = str(response)
        if DEBUG:
            logging.info(f"RESPONSE: {response}")    
        return jsonify({"response": response}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
