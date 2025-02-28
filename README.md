# AI Employee

AI-Employee is your ultimate personal assistant, seamlessly integrating all of NLSQL’s powerful applications and a wide range of third-party tools to make your work life easier than ever. With the cutting-edge capabilities of large language models, AI-Employee takes intelligent reasoning to the next level, empowering you to tackle complex tasks with ease and creativity. The possibilities are endless—whether you're automating processes, solving problems, or discovering new ways to optimize your workflow, AI-Employee is here to make it happen.

## Environment Variables
Coding sandbox
* SANDBOX_ENDPOINT - _endpoint URL for the coding sandbox where LLM can execute code_

LLM variables
* MODEL_API_KEY - _API key for the LLM_
* MODEL_ENDPOINT - _LLM endpoint URL_
* MODEL_NAME - _LLM name_
* MODEL_DEPLOYMENT_NAME - _LLM's Azure deployment name (Azure OpenAI only)_
* MODEL_VERSION - _LLM version (Azure OpenAI only)_
* MODEL_SYSTEM_PROMPT - _Persistent prompt to help guide the LLM_
* MODEL_TIMEOUT - _Timeout in seconds that the LLM will take to complete the request (default: 300)_
* MODEL_MEMORY_TOKENS - _Total number of chat history tokens the model will store for memory (default: 3000)_
* MODEL_MAX_ITERATIONS - _Total number of iterations the model will take before giving up (default: 10)_

Direct Line tools
(replace \<tool name\> with a name of your choice, tool names for secret and description must match)
* DL_AZ_\<tool name\> - _Direct Line secret_
* DL_AZ_\<tool name\>_DESCRIPTION - _Description of the tool for LLM_


Azure variables
* AZURE_CLIENT_ID - _Client ID of the Azure Managed Identity_
* MicrosoftAppId - _Microsoft App ID of the Azure Bot Service_
* MicrosoftAppTenantId - _Microsoft Tenant ID of the Azure Bot Service_
* MicrosoftAppType - _Type of application used for authentication (default: UserAssignedMSI)_

Other variables
* DEBUG - _For debugging logs (default: False)_

## Run Locally

To run in your local environment follow these steps:

* Comment out: 
    ```
    const tokenCredential = new DefaultAzureCredential();
    const accessToken = await tokenCredential.getToken("https://management.azure.com/.default");
    ```
    - from `bot/src/bot.ts`
    ```
    // MicrosoftAppType: process.env.MicrosoftAppType,
    // MicrosoftAppTenantId: process.env.MicrosoftAppTenantId,
    ```
    - from `bot/src/index.ts`

* run: `docker build -t ai-employee .`

* run: `docker run --rm -p 8080:80 --env-file .env ai-employee`

* use MS Bot Emulator on address `http://localhost:8080/api/messages`

* or, add ennironment variables: `MICROSOFT_APP_ID` and `MICROSOFT_APP_PASSSWORD` to use an external MS bot.
