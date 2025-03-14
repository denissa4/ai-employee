import os
import logging
import aiohttp
import asyncio
from quart import Quart, request, jsonify
from core import get_agent
from helpers.attachments_handler import download_and_save

# Set up logging
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
logging.basicConfig(level=logging.DEBUG)
app = Quart(__name__)
app.logger.setLevel(logging.DEBUG)

# Temp storage
user_sessions = {}  # Stores user authentication details
user_sessions_lock = asyncio.Lock()
pending_prompts = {}  # Store prompts awaiting authentication

async def get_user_session(user_id):
    async with user_sessions_lock:
        return user_sessions.get(user_id)

async def update_user_session(user_id, data):
    async with user_sessions_lock:
        user_sessions[user_id] = data

async def store_pending_prompt(user_id, prompt_data):
    async with user_sessions_lock:
        pending_prompts[user_id] = prompt_data

async def get_pending_prompt(user_id):
    async with user_sessions_lock:
        return pending_prompts.pop(user_id, None)

# User agents
user_agents = {}
user_agents_lock = asyncio.Lock()

CLIENT_ID = os.getenv("CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("REDIRECT_URI", "")
TENANT_ID = os.getenv('TENANT_ID', '')
TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
GRAPH_API_URL = "https://graph.microsoft.com/v1.0/me"

@app.route("/prompt", methods=["POST"])
async def prompt():
    """Handles messages from Azure Bot, processes with LLM asynchronously, and responds with context."""
    try:
        data = await request.get_json()
        prompt_text = data.get("prompt", "").strip()
        user_id = data.get("user_id")
        channel_id = data.get("channel_id")

        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        if DEBUG:
            app.logger.info(f"USER ID: {user_id}, PROMPT: {prompt_text}")

        # Check for authentication requirement
        if "email" in prompt_text or "@" in prompt_text:
            user_session = await get_user_session(user_id)

            if not user_session or "access_token" not in user_session:
                oauth_url = (
                    f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/authorize"
                    f"?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}"
                    f"&scope=User.Read%20Mail.Read&prompt=consent&state={user_id}"
                )

                # Store the pending prompt
                await store_pending_prompt(user_id, data)

                return jsonify({
                    "response": "Please authenticate to access your emails.",
                    "oauth_url": oauth_url
                }), 200


            access_token = user_session.get("access_token", "")
            user_email = user_session.get("email", "Unknown")

            if DEBUG:
                app.logger.info(f"ACCESS_TOKEN: {access_token}, USER EMAIL: {user_email}")

        # Handle refresh command
        if prompt_text.lower() == "refresh":
            async with user_agents_lock:
                if user_id in user_agents:
                    user_agents[user_id].memory.reset()
                    return jsonify({"response": "Chat history has been refreshed."}), 200

        # Handle file attachments
        file_path = ""
        attachments = data.get("attachments", [])

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
        full_message_parts = [prompt_text] if prompt_text else []
        if file_path:
            full_message_parts.append(f"ATTACHMENT: {file_path}")

        full_message = "\n".join(full_message_parts)

        # Get or create agent
        async with user_agents_lock:
            if user_id not in user_agents:
                user_agents[user_id] = get_agent()

            agent = user_agents[user_id]

        # Send prompt to LLM agent
        response = await agent.achat(full_message)

        if DEBUG:
            app.logger.info(f"RESPONSE FROM LLM: {response}")

        return jsonify({"response": response}), 200

    except Exception as e:
        app.logger.error(f"Error in /prompt: {e}")
        return jsonify({"error": str(e)}), 500


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
        

async def get_user_info(access_token):
    """Fetch user details (email) from Microsoft Graph API."""
    headers = {"Authorization": f"Bearer {access_token}"}

    async with aiohttp.ClientSession() as session:
        async with session.get(GRAPH_API_URL, headers=headers) as response:
            return await response.json()


@app.route("/callback")
async def callback():
    """Handles OAuth callback by exchanging the code for an access token and resuming the pending request."""
    code = request.args.get("code")
    user_id = request.args.get("state")  # Retrieve stored user_id

    if not code or not user_id:
        return jsonify({"error": "Missing authorization code or user_id"}), 400

    token_response = await get_access_token(code)

    if "access_token" not in token_response:
        return jsonify({"error": "Failed to get access token", "details": token_response}), 400

    access_token = token_response["access_token"]

    # Fetch user info from Microsoft Graph
    user_info = await get_user_info(access_token)
    if not user_info:
        return jsonify({"error": "Failed to fetch user info"}), 400

    user_email = user_info.get("mail") or user_info.get("userPrincipalName")

    # Store the session using the user_id
    await update_user_session(user_id, {
        "access_token": access_token,
        "email": user_email
    })

    if DEBUG:
        app.logger.info(f"User session saved for {user_id}")

    # Retrieve and process the pending prompt
    pending_prompt_data = await get_pending_prompt(user_id)
    if pending_prompt_data:
        return await prompt()  # Resuming the prompt function

    return jsonify({"message": "Authentication successful!", "user_id": user_id, "email": user_email})
