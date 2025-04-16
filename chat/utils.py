import deepl
from hotel_admin import settings

def translate_text(text, target_lang):

    auth_key = settings.DEEPL_API_KEY
    translator = deepl.Translator(auth_key)

    if text and text[0].isalpha() and text.isascii():
        text = text.capitalize()

    result = translator.translate_text(text, target_lang=target_lang)

    return result.text
