import os
import logging
import asyncio
from quart import Quart, request, jsonify
from core import get_agent
# Import helper functions
from helpers.attachments_handler import download_and_save

# Initialize the app
app = Quart(__name__)

# Set up logging
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
logging.basicConfig(level=logging.DEBUG)
app.logger.setLevel(logging.DEBUG)

# Initialize the agent
user_agents = {}
user_agents_lock = asyncio.Lock()

if DEBUG:
    app.logger.info("AGENT CREATED AND READY TO CHAT")

@app.route("/prompt", methods=["POST"])
async def prompt():
    """Handles messages from Azure Bot, processes with LLM asynchronously, and responds with context."""
    try:
        data = await request.get_json()
        prompt = data.get("prompt", '')
        user_id = data.get("user_id")
        channel_id = data.get("channel_id")
        if DEBUG:
            app.logger.info(f"USER ID: {user_id}")
            app.logger.info(f"CHANNEL ID: {channel_id}")
            app.logger.info(f"USER PROMPT: {prompt}")
        try:

            # Check if the user sent the "refresh" command
            if prompt.lower() == "refresh":
                # Clear the chat history for this user
                async with user_agents_lock:
                    if user_id in user_agents:
                        agent = user_agents[user_id]
                        agent.memory.reset()  # Reset the agent's chat history
                        if DEBUG:
                            app.logger.info(f"Chat history cleared for user: {user_id}")
                return jsonify({"response": "Chat history has been refreshed."}), 200

            attachments = data.get("attachments", [])
            if DEBUG:
                app.logger.info(f"ATTACHMENTS: {attachments}")

            # Get download URL for attachments
            file_path = ''
            if attachments and isinstance(attachments, list) and isinstance(attachments[0], dict):
                if channel_id == "msteams":
                    url = attachments[0].get("content", {}).get("downloadUrl")
                else:
                    url = next(
                        (attachments[0].get(key) for key in ["contentUrl", "fileUrl"] if attachments[0].get(key)),
                        None
                    )
                if url:
                    name = attachments[0].get('name', 'unknown_file')
                    file_path = await download_and_save(url, name)
                    app.logger.info(f"THIS HAPPENED:::::  {file_path}")
        except:
            file_path = ''
        
        if DEBUG:
            app.logger.info(file_path)

        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        # Form the full message to the LLM
        full_message_parts = []
        if prompt:
            full_message_parts.append(f"{prompt}")
        if file_path:
            full_message_parts.append(f"ATTACHMENT: {file_path}")

        full_message = "\n".join(full_message_parts)

        if DEBUG:
            app.logger.info(full_message)

        # Get or create an agent for this user
        async with user_agents_lock:
            if user_id not in user_agents:
                user_agents[user_id] = get_agent()  # Create a new agent
                if DEBUG:
                    app.logger.info(f"New agent created for user: {user_id}")

            agent = user_agents[user_id]

        response = await agent.achat(full_message)

        if not isinstance(response, (dict, list)):
            response = str(response)
        if DEBUG:
            app.logger.info(f"RESPONSE: {response}")
        return jsonify({"response": response}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

