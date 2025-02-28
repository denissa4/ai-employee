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
from tools.edit_word_doc import read_word_doc, replace_text_in_doc


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
        else:
            return AzureAICompletionsModel(
                endpoint=os.getenv('MODEL_ENDPOINT', ''),
                credential=os.getenv("MODEL_API_KEY", ""),
                model_name=os.getenv('MODEL_NAME', ''),
                timeout=float(os.getenv('MODEL_TIMEOUT', 300.00)),
            )
    else:
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


def read_word_document(document_path: str):
    try:
        return read_word_doc(document_path)
    except Exception as e:
        return f"Error reading document: {e}"
    
def get_read_word_document_tool():
    return FunctionTool.from_defaults(
        name="read_word_document",
        fn=read_word_document,
        description=f"""Parses and extracts all the text from a word document.

        * The document_path argument should be a string of the full document path including filename and extention, e.g. "/tmp/document_name.docx"
        
        - Use this tool if the user asks you to read a document with the .doc or .docx extention.
        - If the user askes you to edit or translate an entire document, use this tool to get the readable text,
        then use the replace_text_in_word_document tool to replace the text **replace the text in paragraph or sentence
        chunks to avoid complications**
        
        this tool returns the raw text from the given document.""",
    )


def replace_text_in_word_document(document_path: str, target: str, replacement: str, final: bool):
    try:
        return replace_text_in_doc(document_path, target, replacement, final)
    except Exception as e:
        return f"Error editing document: {e}"
    
def get_replace_text_in_word_document_tool():
    return FunctionTool.from_defaults(
        name="replace_text_in_word_document",
        fn=replace_text_in_word_document,
        description=f"""Replaces the target text with the replacement text in a word document. Returns the file path of the edited document.

        * The 'document_path' argument should be a string of the full document path including filename and extention, e.g. "/tmp/document_name.docx"
        * The 'target' argument should be the target string you want to replace.
        * The 'replacement' argument should be the replacement string.

        - Use this tool if the user askes you to edit a document with the .doc or .docx extention.
        - **Make sure the target string is exactly as it appears in the data returned from the read_word_document tool.**
        - If the user requests that you change a large amount of text, use this tool multiple times **ensuring you use the new file path returned from this tool.**

        This tool will return the file path of the edited document, ready for further editing.
        **IMPORTANT: Use the 'final' boolean argument set to True for the final edit of the document. You will then receive a download URL to send to the user.**
        """,
    )

# Set up agent with tools
def get_agent():
    llm = get_llm()
    execute_tool = get_execute_tool()
    direct_line_tool = get_direct_line_tool()
    read_word_tool = get_read_word_document_tool()
    replace_word_text_tool = get_replace_text_in_word_document_tool()
    memory = ChatMemoryBuffer.from_defaults(token_limit=int(os.getenv('MODEL_MEMORY_TOKENS', 3000)))
    agent = ReActAgent.from_tools([execute_tool, direct_line_tool, read_word_tool, replace_word_text_tool], llm=llm, verbose=True, memory=memory)
    return agent
