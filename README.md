# AI Employee

AI-Employee is your ultimate personal assistant, seamlessly integrating all of NLSQL’s powerful applications and a wide range of third-party tools to make your work life easier than ever. With the cutting-edge capabilities of large language models, AI-Employee takes intelligent reasoning to the next level, empowering you to tackle complex tasks with ease and creativity. The possibilities are endless—whether you're automating processes, solving problems, or discovering new ways to optimize your workflow, AI-Employee is here to make it happen.

## Environment Variables
### Coding sandbox
* SANDBOX_ENDPOINT - _endpoint URL for the coding sandbox where LLM can execute code_

### LLM variables
* MODEL_API_KEY - _API key for the LLM - For AWS Bedrock models this should be the AWS Secret Access Key_
* MODEL_ENDPOINT - _LLM endpoint URL_
* MODEL_NAME - _LLM name - For AWS Bedrock models add the prefix "AWS-" to your model name, e.g. AWS-anthropic.claude-3-7-sonnet-20250219-v1:0_
* MODEL_DEPLOYMENT_NAME - _LLM's Azure deployment name (Azure OpenAI) - For AWS Bedrock models this should be the AWS Access Key ID._
* MODEL_VERSION - _LLM version (Azure OpenAI) - For AWS Bedrock models this should be the model region, e.g. 'us-east-1'_
* MODEL_SYSTEM_PROMPT - _Persistent prompt to help guide the LLM_
* MODEL_TIMEOUT - _Timeout in seconds that the LLM will take to complete the request (default: 300)_
* MODEL_MEMORY_TOKENS - _Total number of chat history tokens the model will store for memory (default: 3000)_
* MODEL_MAX_TOKENS - _The maximum number of tokens the model will handle (default: 8000)_
* MODEL_MAX_ITERATIONS - _Total number of iterations the model will take before giving up (default: 10)_

### Direct Line tools
(replace \<tool name\> with a name of your choice, tool names for secret and description must match)
* DL_AZ_\<tool name\> - _Direct Line secret_
* DL_AZ_\<tool name\>_DESCRIPTION - _Description of the tool for LLM_

### Other tools
#### Google Search
* GOOGLE_SEARCH_API_KEY - _Your Google Custom Search API key (ref: https://console.cloud.google.com/apis/api/customsearch.googleapis.com)_
* GOOGLE_SEARCH_ID - _Your custom search engine ID (ref: https://programmablesearchengine.google.com/)_

#### Google Gemini (image recognition)
* GEMINI_ROCOGNITION_MODEL - _Gemini image recognition model name_
* GEMINI_API_KEY - _Your Google Gemini API key (ref: https://aistudio.google.com/app/apikey)_

### Azure variables
* AZURE_CLIENT_ID - _Client ID of the Azure Managed Identity_
* MicrosoftAppId - _Microsoft App ID of the Azure Bot Service_
* MicrosoftAppTenantId - _Microsoft Tenant ID of the Azure Bot Service_
* MicrosoftAppType - _Type of application used for authentication (default: UserAssignedMSI)_

### Other variables
* EMAIL_ADDRESS - _Email address for sending emails_
* EMAIL_PASSWORD - _Email password for sending emails_
* DEBUG - _For debugging logs (default: False)_

## Run Locally

To run in your local environment follow these steps:

1. Comment out: 
    ```
    // const tokenCredential = new DefaultAzureCredential();
    // const accessToken = await tokenCredential.getToken("https://management.azure.com/.default");
    ```
    - from `bot/src/bot.ts`
    ```
    // MicrosoftAppType: process.env.MicrosoftAppType,
    // MicrosoftAppTenantId: process.env.MicrosoftAppTenantId,
    ```
    - from `bot/src/index.ts`

2. run: `docker build -t ai-employee .`

3. run: `docker run --rm -p 8080:80 --env-file .env ai-employee`

4. use MS Bot Emulator on address `http://localhost:8080/api/messages`

5. or, add environment variables: `MICROSOFT_APP_ID` and `MICROSOFT_APP_PASSWORD` to use an external MS bot.

> **Note:**  _To utilize the full capabilities of the application it is recommended that you run the sandbox environment application alongside AI-Employee (https://github.com/denissa4/ai-employee-sandbox)_


