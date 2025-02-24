import os
import logging
import asyncio
import nest_asyncio
from flask import Flask, request, jsonify
from core import get_agent

nest_asyncio.apply()

DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

app = Flask(__name__)

# Initialize the agent
agent = get_agent()

if DEBUG:
    logging.info("AGENT CREATED AND READY TO CHAT")

# Load environment variable for the maximum context size
MAX_CONTEXT_SIZE = int(os.getenv('MAX_CONTEXT_SIZE', 5))  # Default to 5 messages if not set

# Dictionary to store user conversation context
user_context = {}

@app.route("/prompt", methods=["POST"])
def prompt():
    """Handles messages from Azure Bot, processes with LLM asynchronously, and responds with context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        data = request.json
        prompt = data.get("prompt")
        user_id = data.get("user_id")

        if not prompt or not user_id:
            return jsonify({"error": "Prompt and user_id are required"}), 400

        if DEBUG:
            logging.info(f"USER PROMPT: {prompt} (User ID: {user_id})")

        # If the user sends "refresh", clear their conversation history
        if prompt.strip().lower() == "refresh":
            user_context.pop(user_id, None)  # Remove user's history if it exists
            return jsonify({"response": "Your conversation history has been cleared."}), 200

        # Get the user context (conversation history)
        context = user_context.get(user_id, [])

        # Append the new prompt to the existing context
        context.append(f"User: {prompt}")

        # Trim the context if it exceeds the MAX_CONTEXT_SIZE
        if len(context) > MAX_CONTEXT_SIZE:
            context.pop(0)  # Remove the oldest message

        # Create the full context for the LLM, including previous messages
        updated_context = "\n".join(context)

        # Pass the updated context to the LLM
        response = loop.run_until_complete(agent.achat(updated_context))

        # Append the bot's response to the context
        context.append(f"Bot: {response}")

        # Store the updated context for the user
        user_context[user_id] = context

        if not isinstance(response, (dict, list)):
            response = str(response)
        if DEBUG:
            logging.info(f"RESPONSE: {response}")
        return jsonify({"response": response}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        loop.close()
