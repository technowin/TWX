# views.py
import hashlib
from django.core.cache import cache
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views import View
from django.utils import translation
from requests import request
from .models import *
import uuid
import re
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
import json
import google.generativeai as genai
from ChatModal.models import *
import os
# from googletrans import Translator  
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.core.validators import RegexValidator
from django.shortcuts import get_object_or_404, redirect, render
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import ChatSession, ChatLog

# Initialize Gemini (replace with your actual API key)
# genai.configure(api_key='AIzaSyCEDlkdLcCrhy2tRgXTd22-67SB_Dmdcaw')

genai.configure(api_key='AIzaSyDYWMDZ25wRJtmAkjMLUH_7Oazrdpocrdc')
# genai.configure(api_key='AIzaSyD3QsIBPODMpfVI7Xd57iLGbGW4uPTfuoc')

# translator = Translator()

# class ChatBotView(View):
#     """Chatbot view with dynamic menu system"""
    
#     def get(self, request, *args, **kwargs):
#     # Clear menu navigation session on fresh page load (not AJAX)
#         if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#             if 'current_menu_parent' in request.session:
#                 del request.session['current_menu_parent']
        
#         languages = list(Language.objects.filter(is_active=True).values('code', 'name'))
#         if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#             return JsonResponse({'languages': languages})
#         return render(request, 'Chat/chat.html', {
#             'languages_json': json.dumps(languages),
#             'languages': languages,
#         })
    
#     def _translate_text(self, text, target_language):
#         """Universal translation function for all supported languages"""
#         if target_language == 'en':
#             return text
            
#         # Language mapping with script requirements
#         LANGUAGE_SCRIPTS = {
#             'hi': ('Hindi', 'Devanagari'),
#             'mr': ('Marathi', 'Devanagari'),
#             'gu': ('Gujarati', 'Gujarati'),
#             'ur': ('Urdu', 'Nastaliq'),
#             'bn': ('Bengali', 'Bengali'),
#             'ta': ('Tamil', 'Tamil'),
#             'te': ('Telugu', 'Telugu'),
#             'kn': ('Kannada', 'Kannada'),
#             'ml': ('Malayalam', 'Malayalam'),
#             'pa': ('Punjabi', 'Gurmukhi'),
#         }
        
#         # Get language details
#         language_name, script = LANGUAGE_SCRIPTS.get(target_language, (target_language, None))
        
#         cache_key = f"trans_{target_language}_{hashlib.md5(text.encode()).hexdigest()}"
#         cached = cache.get(cache_key)
#         if cached:
#             return cached
            
#         try:
#             model = genai.GenerativeModel('gemini-2.5-flash')
#             prompt = f"""
#             Translate this manufacturing menu item to {language_name}.
#             Important Instructions:
#             1. Keep technical terms in English if no translation exists
#             2. Return ONLY the translated text
#             3. Use {script} script if specified
#             4. For Urdu, use proper Nastaliq script
#             5. Never add explanations or notes
            
#             Text to translate: "{text}"
#             """
            
#             response = model.generate_content(prompt)
#             translated = response.text.strip('"\'').strip()
            
#             # Remove common response prefixes
#             for prefix in ["Translation:", "Translated text:", "Here's the translation:"]:
#                 if translated.startswith(prefix):
#                     translated = translated[len(prefix):].strip()
            
#             # Validate script if we have a known script requirement
#             if script and not self._validate_script(translated, target_language):
#                 raise ValueError(f"Translation doesn't appear to be in {script} script")
                
#             cache.set(cache_key, translated, 60*60*24)  # Cache for 24 hours
#             return translated
            
#         except Exception as e:
#             print(f"Translation error for {language_name}: {e}")
#             return text  # Fallback to original text

#     def _validate_script(self, text, language_code):
#         """Validate the script matches the expected language script"""
#         SCRIPT_RANGES = {
#             'hi': r'[\u0900-\u097F]',  # Devanagari (Hindi, Marathi)
#             'mr': r'[\u0900-\u097F]',
#             'gu': r'[\u0A80-\u0AFF]',  # Gujarati
#             'ur': r'[\u0600-\u06FF]',  # Arabic/Nastaliq (basic range for Urdu)
#             'bn': r'[\u0980-\u09FF]',  # Bengali
#             'ta': r'[\u0B80-\u0BFF]',  # Tamil
#             'te': r'[\u0C00-\u0C7F]',  # Telugu
#             'kn': r'[\u0C80-\u0CFF]',  # Kannada
#             'ml': r'[\u0D00-\u0D7F]',  # Malayalam
#             'pa': r'[\u0A00-\u0A7F]',  # Gurmukhi (Punjabi)
#         }
        
#         if language_code not in SCRIPT_RANGES:
#             return True  # No validation for unknown languages
        
#         return bool(re.search(SCRIPT_RANGES[language_code], text))
        
#     def post(self, request):
#         """Handle user input with proper flow control"""
#         input_text = request.POST.get('input_text', '').strip()

#         # language_name = get_object_or_404(Language, code= language).name 
#         language_code = request.POST.get('selected_language') or request.session.get('language')

        
#         # 1. First handle contact collection if not completed
#         if input_text.lower() == "any other query":
#             request.session['awaiting_query'] = True
#             response_text = self._translate_text("Please write your query:", language_code)
#             self._log_chat(
#                 request=request,
#                 user_input=input_text,
#                 bot_response=response_text,
#                 menu_option=None
#             )
#             return JsonResponse({
#                 'response': "Please write your query:",
#                 'awaiting_query': True,
#                 'selected_language': request.session.get('language', 'en')
#             })
        
#         # Handle contact collection if not completed
#         if not request.session.get('collected_contact'):
#             return self._handle_contact_collection(request, input_text,language_code)
        
#         # Handle query input if awaiting
#         if request.session.get('awaiting_query'):
#             request.session.pop('awaiting_query', None)
#             if self._is_complex_query(input_text):
#                 return self._handle_human_support(request, input_text)
#             else:
#                 return self._handle_ai_response_user(input_text)
        
#         # 2. Handle language selection if not set (shouldn't normally happen after contact collection)
#         if 'selected_language' not in request.POST and 'language' not in request.session:
#             return self._handle_language_selection(input_text)
        
#         # Get selected language (from session if not in POST)
#         try:
#             language_code = request.POST.get('selected_language') or request.session.get('language')
#             language = Language.objects.get(
#                 Q(code=language_code),
#                 is_active=True
#             )
#             translation.activate(language.code)
#             request.session['language'] = language.code  # Ensure language is stored in session
#         except Language.DoesNotExist:
#             return JsonResponse({
#                 'error': 'Invalid language selected'
#             }, status=400)
        
#         # 3. Handle normal chat flow after contact collection
#         # Menu commands
#         if input_text.lower() in ['menu', 'main menu', 'home']:
#             request.session['current_menu_parent'] = None  # Reset to main menu
#             return self._get_main_menu(language)
        
#         # Check if input matches any menu option
#         menu_option = self._find_matching_menu_option(input_text, language)
#         if menu_option:
#             return self._handle_menu_selection(menu_option, language)
        
#         # Default response
#         return JsonResponse({
#             'response': self._translate_text(
#                 "Welcome !!! Please select from the menu options Below.",
#                 language.code
#             ),
#             'menu_options': self._get_menu_options(language, request.session.get('current_menu_parent'))
#         })
    
#     def _handle_language_selection(self, input_text):
#         """Process language selection"""
#         try:
#             if input_text.isdigit():
#                 language = Language.objects.filter(is_active=True).order_by('id')[int(input_text)-1]
#             else:
#                 language = Language.objects.get(
#                     Q(name__iexact=input_text) | Q(code__iexact=input_text),
#                     is_active=True
#                 )
            
#             welcome_msg = self._translate_text(
#                 "Welcome! How can I assist you today?",
#                 language.code
#             )
            
#             return JsonResponse({
#                 'response': welcome_msg,
#                 'menu_options': self._get_main_menu_options(language),
#                 'selected_language': language.code
#             })
        
#         except (IndexError, Language.DoesNotExist):
#             languages = Language.objects.filter(is_active=True)
#             options = "\n".join(
#                 f"{i+1}. {lang.name}" 
#                 for i, lang in enumerate(languages)
#             )
#             prompt_msg = "Please select a valid language:\n" + options
            
#             return JsonResponse({
#                 'response': prompt_msg
#             })
    
#     def _get_main_menu(self, language):
#         """Return the main menu in selected language"""
#         return JsonResponse({
#             'response': self._translate_text(
#                 "Please choose from the options below:",
#                 language.code
#             ),
#             'menu_options': self._get_menu_options(language, parent=None)  # Get root menu
#         })
    
#     def _get_menu_options(self, language, parent=None):
#         """
#         Get menu options based on parent
#         If parent is None, returns main menu options
#         """
#         menu_options = MenuOption.objects.filter(
#             parent=parent,
#             is_active=True
#         ).order_by('order')
        
#         return [
#             {
#                 'option_number': opt.option_number,
#                 'menu_text': self._translate_text(opt.menu_text, language.code),
#                 'original_id': opt.id,
#                 'has_children': opt.children.filter(is_active=True).exists()
#             }
#             for opt in menu_options
#         ]
    
#     def _find_matching_menu_option(self, input_text, language):
#         """Find matching menu option"""
#         # Get current parent from session or None for main menu
#         current_parent_id = self.request.session.get('current_menu_parent')
        
#         if input_text.isdigit():
#             try:
#                 return MenuOption.objects.get(
#                     option_number=input_text,
#                     parent_id=current_parent_id,
#                     is_active=True
#                 )
#             except MenuOption.DoesNotExist:
#                 pass
        
#         # Search in current menu level
#         menu_options = MenuOption.objects.filter(
#             parent_id=current_parent_id,
#             is_active=True
#         )
        
#         for option in menu_options:
#             if input_text.lower() in option.menu_text.lower():
#                 return option
        
#         return None
    

    

#     def _handle_contact_collection(self, request, input_text, language_code):
#         """Handle phone and email collection flow with language support"""
#         session = request.session
#         language = Language.objects.get(code=language_code)

#         # Clean the input - remove all non-digit characters for phone
#         cleaned_input = re.sub(r'\D', '', input_text) if input_text else ''
        
#         # PHONE NUMBER COLLECTION
#         if 'awaiting_phone' not in session and 'phone' not in session:
#             session['awaiting_phone'] = True
#             return JsonResponse({
#                 'response': self._translate_text(
#                     "Please enter your 10-digit Indian phone number:",
#                     language.code
#                 ),
#                 'collecting_contact': True,
#                 'awaiting_input': 'phone'
#             })
        
#         if 'awaiting_phone' in session and 'phone' not in session:
#             # Validate Indian phone number
#             if not re.match(r'^[6-9]\d{9}$', cleaned_input):
#                 return JsonResponse({
#                     'response': self._translate_text(
#                         "Please enter a valid 10-digit Indian phone number (should start with 6-9):",
#                         language.code
#                     ),
#                     'collecting_contact': True,
#                     'awaiting_input': 'phone'
#                 })
            
#             session['phone'] = cleaned_input
#             session.pop('awaiting_phone', None)
#             session['awaiting_email'] = True
#             return JsonResponse({
#                 'response': self._translate_text(
#                     "Thank you. Now please enter your email address:",
#                     language.code
#                 ),
#                 'collecting_contact': True,
#                 'awaiting_input': 'email'
#             })
        
#         # EMAIL COLLECTION
#         if 'awaiting_email' in session and 'email' not in session:
#             # Email validation should be in English only
#             if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', input_text):
#                 return JsonResponse({
#                     'response': self._translate_text(
#                         "Please enter a valid email address (e.g. example@gmail.com):",
#                         language.code
#                     ),
#                     'collecting_contact': True,
#                     'awaiting_input': 'email'
#                 })
            
#             try:
#                 # Check for previous sessions with this phone and email
#                 previous_sessions = ChatSession.objects.filter(
#                     phone_number=session['phone'],
#                     email=input_text
#                 ).order_by('-created_at')
                
#                 summary_response = ""
                
#                 if previous_sessions.exists():
#                     # Get the most recent session
#                     latest_session = previous_sessions.first()
                    
#                     # Get all chat logs for this session
#                     previous_chats = ChatLog.objects.filter(
#                         session_id=latest_session.id
#                     ).order_by('timestamp')
                    
#                     if previous_chats.exists():
#                         # Prepare conversation history for summary
#                         conversation_history = "\n".join(
#                             [f"{'User' if chat.user_input else 'Bot'}: {chat.bot_response}" 
#                             for chat in previous_chats]
#                         )
                        
#                         # Language mapping for Gemini prompt
#                         LANGUAGE_NAMES = {
#                             'hi': 'Hindi',
#                             'mr': 'Marathi',
#                             'gu': 'Gujarati',
#                             'ur': 'Urdu',
#                             'bn': 'Bengali',
#                             'ta': 'Tamil',
#                             'te': 'Telugu',
#                             'kn': 'Kannada',
#                             'ml': 'Malayalam',
#                             'pa': 'Punjabi',
#                             'en': 'English'
#                         }
                        
#                         # Generate summary prompt in the selected language
#                         summary_prompt = f"""
#                         Please provide a concise summary (2-3 sentences) in {LANGUAGE_NAMES.get(language_code, 'English')} 
#                         of this conversation history. Important instructions:
#                         1. Keep the summary brief and relevant
#                         2. Maintain context of the conversation
#                         3. Return ONLY the summary text in the requested language
#                         4. Use appropriate script for the language
#                         5. Never add explanations or notes
                        
#                         Conversation History:
#                         {conversation_history}
#                         """
                        
#                         # Get summary from Gemini
#                         model = genai.GenerativeModel('gemini-2.0-flash')
#                         response = model.generate_content(summary_prompt)
#                         summary_response = response.text.strip('"\'').strip()
                        
#                         # Remove common response prefixes if any
#                         for prefix in ["Summary:", "Here's the summary:", "Conversation summary:"]:
#                             if summary_response.startswith(prefix):
#                                 summary_response = summary_response[len(prefix):].strip()
                
#                 # Create new chat session
#                 chat_session = ChatSession.objects.create(
#                     phone_number=session['phone'],
#                     email=input_text,
#                     language=language.code
#                 )
                
#                 # Clear collection flags and set completion flag
#                 session.pop('awaiting_email', None)
#                 session['collected_contact'] = True
#                 session['chat_session_id'] = chat_session.id
                
#                 welcome_msg = self._translate_text(
#                     "Thank you! How can I assist you today?",
#                     language.code
#                 ) + (f"\n\n{summary_response}" if summary_response else "")
                
#                 # Add the "Do you want to talk about more?" prompt before menu
#                 menu_prompt = self._translate_text(
#                     "Do you want to talk about more? Please choose from below:",
#                     language.code
#                 )
                
#                 return JsonResponse({
#                     'response': f"{welcome_msg}\n\n{menu_prompt}",
#                     'show_menu': True,
#                     'menu_options': self._get_menu_options(language, None),  # Main menu
#                     'selected_language': language.code
#                 })
                
#             except Exception as e:
#                 print(f"Error saving contact: {str(e)}")
#                 return JsonResponse({
#                     'response': self._translate_text(
#                         "We encountered an error. Please start again.",
#                         language.code
#                     ),
#                     'reset_contact': True
#                 })
        

#     def _handle_menu_selection(self, menu_option, language):
#         """Process menu selection with 'Any Other Query' option in every response"""
#         # First check if this is the "Any Other Query" selection
#         # if menu_option.menu_text.lower() == "any other query":
#         #     self.request.session['awaiting_query'] = True
#         #     return JsonResponse({
#         #         'response': self._translate_text("Please write your query:", language.code),
#         #         'awaiting_query': True,
#         #         'selected_language': language.code
#         #     })
        
#         # Store current menu parent in session
#         self.request.session['current_menu_parent'] = menu_option.id
        
#         # Check if this menu has active submenus
#         has_children = menu_option.children.filter(is_active=True).exists()
        
#         if has_children:
#             # Get submenu options
#             menu_options = self._get_menu_options(language, menu_option)
            
#             response_text = self._translate_text(
#                 f"{menu_option.menu_text} - Please choose from the options below:",
#                 language.code
#             )
            
#             self._log_chat(
#                 request=self.request,
#                 user_input=menu_option.menu_text,
#                 bot_response=response_text,
#                 menu_option=menu_option
#             )
            
#             return JsonResponse({
#                 'response': response_text,
#                 'menu_options': menu_options,
#                 'footer_text': "Do you have any further questions?",  # Add this as separate field
#                 'selected_language': language.code,
#                 'is_submenu': True
#             })
#         else:
#             try:
#                 response = BotResponse.objects.get(menu_option=menu_option)
#                 translated_response = self._translate_text(
#                     response.response_text,
#                     language.code
#                 )
                
#                 self._log_chat(
#                     request=self.request,
#                     user_input=menu_option.menu_text,
#                     bot_response=translated_response,
#                     menu_option=menu_option
#                 )
                
#                 return JsonResponse({
#                     'response': translated_response,
#                     'media_url': response.media_url,
#                     'selected_language': language.code,
#                     'show_back_button': True,
#                     'show_other_query': True  # Flag to show "Any Other Query" option
#                 })
                
#             except BotResponse.DoesNotExist:
#                 # Fallback to AI response
#                 return self._handle_ai_response(menu_option, language)

#     def _log_chat(self, request, user_input, bot_response, menu_option=None, is_ai_response=False):
#         """Log chat interaction to database"""
#         if 'chat_session_id' in request.session:
#             ChatLog.objects.create(
#                 session_id=request.session['chat_session_id'],
#                 user_input=user_input,
#                 bot_response=bot_response,
#                 menu_option=menu_option,
#                 is_ai_response=is_ai_response
#             )

#     def _update_last_chat_log(self, request, bot_response):
#         """Update the most recent chat log entry with the bot's response"""
#         if 'chat_session_id' in request.session:
#             last_log = ChatLog.objects.filter(
#                 session_id=request.session['chat_session_id']
#             ).order_by('-timestamp').first()
            
#             if last_log:
#                 last_log.bot_response = bot_response
#                 last_log.save()


#     def _handle_ai_response(self, menu_option, language):
#         """Generate AI response using chat history"""
#         chat_history = ChatLog.objects.filter(
#             session_id=self.request.session['chat_session_id']
#         ).order_by('timestamp')
        
#         context = "\n".join(
#             f"User: {log.user_input}\nBot: {log.bot_response}" 
#             for log in chat_history
#         )
        
#         model = genai.GenerativeModel('gemini-2.0-flash')
#         prompt = f"""
#         You are a professional AI assistant for a manufacturing company.
#         Context from current conversation:
#         {context}
        
#         New user query: {menu_option.menu_text}
        
#         Please provide a helpful, accurate response in {language.code} language.
#         Important: 
#         - Keep technical terms in English if needed
#         - Be concise but informative
#         - Only return the response text, no explanations
#         """
        
#         try:
#             response = model.generate_content(prompt)
#             ai_response = response.text.strip()
#             translated_response = self._translate_text(ai_response, language.code)
            
#             self._log_chat(
#                 request=self.request,
#                 user_input=menu_option.menu_text,
#                 bot_response=translated_response,
#                 menu_option=menu_option,
#                 is_ai_response=True
#             )
            
#             return JsonResponse({
#                 'response': translated_response,
#                 'selected_language': language.code,
#                 'show_back_button': True,
#                 'show_other_query': True
#             })
            
#         except Exception as e:
#             print(f"AI Error: {str(e)}")
#             return self._get_main_menu(language)


#     def _handle_ai_response_user(self, input_text):
#         """Generate AI response for free-form queries in selected language"""
#         try:
#             # Get current language from session
#             language_code = self.request.session.get('language', 'en')
#             language = Language.objects.get(code=language_code)
            
#             # Get chat history for context
#             chat_history = ChatLog.objects.filter(
#                 session_id=self.request.session['chat_session_id']
#             ).order_by('timestamp')
            
#             # Prepare context
#             context = "\n".join(
#                 f"User: {log.user_input}\nBot: {log.bot_response}" 
#                 for log in chat_history
#             )
            
#             # Generate prompt with language specification
#             model = genai.GenerativeModel('gemini-2.0-flash')
#             prompt = f"""
#             You are a professional AI assistant for a manufacturing company.
#             Context from current conversation:
#             {context}
            
#             New user query: {input_text}
            
#             Please provide a helpful, accurate response in {language.name} language.
#             Important: 
#             - Keep technical terms in English if needed
#             - Be concise but informative
#             - Only return the response text, no explanations
#             - Respond in {language.name} language using appropriate script if needed
#             """
            
#             # Get AI response
#             response = model.generate_content(prompt)
#             ai_response = response.text.strip()
            
#             # Additional translation to ensure proper script if needed
#             translated_response = self._translate_text(ai_response, language.code)
            
#             # Log the interaction (both user input and bot response)
#             self._log_chat(
#                 request=self.request,
#                 user_input=input_text,
#                 bot_response=translated_response,
#                 menu_option=None,
#                 is_ai_response=True
#             )
            
#             return JsonResponse({
#                 'response': translated_response,
#                 'selected_language': language.code,
#                 'show_back_button': True,
#                 'show_other_query': True
#             })
            
#         except Exception as e:
#             print(f"AI Error: {str(e)}")
#             language_code = self.request.session.get('language', 'en')
#             error_msg = self._translate_text(
#                 "Sorry, I encountered an error. Please try again.",
#                 language_code
#             )
            
#             # Log the error
#             self._log_chat(
#                 request=self.request,
#                 user_input=input_text,
#                 bot_response=error_msg,
#                 menu_option=None,
#                 is_ai_response=True
#             )
            
#             return JsonResponse({
#                 'response': error_msg,
#                 'show_back_button': True,
#                 'selected_language': language_code
#             })

    
    
#     def _handle_human_support(self, request, query_text):
#         """Process complex queries that need human support"""
#         language = Language.objects.get(
#             code=request.session.get('language', 'en')
#         )
        
#         # Log the query
#         self._log_chat(
#             request,
#             query_text,
#             "Your  query has been recorded. Our team will contact you soon.",
#             None
#         )
        
#         return JsonResponse({
#             'response': self._translate_text(
#                 "Thank you for your query. Our team will contact you soon.",
#                 language.code
#             ),
#             'selected_language': language.code,
#             'show_back_button': True
#         })
    
#     def _is_complex_query(self, query_text):
#         """
#         Determine if a query is too complex for AI to handle.
#         Returns True for complex queries that should go to human support.
#         """
#         # Define indicators of complex queries
#         complex_indicators = [
#             'custom solution', 'enterprise', 'integration',
#             'consultation', 'specific requirement', 'detailed',
#             'complex', 'project', 'proposal', 'business need',
#             'urgent', 'custom development', 'tailored'
#         ]
        
#         # Check query length (more than 30 words is complex)
#         if len(query_text.split()) > 30:
#             return True 
        
#         # Check for complex indicators
#         query_lower = query_text.lower()
#         return any(
#             indicator in query_lower for indicator in complex_indicators
#         )
    

def convert_input_view(request):
    """Convert user input to selected language"""
    try:
        data = json.loads(request.body)
        text = data.get('text', '')
        language_code = data.get('language', 'en')
        
        if language_code == 'en' or not text:
            return JsonResponse({'converted_text': text})
        
        # Language mapping
        LANGUAGE_NAMES = {
            'hi': 'Hindi',
            'mr': 'Marathi',
            'gu': 'Gujarati',
            'ur': 'Urdu',
            'bn': 'Bengali',
            'ta': 'Tamil',
            'te': 'Telugu',
            'kn': 'Kannada',
            'ml': 'Malayalam',
            'pa': 'Punjabi'
        }
        
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = f"""
        Translate this text to {LANGUAGE_NAMES.get(language_code, language_code)}.
        Important Instructions:
        1. Keep technical terms in English if no translation exists
        2. Return ONLY the translated text
        3. Use appropriate script for the language
        4. Never add explanations or notes
        
        Text to translate: "{text}"
        """
        
        response = model.generate_content(prompt)
        translated = response.text.strip('"\'').strip()
        
        # Remove common response prefixes
        for prefix in ["Translation:", "Translated text:", "Here's the translation:"]:
            if translated.startswith(prefix):
                translated = translated[len(prefix):].strip()
        
        return JsonResponse({'converted_text': translated})
    
    except Exception as e:
        print(f"Conversion error: {str(e)}")
        return JsonResponse({'converted_text': text})
    


@login_required
def chat_session_list(request):
    """View all chat sessions with dropdown filters"""
    sessions = ChatSession.objects.all().prefetch_related('logs').order_by('-created_at')
    
    # Get filter parameters from request
    language_filter = request.GET.get('language')
    phone_filter = request.GET.get('phone')
    email_filter = request.GET.get('email')
    
    # Apply filters
    if language_filter:
        sessions = sessions.filter(language=language_filter)
    if phone_filter:
        sessions = sessions.filter(phone_number=phone_filter)
    if email_filter:
        sessions = sessions.filter(email=email_filter)
    
    # Get distinct values for dropdowns
    languages = Language.objects.filter(is_active=True)
    phone_numbers = ChatSession.objects.values_list('phone_number', flat=True).distinct().order_by('phone_number')
    emails = ChatSession.objects.values_list('email', flat=True).distinct().order_by('email')
    
    return render(request, 'Chat/chat_session_list.html', {
        'sessions': sessions,
        'languages': languages,
        'phone_numbers': phone_numbers,
        'emails': emails,
        'selected_language': language_filter,
        'selected_phone': phone_filter,
        'selected_email': email_filter
    })

@login_required
def chat_session_detail(request, reqno):
    """View details of a specific chat session with related menu options"""
    session = get_object_or_404(
        ChatSession.objects.prefetch_related('logs', 'logs__menu_option'),
        REQNO=reqno
    )
    
    # Get root menu options (constant for all chats)
    root_menu_options = MenuOption.objects.filter(parent__isnull=True).order_by('order')
    
    logs_with_menus = []
    for log in session.logs.all().order_by('timestamp'):
        log_data = {
            'log': log,
            'related_menu_options': None
        }
        
        # Only show menu options if this was a menu selection
        if log.menu_option:
            if log.menu_option.parent:
                log_data['related_menu_options'] = log.menu_option.parent.children.all()
            else:
                log_data['related_menu_options'] = root_menu_options
        
        logs_with_menus.append(log_data)
    
    return render(request, 'Chat/chat_session_detail.html', {
        'session': session,
        'logs_with_menus': logs_with_menus,
        'root_menu_options': root_menu_options,  # Pass constant root menu
        'initial_bot_message': "Welcome! How can I assist you today?"
    })

@login_required
def chat_log_search(request):
    """Search through chat logs"""
    query = request.GET.get('q', '')
    logs = ChatLog.objects.filter(
        Q(user_input__icontains=query) | 
        Q(bot_response__icontains=query))
    return render(request, 'Chat/log_search.html', {'logs': logs, 'query': query})


class ChatBotView(View):
    """Chatbot view with dynamic menu system"""
    
    def get(self, request, *args, **kwargs):
        # Clear all menu-related session data on fresh page load
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            menu_session_keys = [
                'current_menu_parent',
                'awaiting_query',
            ]
            for key in menu_session_keys:
                if key in request.session:
                    del request.session[key]
            
            # Only clear human support if starting fresh
            if 'chat_session_id' not in request.session:
                request.session.pop('human_support_requested', None)
            
        languages = list(Language.objects.filter(is_active=True).values('code', 'name'))
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'languages': languages})
        return render(request, 'Chat/chat.html', {
            'languages_json': json.dumps(languages),
            'languages': languages,
        })

    
    def _translate_text(self, text, target_language):
        """Universal translation function for all supported languages"""
        if target_language == 'en':
            return text
            
        # Language mapping with script requirements
        LANGUAGE_SCRIPTS = {
            'hi': ('Hindi', 'Devanagari'),
            'mr': ('Marathi', 'Devanagari'),
            'gu': ('Gujarati', 'Gujarati'),
            'ur': ('Urdu', 'Nastaliq'),
            'bn': ('Bengali', 'Bengali'),
            'ta': ('Tamil', 'Tamil'),
            'te': ('Telugu', 'Telugu'),
            'kn': ('Kannada', 'Kannada'),
            'ml': ('Malayalam', 'Malayalam'),
            'pa': ('Punjabi', 'Gurmukhi'),
        }
        
        # Get language details
        language_name, script = LANGUAGE_SCRIPTS.get(target_language, (target_language, None))
        
        cache_key = f"trans_{target_language}_{hashlib.md5(text.encode()).hexdigest()}"
        cached = cache.get(cache_key)
        if cached:
            return cached
            
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            prompt = f"""
            Translate this manufacturing menu item to {language_name}.
            Important Instructions:
            1. Keep technical terms in English if no translation exists
            2. Return ONLY the translated text
            3. Use {script} script if specified
            4. For Urdu, use proper Nastaliq script
            5. Never add explanations or notes
            
            Text to translate: "{text}"
            """
            
            response = model.generate_content(prompt)
            translated = response.text.strip('"\'').strip()
            
            # Remove common response prefixes
            for prefix in ["Translation:", "Translated text:", "Here's the translation:"]:
                if translated.startswith(prefix):
                    translated = translated[len(prefix):].strip()
            
            # Validate script if we have a known script requirement
            if script and not self._validate_script(translated, target_language):
                raise ValueError(f"Translation doesn't appear to be in {script} script")
                
            cache.set(cache_key, translated, 60*60*24)  # Cache for 24 hours
            return translated
            
        except Exception as e:
            print(f"Translation error for {language_name}: {e}")
            return text  # Fallback to original text

    def _validate_script(self, text, language_code):
        """Validate the script matches the expected language script"""
        SCRIPT_RANGES = {
            'hi': r'[\u0900-\u097F]',  # Devanagari (Hindi, Marathi)
            'mr': r'[\u0900-\u097F]',
            'gu': r'[\u0A80-\u0AFF]',  # Gujarati
            'ur': r'[\u0600-\u06FF]',  # Arabic/Nastaliq (basic range for Urdu)
            'bn': r'[\u0980-\u09FF]',  # Bengali
            'ta': r'[\u0B80-\u0BFF]',  # Tamil
            'te': r'[\u0C00-\u0C7F]',  # Telugu
            'kn': r'[\u0C80-\u0CFF]',  # Kannada
            'ml': r'[\u0D00-\u0D7F]',  # Malayalam
            'pa': r'[\u0A00-\u0A7F]',  # Gurmukhi (Punjabi)
        }
        
        if language_code not in SCRIPT_RANGES:
            return True  # No validation for unknown languages
        
        return bool(re.search(SCRIPT_RANGES[language_code], text))
        
    def post(self, request):
        """Handle user input with proper flow control"""
        input_text = request.POST.get('input_text', '').strip()
        language_code = request.POST.get('selected_language') or request.session.get('language')

        # Handle human support requests
        if request.session.get('human_support_requested'):
            if input_text.lower() in ['menu', 'main menu', 'home']:
                request.session.pop('human_support_requested', None)
                return self._get_main_menu(Language.objects.get(code=language_code))
            return JsonResponse({
                'response': self._translate_text(
                    "We have assigned a support representative to your case. They will contact you shortly. "
                    "To start a new conversation, please type 'home'.",
                    language_code
                ),
                'selected_language': language_code
            })

        # Handle contact collection if not completed
        if not request.session.get('collected_contact'):
            return self._handle_contact_collection(request, input_text, language_code)
        
        try:
            language = Language.objects.get(
                Q(code=language_code),
                is_active=True
            )
            translation.activate(language.code)
            request.session['language'] = language.code
        except Language.DoesNotExist:
            return JsonResponse({
                'error': 'Invalid language selected'
            }, status=400)
        
        # Check for direct language selection by text
        if not request.session.get('language_selected'):
            lang_match = self._detect_language_from_input(input_text)
            if lang_match:
                request.session['language_selected'] = True
                return self._handle_language_selection(lang_match.code)

        # Menu commands
        if input_text.lower() in ['menu', 'main menu', 'home']:
            request.session['current_menu_parent'] = None
            return self._get_main_menu(language)
        
        # Check if input matches any menu option
        menu_option = self._find_matching_menu_option(input_text, language)
        if menu_option:
            return self._handle_menu_selection(menu_option, language)
        
        # Handle free-form queries
        return self._handle_free_form_query(request, input_text, language)
    
    def _detect_language_from_input(self, input_text):
        """Detect language from text input"""
        if not input_text:
            return None
            
        input_text = input_text.lower().strip()
        languages = Language.objects.filter(is_active=True)
        
        # Check by number
        if input_text.isdigit():
            index = int(input_text) - 1
            if 0 <= index < len(languages):
                return languages[index]
        
        # Check by name or code
        for lang in languages:
            if (input_text == lang.name.lower() or 
                input_text == lang.code.lower()):
                return lang
        return None
    
    def _handle_free_form_query(self, request, input_text, language):
        """Handle direct user queries not matching menu options"""
        # First try to find a matching response in BotResponse
        try:
            # Search for exact match or similar question
            response = BotResponse.objects.filter(
                Q(response_text__icontains=input_text) |
                Q(menu_option__menu_text__icontains=input_text)
            ).first()
            
            if response:
                translated_response = self._translate_text(
                    response.response_text,
                    language.code
                )
                
                self._log_chat(
                    request=request,
                    user_input=input_text,
                    bot_response=translated_response,
                    menu_option=response.menu_option
                )
                
                return JsonResponse({
                    'response': translated_response,
                    'media_url': response.media_url,
                    'selected_language': language.code,
                    'show_back_button': True
                })
        except Exception as e:
            print(f"Error searching bot responses: {e}")
        
        # If no matching response found, assign to human support
        request.session['human_support_requested'] = True
        
        # Log the query
        self._log_chat(
            request,
            input_text,
            "Your query has been recorded and assigned to a support representative.",
            None
        )
        
        return JsonResponse({
            'response': self._translate_text(
                "Thank you for your query. We have assigned a support representative to your case. "
                "They will contact you shortly. For any further questions, please wait for their response.",
                language.code
            ),
            'selected_language': language.code,
            'show_back_button': True
        })
    
    def _handle_language_selection(self, input_text):
        """Process language selection"""
        try:
            if input_text.isdigit():
                language = Language.objects.filter(is_active=True).order_by('id')[int(input_text)-1]
            else:
                language = Language.objects.get(
                    Q(name__iexact=input_text) | Q(code__iexact=input_text),
                    is_active=True
                )
            
            welcome_msg = self._translate_text(
                "Welcome! How can I assist you today?",
                language.code
            )
            
            return JsonResponse({
                'response': welcome_msg,
                'menu_options': self._get_main_menu_options(language),
                'selected_language': language.code
            })
        
        except (IndexError, Language.DoesNotExist):
            languages = Language.objects.filter(is_active=True)
            options = "\n".join(
                f"{i+1}. {lang.name}" 
                for i, lang in enumerate(languages)
            )
            prompt_msg = "Please select a valid language:\n" + options
            
            return JsonResponse({
                'response': prompt_msg
            })
        
    def _get_main_menu_options(self, language):
        """Get main menu options for the specified language"""
        return self._get_menu_options(language, parent=None)
    
    def _get_main_menu(self, language):
        """Return the main menu in selected language"""
        return JsonResponse({
            'response': self._translate_text(
                "Please choose from the options below:",
                language.code
            ),
            'menu_options': self._get_menu_options(language, parent=None)
        })
    
    def _get_menu_options(self, language, parent=None):
        """
        Get menu options based on parent
        If parent is None, returns main menu options
        """
        menu_options = MenuOption.objects.filter(
            parent=parent,
            is_active=True
        ).order_by('order')
        
        return [
            {
                'option_number': opt.option_number,
                'menu_text': self._translate_text(opt.menu_text, language.code),
                'original_id': opt.id,
                'has_children': opt.children.filter(is_active=True).exists()
            }
            for opt in menu_options
        ]
    
    def _find_matching_menu_option(self, input_text, language):
        """Find matching menu option"""
        current_parent_id = self.request.session.get('current_menu_parent')
        
        if input_text.isdigit():
            try:
                return MenuOption.objects.get(
                    option_number=input_text,
                    parent_id=current_parent_id,
                    is_active=True
                )
            except MenuOption.DoesNotExist:
                pass
        
        # Search in current menu level
        menu_options = MenuOption.objects.filter(
            parent_id=current_parent_id,
            is_active=True
        )
        
        for option in menu_options:
            if input_text.lower() in option.menu_text.lower():
                return option
        
        return None
    
    def _handle_contact_collection(self, request, input_text, language_code):
        """Handle phone and email collection flow with language support"""
        session = request.session
        language = Language.objects.get(code=language_code)

        # Clean the input - remove all non-digit characters for phone
        cleaned_input = re.sub(r'\D', '', input_text) if input_text else ''
        
        # PHONE NUMBER COLLECTION
        if 'awaiting_phone' not in session and 'phone' not in session:
            session['awaiting_phone'] = True
            return JsonResponse({
                'response': self._translate_text(
                    "Please enter your 10-digit Indian phone number:",
                    language.code
                ),
                'collecting_contact': True,
                'awaiting_input': 'phone'
            })
        
        if 'awaiting_phone' in session and 'phone' not in session:
            # Validate Indian phone number
            if not re.match(r'^[6-9]\d{9}$', cleaned_input):
                return JsonResponse({
                    'response': self._translate_text(
                        "Please enter a valid 10-digit Indian phone number (should start with 6-9):",
                        language.code
                    ),
                    'collecting_contact': True,
                    'awaiting_input': 'phone'
                })
            
            session['phone'] = cleaned_input
            session.pop('awaiting_phone', None)
            session['awaiting_email'] = True
            return JsonResponse({
                'response': self._translate_text(
                    "Thank you. Now please enter your email address:",
                    language.code
                ),
                'collecting_contact': True,
                'awaiting_input': 'email'
            })
        
        # EMAIL COLLECTION
        if 'awaiting_email' in session and 'email' not in session:
            # Email validation should be in English only
            if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', input_text):
                return JsonResponse({
                    'response': self._translate_text(
                        "Please enter a valid email address (e.g. example@gmail.com):",
                        language.code
                    ),
                    'collecting_contact': True,
                    'awaiting_input': 'email'
                })
            
            try:
                # Create new chat session
                chat_session = ChatSession.objects.create(
                    phone_number=session['phone'],
                    email=input_text,
                    language=language.code
                )
                
                # Clear collection flags and set completion flag
                session.pop('awaiting_email', None)
                session['collected_contact'] = True
                session['chat_session_id'] = chat_session.id
                session['language_selected'] = True  # Add this line
                
                welcome_msg = self._translate_text(
                    "Thank you! How can I assist you today?",
                    language.code
                )
                
                return JsonResponse({
                    'response': welcome_msg,
                    'show_menu': True,
                    'menu_options': self._get_main_menu_options(language),
                    'selected_language': language.code
                })
                
            except Exception as e:
                print(f"Error saving contact: {str(e)}")
                return JsonResponse({
                    'response': self._translate_text(
                        "We encountered an error. Please start again.",
                        language.code
                    ),
                    'reset_contact': True
                })

    def _handle_menu_selection(self, menu_option, language):
        """Process menu selection"""
        self.request.session['current_menu_parent'] = menu_option.id
        
        has_children = menu_option.children.filter(is_active=True).exists()
        
        if has_children:
            menu_options = self._get_menu_options(language, menu_option)
            
            response_text = self._translate_text(
                f"{menu_option.menu_text} - Please choose from the options below:",
                language.code
            )
            
            enquiry_prompt = "<br><br>" + self._translate_text(
                "<b>If you have any further questions, please type them directly in the chat.</b>",
                language.code
            )
            
            self._log_chat(
                request=self.request,
                user_input=menu_option.menu_text,
                bot_response=response_text,
                menu_option=menu_option
            )
            
            return JsonResponse({
                'response': response_text,
                'menu_options': menu_options,
                'footer_text': enquiry_prompt,
                'selected_language': language.code,
                'is_submenu': True
            })
        else:
            try:
                response = BotResponse.objects.get(menu_option=menu_option)
                translated_response = self._translate_text(
                    response.response_text,
                    language.code
                )
                
                enquiry_prompt = "<br><br>" + self._translate_text(
                    "<b>If you have any further questions, please type them directly in the chat.</b>",
                    language.code
                )
                
                self._log_chat(
                    request=self.request,
                    user_input=menu_option.menu_text,
                    bot_response=translated_response,
                    menu_option=menu_option
                )
                
                return JsonResponse({
                    'response': translated_response,
                    'bot_footer_text': enquiry_prompt,
                    'media_url': response.media_url,
                    'selected_language': language.code,
                    'show_back_button': True
                })
            except BotResponse.DoesNotExist:
                return self._handle_ai_response(menu_option, language)

    def _log_chat(self, request, user_input, bot_response, menu_option=None, is_ai_response=False):
        """Log chat interaction to database"""
        if 'chat_session_id' in request.session:
            ChatLog.objects.create(
                session_id=request.session['chat_session_id'],
                user_input=user_input,
                bot_response=bot_response,
                menu_option=menu_option,
                is_ai_response=is_ai_response
            )

    def _update_last_chat_log(self, request, bot_response):
        """Update the most recent chat log entry with the bot's response"""
        if 'chat_session_id' in request.session:
            last_log = ChatLog.objects.filter(
                session_id=request.session['chat_session_id']
            ).order_by('-timestamp').first()
            
            if last_log:
                last_log.bot_response = bot_response
                last_log.save()

    def _handle_ai_response(self, menu_option, language):
        """Generate AI response using chat history"""
        chat_history = ChatLog.objects.filter(
            session_id=self.request.session['chat_session_id']
        ).order_by('timestamp')
        
        context = "\n".join(
            f"User: {log.user_input}\nBot: {log.bot_response}" 
            for log in chat_history
        )
        
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = f"""
        You are a professional AI assistant for a manufacturing company.
        Context from current conversation:
        {context}
        
        New user query: {menu_option.menu_text}
        
        Please provide a helpful, accurate response in {language.code} language.
        Important: 
        - Keep technical terms in English if needed
        - Be concise but informative
        - Only return the response text, no explanations
        """
        
        try:
            response = model.generate_content(prompt)
            ai_response = response.text.strip()
            translated_response = self._translate_text(ai_response, language.code)
            
            # Add enquiry prompt
            enquiry_prompt = "<br><br>" + self._translate_text(
                "<b>If you have any further questions, please type them directly in the chat.</b>",
                language.code
            )
            full_response = f"{translated_response}\n\n{enquiry_prompt}"
            
            self._log_chat(
                request=self.request,
                user_input=menu_option.menu_text,
                bot_response=full_response,
                menu_option=menu_option,
                is_ai_response=True
            )
            
            return JsonResponse({
                'response': full_response,
                'selected_language': language.code,
                'show_back_button': True
            })
            
        except Exception as e:
            print(f"AI Error: {str(e)}")
            return self._get_main_menu(language)