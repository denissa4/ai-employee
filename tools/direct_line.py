import asyncio
import httpx
### Direct Line Bot Functions ###
async def create_conversation(dl_lantern):
    """Starts a new Direct Line conversation."""
    url = "https://directline.botframework.com/v3/directline/conversations"
    headers = {"Authorization": f"Bearer {dl_lantern}", "Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers)
        response.raise_for_status()
        return response.json()["conversationId"]

async def send_message(dl_lantern, conversation_id, text):
    """Sends a message to the bot."""
    url = f"https://directline.botframework.com/v3/directline/conversations/{conversation_id}/activities"
    headers = {"Authorization": f"Bearer {dl_lantern}", "Content-Type": "application/json"}
    data = {"type": "message", "from": {"id": "user1"}, "text": text}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["id"]

async def get_bot_response(dl_lantern, conversation_id, last_message_id):
    """Polls for bot responses."""
    url = f"https://directline.botframework.com/v3/directline/conversations/{conversation_id}/activities"
    headers = {"Authorization": f"Bearer {dl_lantern}", "Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            activities = response.json().get("activities", [])

            for activity in activities:
                if activity["id"] != last_message_id and activity["from"]["id"] != "user1":
                    return activity["text"], activity["id"]

            await asyncio.sleep(1)  # Short delay to avoid excessive polling

async def chat_with_bot(dl_lantern, user_message):
    """Handles the bot conversation flow asynchronously."""
    conversation_id = await create_conversation(dl_lantern)

    # Initial "Hello" to get bot's greeting
    last_message_id = await send_message(dl_lantern, conversation_id, "Hello")
    bot_response, last_message_id = await get_bot_response(dl_lantern, conversation_id, last_message_id)

    # Send actual user message
    last_message_id = await send_message(dl_lantern, conversation_id, user_message)
    bot_response, last_message_id = await get_bot_response(dl_lantern, conversation_id, last_message_id)

    return bot_response
