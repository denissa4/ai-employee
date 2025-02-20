import os
import requests
import logging
from flask import Flask, request, jsonify
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.azure_openai import AzureOpenAI
from botbuilder.core import BotFrameworkAdapter, Activity
from botbuilder.integration.aiohttp import BotFrameworkHttpAdapter
from bot import EmployeeBot  # Assuming EmployeeBot is defined in bot.py

app = Flask(__name__)

SANDBOX_URL = os.getenv('SANDBOX_ENDPOINT', '')

llm = AzureOpenAI(
    model=os.getenv('MODEL_NAME', ''),
    deployment_name=os.getenv('MODEL_DEPLOYMENT_NAME', ''),
    api_key=os.getenv('MODEL_API_KEY', ''),
    azure_endpoint=os.getenv('MODEL_ENDPOINT', ''),
    api_version=os.getenv('MODEL_VERSION', ''),
)

# Function to execute Python code
def execute_python_code(code: str):
    try:
        response = requests.post(SANDBOX_URL, json={"code": code}, timeout=120)
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
        
        logging.info(f"USER PROMPT: {prompt}")

        response = agent.chat(prompt)
        if not isinstance(response, (dict, list)):
            response = str(response)

        logging.info(f"RESPONSE: {response}")
        
        return jsonify({"response": response}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Initialize Bot Framework Adapter (no need for app_id and app_password with managed identity)
adapter = BotFrameworkHttpAdapter()

bot = EmployeeBot()

@app.route("/api/messages", methods=["POST"])
def messages():
    """Handles messages from Azure Bot Service."""
    try:
        body = request.json
        activity = Activity().deserialize(body)
        auth_header = request.headers.get("Authorization", "")

        # Send the user message to /prompt endpoint
        prompt_data = {
            "prompt": activity.text  # Take the user's message as the prompt
        }

        # Forward the message to /prompt for processing
        response = requests.post(f'http://localhost:8000/prompt', json=prompt_data)

        if response.status_code == 200:
            prompt_response = response.json().get('response', 'No response')
            activity.text = prompt_response  # Set the bot response based on /prompt response
        else:
            activity.text = "Failed to process the prompt."

        # Now send the bot's response back to the user
        response = adapter.process_activity(activity, auth_header, bot.on_turn)

        return jsonify({"status": "message processed"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
