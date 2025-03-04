import os
import requests
import asyncio
from llama_index.core.agent import ReActAgent
from llama_index.llms.deepseek import DeepSeek
from llama_index.core.tools import FunctionTool
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.llms.azure_inference import AzureAICompletionsModel
# Import helper functions
from helpers.get_tool_envs import load_envs
# Import tools
from tools.direct_line import send_and_receive_message
from tools.edit_word_doc import map_style_dependencies_with_text, combined_replace
from tools.translate_text import translate_with_llm


SANDBOX_URL = os.getenv('SANDBOX_ENDPOINT', '')

# Initialize the LLM
def get_llm():
    if "deepseek" in os.getenv('MODEL_NAME', '').lower():
        if "legacy" in os.getenv('MODEL_NAME', '').lower():
            # Legacy DeepSeek method
            return DeepSeek(
                model=os.getenv('MODEL_NAME', ''),
                api_key=os.getenv("MODEL_API_KEY", ""),
                api_base=os.getenv('MODEL_ENDPOINT', ''),
                prompt=os.getenv('MODEL_SYSTEM_PROMPT', None),
                timeout=float(os.getenv('MODEL_TIMEOUT', 300.00)),
            )
        return AzureAICompletionsModel(
            endpoint=os.getenv('MODEL_ENDPOINT', ''),
            credential=os.getenv("MODEL_API_KEY", ""),
            model_name=os.getenv('MODEL_NAME', ''),
            timeout=float(os.getenv('MODEL_TIMEOUT', 300.00)),
            system_prompt=os.getenv('MODEL_SYSTEM_PROMPT', None)
        )
    else:
        if not os.getenv('MODEL_DEPLOYMENT_NAME', ''):
            return AzureAICompletionsModel(
                endpoint=os.getenv('MODEL_ENDPOINT', ''),
                credential=os.getenv("MODEL_API_KEY", ""),
                model_name=os.getenv('MODEL_NAME', ''),
                timeout=float(os.getenv('MODEL_TIMEOUT', 300.00)),
                system_prompt=os.getenv('MODEL_SYSTEM_PROMPT', None)
            )
        return AzureOpenAI(
            model=os.getenv('MODEL_NAME', ''),
            deployment_name=os.getenv('MODEL_DEPLOYMENT_NAME', ''),
            api_key=os.getenv('MODEL_API_KEY', ''),
            azure_endpoint=os.getenv('MODEL_ENDPOINT', ''),
            api_version=os.getenv('MODEL_VERSION', ''),
            system_prompt=os.getenv('MODEL_SYSTEM_PROMPT', None),
            timeout=float(os.getenv('MODEL_TIMEOUT', 300.00)),
        )

# Create ReAct-compatible tools
def execute_python_code(code: str):
    try:
        response = requests.post(f"{SANDBOX_URL}/execute", json={"code": code}, timeout=600)
        return response.json().get("output", "No output received")
    except Exception as e:
        return f"Execution error: {e}"

def get_execute_tool():
    return FunctionTool.from_defaults(
        name="execute_python_code",
        fn=execute_python_code,
        description=f"""Executes Python code in a sandbox container and returns the output in this format:
        
        {{\n    \"stdout\": \"\",\n    \"stderr\": \"\",\n    \"file\": None,\n    \"error\": None\n}}

        - **Use this tool whenever no specific tool is available for the requested task.**
        - If the user requires **up-to-date information**, **always** use this tool instead of relying on your own knowledge—unless a more appropriate tool is available.
        - If the user's request requires a file to be generated use this tool and **always** store the file in /srv. Give the download URL to the user the URL will be {SANDBOX_URL}/download/<filename>
        be sure to replace <filename> with the file that is returned from this tool.

        * Use the reportlab library for creating PDF files from scratch
        * Use matplotlib for creating data visualizations
        
        This tool ensures that calculations, data processing, and external queries are executed in real-time.""",
    )


def send_direct_line_message(dl_lantern: str, message: str):
    """Sends a message to an Azure Direct Line bot and returns its response."""
    try:
        return asyncio.run(send_and_receive_message(dl_lantern, message))
    except Exception as e:
        return f"Error communicating with bot: {e}"

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


def map_styles_for_word_doc(document_path: str):
    try:
        return map_style_dependencies_with_text(document_path)
    except Exception as e:
        return f"Error generating style map: {e}"
    
def get_style_map_tool():
    return FunctionTool.from_defaults(
        name="generate_style_map_for_word_document",
        fn=map_styles_for_word_doc,
        description=f"""Use this tool to generate a style map with corresponding text from a Word document.
        
        * 'document_path' should be the path to a Word document, it will always be in the /tmp/ directory
        This tool will return a list of dictionaries, each dictionary will represent one group of text and its styling in the Word document.
        The strcuture of a dictionary is:
            {{
                'style': 'Heading 2', # The style of the body of text
                'text': 'CONFORMITA’ NORMATIVA', # The existing text
                'translated_text': '' # This text will replace the existing text 
            }}
        
        - You should use this tool to analyze, or 'read' a Word document.
        - If the user asks you to translate a Word document, you should use this tool to get the document's style and structure and you should add to the translation
        to the 'translated_text' key in each dictionary, then pass this edited list of dictionaries to the replace_text_in_word_document tool's 'replacements' argument.
        - You should translate the document yourself instead of relying on another tool.
        """
    )


def replace_text_in_word_doc(document_path: str, replacements: list[dict]):
    try:
        return combined_replace(document_path, replacements)
    except Exception as e:
        return f"Error replacing text: {e}"
    
def get_replace_text_in_word_tool():
    return FunctionTool.from_defaults(
        name="replace_text_in_word_document",
        fn=replace_text_in_word_doc,
        description=f"""Use this tool to replace text in a Word document.
        This tool takes the path of the Word document to edit and the replacements in the form of a list of dictionaries, for example:
            [
                {{
                    'style': 'Heading 2',
                    'text': 'SOME TEXT',
                    'translated_text': 'replacement text'
                }},
                {{
                    'style': 'Normal',
                    'text': 'Some other text',
                    'translated_text': 'replacement text'
                }}
            ]

        ** IMPORTANT This tool will return a file path, after receiving the file path you should use the code execution tool to save the file to the 
        /srv directory and give the download link to the user as per the code execution tool's instructions.
            """
    )
    

# Set up agent with tools
def get_agent():
    llm = get_llm()
    execute_tool = get_execute_tool()
    direct_line_tool = get_direct_line_tool()
    style_map_tool = get_style_map_tool()
    replace_text_tool = get_replace_text_in_word_tool()
    memory = ChatMemoryBuffer.from_defaults(token_limit=int(os.getenv('MODEL_MEMORY_TOKENS', 3000)))
    agent = ReActAgent.from_tools(
        tools=[execute_tool,
                direct_line_tool,
                style_map_tool, 
                replace_text_tool], 
        llm=llm, 
        verbose=False, 
        memory=memory,
        max_iterations=int(os.getenv('MODEL_MAX_ITERATIONS', 10))
        )
    return agent
