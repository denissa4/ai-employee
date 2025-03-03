import os
from llama_index.llms.azure_inference import AzureAICompletionsModel

# from deep_translator import GoogleTranslator

# def translate_text(text: str, target_language: str):
#     return GoogleTranslator(source='auto', target=target_language).translate(text)


def translate_with_llm(text_to_translate: str, target_language: str):
    try:
        system_prompt = """You are a translator, able to translate documents to and from many different languages.
        You will be given a string of text to translate, and a target language. You should translate the text into
        the target language making sure to preserve as its context."""

        translator_llm = AzureAICompletionsModel(
            endpoint=os.getenv('MODEL_ENDPOINT', ''),
            credential=os.getenv("MODEL_API_KEY", ""),
            model_name=os.getenv('MODEL_NAME', ''),
            timeout=float(os.getenv('MODEL_TIMEOUT', 300.00)),
            system_prompt=system_prompt
        )
        full_message = f"TEXT: {text_to_translate} \n\n TARGET_LANGUAGE: {target_language}"
        response = translator_llm.chat(full_message)
        if not isinstance(response, (dict, list)):
            response = str(response)
        return response
    except Exception as e:
        return e