import os
import logging
# Set up logging
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
logging.basicConfig(level=logging.DEBUG)

import asyncio
from quart import Quart, request, jsonify
from core import get_agent
# Import helper functions
from helpers.attachments_handler import download_and_save

logging.getLogger("azure").setLevel(logging.ERROR)  # Suppress Azure SDK and AWS logs
logging.getLogger("botocore").setLevel(logging.ERROR)
logging.getLogger("boto3").setLevel(logging.ERROR)
logging.getLogger("s3transfer").setLevel(logging.ERROR)

# Initialize the app
app = Quart(__name__)

app.logger.setLevel(logging.DEBUG)

## Temp storage
user_sessions = {}  # Stores user authentication details
user_sessions_lock = asyncio.Lock()

async def get_user_session(user_id):
    async with user_sessions_lock:
        return user_sessions.get(user_id)

async def update_user_session(user_id, data):
    async with user_sessions_lock:
        user_sessions[user_id] = data
# User agents
user_agents = {}
user_agents_lock = asyncio.Lock()

if DEBUG:
    app.logger.info("AGENT CREATED AND READY TO CHAT")


CLIENT_ID = os.getenv("CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("REDIRECT_URI", "")
TENANT_ID = os.getenv('TENANT_ID', '')
TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"

@app.route("/prompt", methods=["POST"])
async def prompt():
    """Handles messages from Azure Bot, processes with LLM asynchronously, and responds with context."""
    try:
        data = await request.get_json()
        prompt = data.get("prompt", "").strip()
        user_id = data.get("user_id")
        channel_id = data.get("channel_id")

        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        if DEBUG:
            app.logger.info(f"USER ID: {user_id}, CHANNEL ID: {channel_id}, PROMPT: {prompt}")

        # Ensure user authentication
        user_session = await get_user_session(user_id)

        if not user_session or "access_token" not in user_session:
            CLIENT_ID = os.getenv("CLIENT_ID")
            REDIRECT_URI = os.getenv("REDIRECT_URI")

            if not CLIENT_ID or not REDIRECT_URI:
                return jsonify({"error": "Authentication is required but missing env variables"}), 500

            return jsonify({
                "response": "Please authenticate to access your emails.",
                "oauth_url": f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/authorize"
                             f"?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope=User.Read Mail.Read&prompt=consent"
            }), 401

        access_token = user_session["access_token"]
        user_email = user_session.get("email", "Unknown")

        if DEBUG:
            app.logger.info(f"ACCESS_TOKEN: {access_token}, USER EMAIL: {user_email}")

        # Handle refresh command
        if prompt.lower() == "refresh":
            async with user_agents_lock:
                if user_id in user_agents:
                    user_agents[user_id].memory.reset()
                    if DEBUG:
                        app.logger.info(f"Chat history cleared for user: {user_id}")
            return jsonify({"response": "Chat history has been refreshed."}), 200

        # Handle file attachments
        file_path = ""
        attachments = data.get("attachments", [])

        if DEBUG:
            app.logger.info(f"ATTACHMENTS: {attachments}")

        if attachments and isinstance(attachments, list) and isinstance(attachments[0], dict):
            url = None
            if channel_id == "msteams":
                url = attachments[0].get("content", {}).get("downloadUrl")
            else:
                url = next(
                    (attachments[0].get(key) for key in ["contentUrl", "fileUrl"] if attachments[0].get(key)),
                    None
                )

            if url:
                name = attachments[0].get("name", "unknown_file")
                try:
                    file_path = download_and_save(url, name)
                except Exception as e:
                    app.logger.error(f"Error downloading document: {e}")

        # Prepare message for LLM
        full_message_parts = [prompt] if prompt else []
        if file_path:
            full_message_parts.append(f"ATTACHMENT: {file_path}")
            full_message_parts.append(f"USER SESSION: {user_session}")

        full_message = "\n".join(full_message_parts)

        if DEBUG:
            app.logger.info(f"FULL PROMPT: {full_message}")

        # Get or create agent
        async with user_agents_lock:
            if user_id not in user_agents:
                user_agents[user_id] = get_agent()
                if DEBUG:
                    app.logger.info(f"New agent created for user: {user_id}")

            agent = user_agents[user_id]

        # Send prompt to LLM agent
        response = await agent.achat(full_message)

        if not isinstance(response, (dict, list)):
            response = str(response)

        if DEBUG:
            app.logger.info(f"RESPONSE: {response}")

        return jsonify({"response": response}), 200

    except Exception as e:
        app.logger.error(f"Error in /prompt: {e}")
        return jsonify({"error": str(e)}), 500


import aiohttp

async def get_access_token(auth_code):
    """Exchange auth code for an access token."""
    async with aiohttp.ClientSession() as session:
        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": auth_code,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
            "scope": "User.Read Mail.Read"
        }
        async with session.post(TOKEN_URL, data=data) as response:
            return await response.json()
        

GRAPH_API_URL = "https://graph.microsoft.com/v1.0/me"

async def get_user_info(access_token):
    """Fetch user details (email) from Microsoft Graph API."""
    headers = {"Authorization": f"Bearer {access_token}"}

    async with aiohttp.ClientSession() as session:
        async with session.get(GRAPH_API_URL, headers=headers) as response:
            return await response.json()


@app.route("/callback")
async def callback():
    """Handles OAuth callback by exchanging the code for an access token."""
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "No authorization code provided"}), 400

    token_response = await get_access_token(code)

    # Check if we got an access token
    if "access_token" not in token_response:
        return jsonify({"error": "Failed to get access token", "details": token_response}), 400

    access_token = token_response["access_token"]

    # Fetch user info using the access token
    user_info = await get_user_info(access_token)
    if not user_info:
        return jsonify({"error": "Failed to fetch user info"}), 400

    user_id = user_info["id"]
    user_email = user_info["mail"] or user_info["userPrincipalName"]

    # Store the user session with lock
    async with user_sessions_lock:
        user_sessions[user_id] = {
            "access_token": access_token,
            "email": user_email
        }

    return jsonify({"message": "Authentication successful!", "user_id": user_id, "email": user_email})
