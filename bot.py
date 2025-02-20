import requests
from botbuilder.core import ActivityHandler, TurnContext

class EmployeeBot(ActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext):
        # Get the user's message
        user_message = turn_context.activity.text
        
        # Send the user's message to the /prompt endpoint to get the generated response
        prompt_data = {"prompt": user_message}
        try:
            # Make a POST request to /prompt on the same server to process the prompt
            response = requests.post("http://localhost:8000/prompt", json=prompt_data)
            
            if response.status_code == 200:
                # If the response from /prompt is successful, get the bot's response
                bot_response = response.json().get('response', 'No response generated')
            else:
                bot_response = "Error processing your prompt."

        except Exception as e:
            bot_response = f"An error occurred: {e}"

        # Send the response back to the user
        await turn_context.send_activity(bot_response)
