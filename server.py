import os
import logging
import requests
import asyncio
from flask import Flask, request, jsonify
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.deepseek import DeepSeek
from llama_index.llms.azure_openai import AzureOpenAI
# Import any helper functions
from helpers.get_tool_envs import load_envs
# Import custom tools
from tools.direct_line import send_and_receive_message

DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

app = Flask(__name__)

SANDBOX_URL = os.getenv('SANDBOX_ENDPOINT', '')

if os.getenv('MODEL_NAME', '').lower() == 'deepseek':
    llm = DeepSeek(
        model="deepseek-r1",
        api_key=os.getenv("MODEL_API_KEY", ""),
        api_base=os.getenv('MODEL_ENDPOINT', ''),
        prompt=os.getenv('MODEL_SYSTEM_PROMPT', None),
    )
else:
    llm = AzureOpenAI(
        model=os.getenv('MODEL_NAME', ''),
        deployment_name=os.getenv('MODEL_DEPLOYMENT_NAME', ''),
        api_key=os.getenv('MODEL_API_KEY', ''),
        azure_endpoint=os.getenv('MODEL_ENDPOINT', ''),
        api_version=os.getenv('MODEL_VERSION', ''),
        system_prompt=os.getenv('MODEL_SYSTEM_PROMPT', None),
    )

# Create ReAct-compatible tools
def execute_python_code(code: str):
    try:
        response = requests.post(SANDBOX_URL, json={"code": code}, timeout=300)
        return response.json().get("output", "No output received")
    except Exception as e:
        return f"Execution error: {e}"

# Tool to use sandbox to execute python code
execute_tool = FunctionTool.from_defaults(
    name="execute_python",
    fn=execute_python_code,
    description="""Executes Python code in a sandbox container and returns the output.

    - **Use this tool whenever no specific tool is available for the requested task.**
    - If the user requires **up-to-date information**, **always** use this tool instead of relying on your own knowledge—unless a more appropriate tool is available.
    
    This tool ensures that calculations, data processing, and external queries are executed in real-time.""",
)

def send_direct_line_message(dl_lantern: str, message: str):
    """Sends a message to an Azure Direct Line bot and returns its response."""
    try:
        return asyncio.run(send_and_receive_message(dl_lantern, message))
    except Exception as e:
        return f"Error communicating with bot: {e}"

# Direct Line tool - sends message to given bot and returns response
tools_with_descriptions = load_envs()
tool_descriptions = "\n".join([f"    * '{key}' {value}" for key, value in tools_with_descriptions.items()])
direct_line_tool = FunctionTool.from_defaults(
    name="send_direct_line_message",
    fn=send_direct_line_message,
    description=f"""Sends a message to an Azure Direct Line bot and retrieves the response.
    
    The 'dl_lantern' argument should be dynamically chosen based on the user's question:
    {tool_descriptions}
    
    Select the most appropriate variable automatically based on the intent of the user's query.
    If you are unsure which tool to use, please ask the user to specify.
    
    The 'message' argument is the text to send to the bot.
    
    Always wait for the tool to return a response—it will **always** provide one.  
    **Always use the response from this tool to answer the user's question.**""",
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
        response = agent.chat(prompt)
        if not isinstance(response, (dict, list)):
            response = str(response)
        if DEBUG:
            logging.info(f"RESPONSE: {response}")    
        return jsonify({"response": response}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
