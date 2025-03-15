import os
import aiohttp
import logging
import asyncio
import sqlite3
from core import get_agent
from quart import Quart, request, jsonify
# Import helper functions
from helpers.attachments_handler import download_and_save

# Set up logging
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
logging.basicConfig(level=logging.DEBUG)

logging.getLogger("azure").setLevel(logging.ERROR)  # Suppress Azure SDK and AWS logs
logging.getLogger("botocore").setLevel(logging.ERROR)
logging.getLogger("boto3").setLevel(logging.ERROR)
logging.getLogger("s3transfer").setLevel(logging.ERROR)

# Credentials to allow user email access
CLIENT_ID = os.getenv("CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("REDIRECT_URI", "")
TENANT_ID = os.getenv('TENANT_ID', '')
TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
GRAPH_API_URL = "https://graph.microsoft.com/v1.0/me"

# Initialize the app
app = Quart(__name__)

app.logger.setLevel(logging.DEBUG)

user_agents = {}
user_agents_lock = asyncio.Lock()

def init_db():
    conn = sqlite3.connect('ai_employee.db')
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            user_email TEXT,
            access_token TEXT,
            UNIQUE(user_id, channel_id)
        )
    """)
    conn.commit()
    conn.close()

init_db()  # Ensure the database is set up at startup

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
            conn = sqlite3.connect('ai_employee.db')
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO users (user_id, channel_id) VALUES (?, ?)", (user_id, channel_id))
            conn.commit()
            conn.close()

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
                    try:
                        file_path = download_and_save(url, name)
                    except Exception as e:
                        if DEBUG:
                            app.logger.info(f"Error downloading document:  {e}")
        except:
            file_path = ''

        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        # Form the full message to the LLM
        full_message_parts = []
        if user_id:
            full_message_parts.append(f"USER ID: {user_id}")
        if prompt:
            full_message_parts.append(f"PROMPT: {prompt}")
        if file_path:
            full_message_parts.append(f"ATTACHMENT: {file_path}")

        full_message = "\n".join(full_message_parts)

        if DEBUG:
            app.logger.info(f"FULL PROMPT: {full_message}")

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

    conn = sqlite3.connect('ai_employee.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET access_token = ?, user_email = ? WHERE user_id = ?", (access_token, user_email, user_id))
    conn.commit()
    conn.close()

    return jsonify({"message": "Authentication successful!", "user_id": user_id, "email": user_email})
