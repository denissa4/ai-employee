import os
from dotenv import load_dotenv

def load_envs():
    load_dotenv()

    tool_prefix = "DL_AZ_"

    matching_tools = {key: os.environ[key] for key in os.environ if key.startswith(tool_prefix)}

    tools_with_descriptions = {}

    for key, value in matching_tools.items():
        if key.endswith("_DESCRIPTION"):
            base_tool = key.replace("_DESCRIPTION", "")
            if base_tool in matching_tools:
                tools_with_descriptions[base_tool] = value

    return tools_with_descriptions
