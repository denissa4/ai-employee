import httpx
import asyncio

DIRECT_LINE_ENDPOINT = 'https://directline.botframework.com/v3/directline'
TIMEOUT = 25.0

async def start_conversation(client, headers):
    url = f'{DIRECT_LINE_ENDPOINT}/conversations'
    try:
        response = await client.post(url, headers=headers, timeout=TIMEOUT)  # Set timeout to 10 seconds
        if response.status_code in [200, 201]:
            conversation_data = response.json()
            conversation_id = conversation_data['conversationId']
            print(f"Started conversation with ID: {conversation_id}")
            return conversation_id
        else:
            print(f"Error starting conversation: {response.status_code}")
            return None
    except httpx.TimeoutException:
        print("Timeout occurred while starting the conversation.")
        return None


async def send_message(client, conversation_id, message, headers):
    url = f'{DIRECT_LINE_ENDPOINT}/conversations/{conversation_id}/activities'
    message_data = {
        "type": "message",
        "from": {"id": "user1"},
        "text": message
    }
    try:
        response = await client.post(url, headers=headers, json=message_data, timeout=TIMEOUT)  # Timeout for sending message
        if response.status_code == 200:
            return True
        else:
            print(f"Error sending message: {response.status_code}")
            return False
    except httpx.TimeoutException:
        print("Timeout occurred while sending the message.")
        return False


async def get_bot_reply(client, conversation_id, headers):
    url = f'{DIRECT_LINE_ENDPOINT}/conversations/{conversation_id}/activities'
    try:
        response = await client.get(url, headers=headers, timeout=TIMEOUT)  # Timeout for getting reply
        if response.status_code == 200:
            activities = response.json().get('activities', [])
            activities.sort(key=lambda x: x['timestamp'], reverse=True)

            for activity in activities:
                if activity['from']['id'] != 'user1':
                    bot_message = activity['text']
                    return bot_message
        else:
            print(f"Error getting bot reply: {response.status_code}")
            return None
    except httpx.TimeoutException:
        print("Timeout occurred while waiting for the bot's reply.")
        return None


async def send_and_receive_message(secret, message):
    headers = {
        'Authorization': f'Bearer {secret}',
        'Content-Type': 'application/json'
    }

    async with httpx.AsyncClient() as client:
        conversation_id = await start_conversation(client, headers)
        if conversation_id:
            await send_message(client, conversation_id, message, headers)
            await asyncio.sleep(2)  # Wait for the bot to respond
            res = await get_bot_reply(client, conversation_id, headers)
            print(f"Response: {res}")
            return res
        return None

