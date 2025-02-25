import os
import requests
import asyncio
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.deepseek import DeepSeek
from llama_index.llms.azure_openai import AzureOpenAI
# Import helper functions
from helpers.get_tool_envs import load_envs
# Import tools
from tools.direct_line import send_and_receive_message

SANDBOX_URL = os.getenv('SANDBOX_ENDPOINT', '')

# Initialize the LLM
def get_llm():
    if os.getenv('MODEL_NAME', '').lower() == 'deepseek':
        return DeepSeek(
            model="deepseek-r1",
            api_key=os.getenv("MODEL_API_KEY", ""),
            api_base=os.getenv('MODEL_ENDPOINT', ''),
            prompt=os.getenv('MODEL_SYSTEM_PROMPT', None),
        )
    else:
        return AzureOpenAI(
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

def get_execute_tool():
    return FunctionTool.from_defaults(
        name="execute_python",
        fn=execute_python_code,
        description=f"""Executes Python code in a sandbox container and returns the output.

        - **Use this tool whenever no specific tool is available for the requested task.**
        - If the user requires **up-to-date information**, **always** use this tool instead of relying on your own knowledge—unless a more appropriate tool is available.
        - If the user's request requires a file to be generated use this tool and **always** store the file in /srv. You will be given a filename
        give the download URL to the user the URL will be {os.getenv(SANDBOX_URL)}/download/<filename>
        
        This tool ensures that calculations, data processing, and external queries are executed in real-time.""",
    )

def send_direct_line_message(dl_lantern: str, message: str):
    """Sends a message to an Azure Direct Line bot and returns its response."""
    try:
        return asyncio.run(send_and_receive_message(dl_lantern, message))
    except Exception as e:
        return f"Error communicating with bot: {e}"

# Prepare the Direct Line tool
def get_direct_line_tool():
    tools_with_descriptions = load_envs()
    tool_descriptions = "\n".join([f"    * '{key}' {value}" for key, value in tools_with_descriptions.items()])
    
    return FunctionTool.from_defaults(
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

# Set up agent with tools
def get_agent():
    llm = get_llm()
    execute_tool = get_execute_tool()
    direct_line_tool = get_direct_line_tool()

    agent = ReActAgent.from_tools([execute_tool, direct_line_tool], llm=llm, verbose=True)
    return agent
