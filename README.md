# AI Employee

AI-Employee is your ultimate personal assistant, seamlessly integrating all of NLSQL’s powerful applications and a wide range of third-party tools to make your work life easier than ever. With the cutting-edge capabilities of large language models, AI-Employee takes intelligent reasoning to the next level, empowering you to tackle complex tasks with ease and creativity. The possibilities are endless—whether you're automating processes, solving problems, or discovering new ways to optimize your workflow, AI-Employee is here to make it happen.

## Environment Variables
Coding sandbox
* SANDBOX_ENDPOINT - _endpoint URL for the coding sandbox where LLM can execute code_

LLM variables
* MODEL_API_KEY - _API key for the LLM_
* MODEL_ENDPOINT - _LLM endpoint URL_
* MODEL_NAME - _LLM name_
* MODEL_DEPLOYMENT_NAME - _LLM's Azure deployment name (OpenAI only)_
* MODEL_VERSION - _LLM version (OpenAI only)_
* MODEL_SYSTEM_PROMPT - _Persistent prompt to help guide the LLM_
* MODEL_TIMEOUT - _Timeout in seconds that the LLM will take to complete the request_

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