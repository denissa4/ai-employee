import httpx
import asyncio
import json

DIRECT_LINE_ENDPOINT = 'https://directline.botframework.com/v3/directline'


async def start_conversation(client, headers):
    url = f'{DIRECT_LINE_ENDPOINT}/conversations'
    response = await client.post(url, headers=headers)
    if response.status_code in [200, 201]:
        conversation_data = response.json()
        conversation_id = conversation_data['conversationId']
        print(f"Started conversation with ID: {conversation_id}")
        return conversation_id
    else:
        print(f"Error starting conversation: {response.status_code}")
        return None


async def send_message(client, conversation_id, message, headers):
    url = f'{DIRECT_LINE_ENDPOINT}/conversations/{conversation_id}/activities'
    message_data = {
        "type": "message",
        "from": {"id": "user1"},
        "text": message
    }
    response = await client.post(url, headers=headers, json=message_data)
    if response.status_code == 200:
        print(f"Sent message: {message}")
        return True
    else:
        print(f"Error sending message: {response.status_code}")
        return False


async def get_bot_reply(client, conversation_id, headers):
    url = f'{DIRECT_LINE_ENDPOINT}/conversations/{conversation_id}/activities'
    response = await client.get(url, headers=headers)
    if response.status_code == 200:
        activities = response.json().get('activities', [])

        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        
        for activity in activities:
            if activity['from']['id'] != 'user1':
                bot_message = activity['text']
                print(f"Bot says: {bot_message}")
                return bot_message
    else:
        print(f"Error getting bot reply: {response.status_code}")
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
            return await get_bot_reply(client, conversation_id, headers)
        return None
