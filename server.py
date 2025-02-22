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
# if os.getenv('MODEL_NAME', '').lower() == 'deepseek':
#     llm = DeepSeek(
#         model="deepseek-chat"
#         api_key=os.getenv("DEEPSEEK_API_KEY", ""),
#         temperature=0.7
#     )
# else:
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
        response = requests.post(SANDBOX_URL, json={"code": code}, timeout=120)
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
direct_line_tool = FunctionTool.from_defaults(
    name="send_direct_line_message",
    fn=send_direct_line_message,
    description="""Sends a message to an Azure Direct Line bot and retrieves the response.
    
    The 'dl_lantern' argument should be dynamically chosen based on the user's question:
    * 'AGENT_TO_RETRIEVE_DOCUMENTS_KNOWLEDGE_4647' - for querying an LLM about documents stored in Azure Blob Storage.
    * 'NLSQL_TO_RETRIEVE_DATABASE_INFORMATION_2723' - for retrieving information from a database using natural language.
    * 'STRUCTURIZER_TO_ORGANIZE_TEXT_DATA_8391' - for organizing text data based on column names.
    
    Select the most appropriate variable automatically based on the intent of the user's query.
    
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
        # Query the agent to generate and execute Python code
        response = agent.chat(prompt)
        if not isinstance(response, (dict, list)):  # If not JSON-compatible, convert to string
            response = str(response)
        if DEBUG:
            logging.info(f"RESPONSE: {response}")    
        return jsonify({"response": response}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
