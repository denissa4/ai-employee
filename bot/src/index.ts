// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.

import * as path from "path";
import { config } from "dotenv";
const ENV_FILE = path.join(__dirname, "..", ".env");
config({ path: ENV_FILE });

import * as restify from "restify";
import { INodeSocket } from "botframework-streaming";

// Import required bot services.
import { CloudAdapter, ConfigurationServiceClientCredentialFactory, createBotFrameworkAuthenticationFromConfiguration } from "botbuilder";

// Import the Bot class (your business logic)
import Bot from "./bot";

// Enable debug
import { setLogLevel } from "@azure/logger";
setLogLevel("verbose");

// Create HTTP server
const server = restify.createServer();
server.use(restify.plugins.bodyParser());
server.listen(process.env.bot_port || process.env.BOT_PORT || 3978, () => {
    console.log(`\n${server.name} listening to ${server.url}`);
    console.log("\nGet Bot Framework Emulator: https://aka.ms/botframework-emulator");
    console.log('\nTo talk to your bot, open the emulator select "Open Bot"');
});

// Configure credentials for the bot authentication
const credentialsFactory = new ConfigurationServiceClientCredentialFactory({
    MicrosoftAppId: process.env.MicrosoftAppId,
    MicrosoftAppPassword: process.env.MicrosoftAppPassword,
    MicrosoftAppType: process.env.MicrosoftAppType,
    MicrosoftAppTenantId: process.env.MicrosoftAppTenantId,
});

const botFrameworkAuthentication = createBotFrameworkAuthenticationFromConfiguration(null, credentialsFactory);

// Create bot adapter
const adapter = new CloudAdapter(botFrameworkAuthentication);

// Catch-all for errors
const onTurnErrorHandler = async (context, error) => {
    console.error(`\n [onTurnError] unhandled error: ${error}`);
    await context.sendTraceActivity("OnTurnError Trace", `${error}`, "https://www.botframework.com/schemas/error", "TurnError");
    await context.sendActivity("The bot encountered an error or bug. Please, try again later or contact support.");
};

// Set the onTurnError for the singleton CloudAdapter.
adapter.onTurnError = onTurnErrorHandler;

const nlBot = new Bot({
    debug: process.env.DEBUG === "true",
    nlApiUrl: process.env.nlapiurl ?? "http://localhost:8000/prompt",  // Your Flask API endpoint
});

console.log(process.env);

// Listen for incoming requests at /api/messages
server.post("/api/messages", async (req, res) => {
    await adapter.process(req, res, (context) => nlBot.run(context));
});

// Listen for Upgrade requests for Streaming.
server.on("upgrade", async (req, socket, head) => {
    const streamingAdapter = new CloudAdapter(botFrameworkAuthentication);
    streamingAdapter.onTurnError = onTurnErrorHandler;
    await streamingAdapter.process(req, socket as unknown as INodeSocket, head, (context) => nlBot.run(context));
});
