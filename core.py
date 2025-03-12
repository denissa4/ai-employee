import os
import asyncio
import logging
import requests
from llama_index.llms.bedrock import Bedrock
from llama_index.llms.bedrock_converse import BedrockConverse
from llama_index.core.agent import ReActAgent
from llama_index.llms.deepseek import DeepSeek
from llama_index.core.tools import FunctionTool
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.tools.google import GoogleSearchToolSpec, GmailToolSpec
from llama_index.llms.azure_inference import AzureAICompletionsModel
# Import helper functions
from helpers.get_tool_envs import load_envs
# Import tools
from tools.image_recognition import detect_objects
from tools.direct_line import send_and_receive_message
from tools.edit_word_doc import map_style_dependencies_with_text, combined_replace

agent_logger = logging.getLogger(__name__)
agent_logger.setLevel(logging.DEBUG)
agent_logger.propagate = True

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
        if "AWS-" in os.getenv('MODEL_NAME', ''):
            model = os.getenv('MODEL_NAME').replace('AWS-', '')
            return Bedrock(
                model=model,
                aws_access_key_id=os.getenv('MODEL_DEPLOYMENT_NAME', ''),
                aws_secret_access_key=os.getenv("MODEL_API_KEY", ""),
                region_name=os.getenv('MODEL_VERSION', ''),
                context_size=int(os.getenv('MODEL_MEMORY_TOKENS', 3000)),
                max_tokens=120000
            )
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
def execute_python_code(query: str):
    try:
        response = requests.post(f"{SANDBOX_URL}/execute", json={"query": query}, timeout=600)
        return response.json().get("output", "No output received")
    except Exception as e:
        return f"Execution error: {e}"

# def get_execute_tool():
#     return FunctionTool.from_defaults(
#         name="execute_python_code",
#         fn=execute_python_code,
#         description=f"""Executes Python code in a sandbox container and returns the output in this format:
        
#         {{\n    \"stdout\": \"\",\n    \"stderr\": \"\",\n    \"file\": None,\n    \"error\": None\n}}

#         - **Use this tool whenever no specific tool is available for the requested task.**
#         - If the user requires **up-to-date information**, **always** use this tool instead of relying on your own knowledge—unless a more appropriate tool is available.
#         - If the user's request requires a file to be generated use this tool and **always** store the file in '/tmp/sandbox'. Give the download URL to the user the URL will be {SANDBOX_URL}/download/<filename>
#         be sure to replace <filename> with the file that is returned from this tool.

#         * Use the reportlab library for creating PDF files from scratch
#         * Use matplotlib for creating data visualizations
        
#         This tool ensures that calculations, data processing, and external queries are executed in real-time.""",
#     )
def get_execute_tool():
    return FunctionTool.from_defaults(
        name="execute_python_code",
        fn=execute_python_code,
        description=f"""This tool allows you to send a natural language query to a coding language model.
        Your input should always be in the form of a query to an LLM asking it to generate some kind of code.
        
        - **Use this tool whenever no specific tool is available for the requested task.**
        - If the user requires **up-to-date information**, **always** use this tool instead of relying on your own knowledge—unless a more appropriate tool is available.
        - If the user's request requires a file to be generated use this tool. Give the download URL to the user the URL will be {SANDBOX_URL}/download/<filename>
        be sure to replace <filename> with the file that is returned from this tool.
        ** Never tell the model where to save the file or what to call it in you query - it already has this information and you will receive the file name as a response.
        """,
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
        description="""Use this tool to generate a style map with corresponding text from a Word document.
        
        * 'document_path' should be the path to a Word document, it will always be in the /srv/ directory
        This tool will return a list of lists, each nested list will represent one group of text and its styling in the Word document.
        The strcuture of a nested list structure is:
            [
                'Heading 2', # The style of the body of text
                'CONFORMITA’ NORMATIVA', # The existing text
                '' # This text will replace the existing text 
            ]
        
        - You should use this tool to analyze, or 'read' a Word document.
        - If the user asks you to translate a Word document, you should use this tool to get the document's style and structure and you should add to the translation
        to the 'translated_text' key in each dictionary, then pass this edited list of dictionaries to the replace_text_in_word_document tool's 'replacements' argument.
        - You should translate the document yourself instead of relying on another tool.
        - ** IMPORTANT The relevant translations should be completed in a single step **.
        """
    )


def replace_text_in_word_doc(document_path: str, replacements: list[list]):
    try:
        return combined_replace(document_path, replacements)
    except Exception as e:
        return f"Error replacing text: {e}"
    
def get_replace_text_in_word_tool():
    return FunctionTool.from_defaults(
        name="replace_text_in_word_document",
        fn=replace_text_in_word_doc,
        description="""Use the replace_text_in_word_document tool to replace text in a Word document.
        ** Ideal for translations **
        Ensure that the replacements argument is a strict Python list of standard Python lists.
        Each list should follow this format:
            [
                [
                    'Heading 2',
                    'SOME TEXT',
                    'replacement text'
                ],
                [
                    'Normal',
                    'Some other text',
                    'replacement text'
                ]
            ]
        - ** ALWAYS enter the text to translate EXACTLY as it appears in the style map, NEVER use "..." you should ALWAYS enter the full text. **
        - The document_path argument should be the path to the document you want to edit, this will be the same file path you used in the style map tool.
        ** IMPORTANT This tool returns the output in this format:
        {\n    \"stdout\": \"\",\n    \"stderr\": \"\",\n    \"file\": None,\n    \"error\": None\n} send the file URL to the user. **
        """
    )


def read_image(query: str, file_path: str, target_area_box=None):
    try:
        return detect_objects(query, file_path, target_area_box)
    except Exception as e:
        return f"There was an error: {e}"

def get_read_image_tool():
        return FunctionTool.from_defaults(
        name="detect_objects_in_image",
        fn=read_image,
        description="""Use this tool to "read" an image.
        This tool takes 3 arguments:
        - 'query' The user's query to the image recognition model
        - 'file_path' The path to the image file
        - 'target_area_box' (optional) A list of 4 integers which are the x, y coordinates for the top right and bottom left corners of a bounding box
        e.g. [200, 300, 600, 900]
        ** IMPORTANT Do NOT put the bounding box in the user's request in the 'query' argument, always use the 'target_area_box' variable. **
        ** Do NOT ask the image recognition model if the any objects fit into the bounding box spesified to the user, just put the bounding box
        coordinates that the user gave you into the target_area_box argument and the tool will do the rest, you will be given a file to send to the user
        in which they cn varify the bounding box positions. **
        ** If the user asks you to draw a bounding box around something or in a specific area, you should send this prompt to the image recognition model. **
        ** IMPORTANT If the user asks if some object(s) are within a bounding box, you should prompt the image recognition model to give you the bounding boxes for these
        objects. **


        If the user asks to see if an object is in a certain area on the image, you should expect the user to send a set of 4 numbers corresponding to
        the target_area_box's position. ** This variable should be left out or set to None if the user does not ask for you to look in a specific area. **

        ** IMPORTANT This tool returns a string output containing the generated file URL (if applicable) and the response text from the image
        recognition model. **
        """
    )

# Set up agent with tools
def get_agent():
    llm = get_llm()

    google_search_tool_spec = GoogleSearchToolSpec(key=os.getenv('GOOGLE_SEARCH_API_KEY', ''), engine=os.getenv('GOOGLE_SEARCH_ID', ''))
    gmail_tool_spec = GmailToolSpec()

    execute_tool = get_execute_tool()
    direct_line_tool = get_direct_line_tool()
    style_map_tool = get_style_map_tool()
    replace_text_tool = get_replace_text_in_word_tool()
    image_recognition_tool = get_read_image_tool()
    google_search_tool = google_search_tool_spec.to_tool_list()
    gmail_tool = gmail_tool_spec.to_tool_list()

    memory = ChatMemoryBuffer.from_defaults(token_limit=int(os.getenv('MODEL_MEMORY_TOKENS', 3000)))
    tools=[execute_tool, direct_line_tool, style_map_tool, replace_text_tool, image_recognition_tool]
    tools.extend(google_search_tool + gmail_tool)
    agent = ReActAgent.from_tools(
        tools=tools,
        llm=llm, 
        verbose=True, 
        memory=memory,
        max_iterations=int(os.getenv('MODEL_MAX_ITERATIONS', 10))
    )
    return agent
