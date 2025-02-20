from botbuilder.core import ActivityHandler, TurnContext

class EmployeeBot(ActivityHandler):
    def __init__(self, agent):
        self.agent = agent  # Store the LlamaIndex ReActAgent

    async def on_message_activity(self, turn_context: TurnContext):
        """Process user input with LlamaIndex LLM and send the response."""
        user_message = turn_context.activity.text

        # Send message to LlamaIndex's ReActAgent
        response = self.agent.chat(user_message)

        # Convert response to string if it's not already
        if not isinstance(response, str):
            response = str(response)

        # Send LLM response back to the user
        await turn_context.send_activity(response)
