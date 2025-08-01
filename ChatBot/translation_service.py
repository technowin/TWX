# translation_service.py
import requests
from django.conf import settings

class TranslationService:
    @staticmethod
    def translate(text, target_lang):
        """
        Translate text to target language using Google Translate API
        """
        if target_lang == 'en':
            return text  # No translation needed
            
        try:
            # For production, use Google Cloud Translation API
            # This is a free alternative (may have limits)
            response = requests.get(
                f"https://translate.googleapis.com/translate_a/single",
                params={
                    'client': 'gtx',
                    'sl': 'en',
                    'tl': target_lang,
                    'dt': 't',
                    'q': text
                }
            )
            response.raise_for_status()
            translated_text = response.json()[0][0][0]
            return translated_text
        except Exception as e:
            print(f"Translation failed: {e}")
            return text  # Fallback to Englisha