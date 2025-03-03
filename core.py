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
from tools.edit_word_doc import process_document_xml, map_style_dependencies, structured_document_replace, process_embedded_content, validate_document_integrity
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
        else:
            return AzureAICompletionsModel(
                endpoint=os.getenv('MODEL_ENDPOINT', ''),
                credential=os.getenv("MODEL_API_KEY", ""),
                model_name=os.getenv('MODEL_NAME', ''),
                timeout=float(os.getenv('MODEL_TIMEOUT', 300.00)),
                system_prompt=os.getenv('MODEL_SYSTEM_PROMPT', None)
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


def extract_xml_from_word_doc(document_path: str, operation: str, modifications: list):
    try:
        return process_document_xml(document_path, operation, modifications)
    except Exception as e:
        return f"Error processing document: {e}"
    
def get_xml_from_word_tool():
    return FunctionTool.from_defaults(
        name="extract_xml_from_word_document",
        fn=extract_xml_from_word_doc,
        description=f"""This tool extracts the raw XML content and style definitions from a DOCX file. 
        It leverages the underlying XML structure to provide a complete view of the document's body and style settings. 
        This information helps the LLM understand the document's structure, including paragraphs, runs, tables, and other elements.

        Usage:

        When to Use:
        Use this tool when you need an overview of the document's content and formatting before performing any translations or modifications.
        It's ideal for “reading” the document structure.
        How to Use:
        Provide the path to the DOCX file. The tool returns the XML of the document's body and the styles XML.""",
    )


def map_styles_for_word_doc(document_path: str):
    try:
        return map_style_dependencies(document_path)
    except Exception as e:
        return f"Error generating style map: {e}"
    
def get_style_map_tool():
        return FunctionTool.from_defaults(
        name="generate_style_map_for_word_document",
        fn=map_styles_for_word_doc,
        description=f"""This tool analyzes the document’s styles by mapping out the style dependencies and properties. 
        It creates a report showing the hierarchy of styles (e.g., which style is based on which) and their formatting details (such as font, size, and spacing).

        Usage:

        When to Use:
        Use this tool when you need to understand how text is formatted in the document.
        This is useful to determine which parts (like headings, normal text, table text) should be targeted for translation.
        How to Use:
        Provide the path to the DOCX file. The tool returns a report containing a style graph and style properties.""",
    )


def replace_text_in_word_doc(document_path: str, replacements: list):
    try:
        return structured_document_replace(document_path, replacements)
    except Exception as e:
        return f"Error replacing text: {e}"

def get_replace_text_tool():
    return FunctionTool.from_defaults(
        name="replace_text_in_word_document",
        fn=replace_text_in_word_doc,
        description=f"""This tool performs context-sensitive text replacement in paragraphs by editing the underlying XML. 
        It targets only the <w:t> text nodes in runs (while preserving non‑text content such as images) and replaces text based on specified 
        criteria (using prefixes, suffixes, and styles).

        Usage:

        When to Use:
        Use this tool when you need to replace specific text within paragraphs (e.g., in headings or body text) while keeping the formatting 
        and embedded images intact.
        How to Use:
        Provide a DOCX file along with a list of replacement configurations. Each configuration specifies:
        A prefix (the starting text) and an optional suffix (ending text) to identify the target text.
        The style (e.g., "Normal" or "Heading1") that the paragraph must match.
        The translated text to replace the target text.
        """,
    )


def process_embedded_content_in_word_doc(document_path: str, replacements: dict):
    try:
        return process_embedded_content(document_path, replacements)
    except Exception as e:
        return f"Error replacing conent: {e}"
    
def get_embedded_content_processing_tool():
    return FunctionTool.from_defaults(
        name="replace_text_in_embedded_content_in_word_document",
        fn=process_embedded_content_in_word_doc,
        description=f"""This tool processes embedded content within the document, such as tables, charts, and other non-paragraph elements. 
        It searches for text within table cells or chart labels and replaces them according to a provided translation mapping.

        Usage:

        When to Use:
        Use this tool when you need to translate text that appears in tables, charts, 
        or other embedded objects that are not processed by the paragraph text replacement tool.
        How to Use:
        Provide the DOCX file and a mapping of original text to translated text. The tool scans tables and charts and updates the text accordingly.""",
    )


def validate_document_formatting(original_path: str, translated_path: str):
    try:
        return validate_document_integrity(original_path, translated_path)
    except Exception as e:
        return f"Error validating document formatting: {e}"
    
def get_validata_document_formatting_tool():
        return FunctionTool.from_defaults(
        name="validate_document_formatting_after_editing",
        fn=validate_document_formatting,
        description=f"""This tool compares the formatting of the original document with the modified (translated) document. 
        It generates a report on formatting preservation by comparing properties such as paragraph alignment and style details.

        Usage:

        When to Use:
        Use this tool after performing translations and modifications to ensure that the formatting (e.g., spacing, fonts, alignment) 
        remains consistent with the original document.
        How to Use:
        Provide the paths to both the original and the modified DOCX files. The tool returns a report indicating any discrepancies in formatting.""",
    )


def translate_text(text_to_translate: str, target_language: str):
    try:
        translate_with_llm(text_to_translate, target_language)
    except Exception as e:
        return f"Error translating text: {e}"

def get_translate_text_tool():
    return FunctionTool.from_defaults(
        name="translate_text_to_target_language",
        fn=translate_text,
        description=f"""This tool translates a given text into a given target language.
        Use this tool if the user asked for you to translate something.""",
    )


# Set up agent with tools
def get_agent():
    llm = get_llm()
    execute_tool = get_execute_tool()
    direct_line_tool = get_direct_line_tool()
    extract_xml_tool = get_xml_from_word_tool()
    style_map_tool = get_style_map_tool()
    replace_text_tool = get_replace_text_tool()
    replace_embedded_text_tool = get_embedded_content_processing_tool()
    translate_text_tool = get_translate_text_tool()
    validate_document_tool = get_validata_document_formatting_tool()
    memory = ChatMemoryBuffer.from_defaults(token_limit=int(os.getenv('MODEL_MEMORY_TOKENS', 3000)))
    agent = ReActAgent.from_tools(
        tools=[execute_tool,
                direct_line_tool, 
                extract_xml_tool, 
                style_map_tool, 
                replace_text_tool, 
                replace_embedded_text_tool,
                translate_text_tool,
                validate_document_tool], 
        llm=llm, 
        verbose=True, 
        memory=memory,
        max_iterations=int(os.getenv('MODEL_MAX_ITERATIONS', 10))
        )
    return agent
