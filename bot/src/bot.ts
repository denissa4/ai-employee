import { ActivityHandler, TurnContext } from 'botbuilder';
import axios from 'axios';
import { DefaultAzureCredential } from '@azure/identity';

interface BotOptions {
    debug: boolean;
    nlApiUrl: string;
}

class Bot extends ActivityHandler {
    private nlApiUrl: string;
    private debug: boolean;

    constructor(options: BotOptions) {
        super();
        this.nlApiUrl = options.nlApiUrl;
        this.debug = options.debug;

        this.onMessage(async (context: TurnContext, next) => {
            const userMessage = context.activity.text;
            const userId = context.activity.from.id;
            const attachments = context.activity.attachments;
            const channelId = context.activity.channelId;

            try {
                await context.sendActivity("Processing your request... I'll be with you shortly!");
                const response = await this.sendToFlaskApp(userMessage, userId, attachments, channelId);
                await context.sendActivity(response);
            } catch (error) {
                console.error('Error in bot interaction:', error);
                await context.sendActivity('Sorry, there was an issue processing your request: ' + error);
            }

            await next();
        });
    }

    async sendToFlaskApp(userMessage: string, userId: string, attachments: any, channelId: string) {
        try {
            let headers = {}
            const tokenCredential = new DefaultAzureCredential();
            const accessToken = await tokenCredential.getToken("https://management.azure.com/.default");

            const response = await axios.post(this.nlApiUrl, {
                prompt: userMessage,
                user_id: userId,
                attachments: attachments,
                channel_id: channelId,
            }, {
                headers: headers,
                timeout: 600000
            });

            if (response.data.oauth_url) {
                // If there's an oauth_url in the response, prompt the user to authenticate
                return `Please authenticate by clicking the following link: ${response.data.oauth_url}`;
            }

            return response.data.response;
        } catch (error) {
            console.error('Error sending message to Flask:', error);
            throw new Error(`Error interacting with Flask app: ${error.message || error}`);
        }
    }
}

export default Bot;
