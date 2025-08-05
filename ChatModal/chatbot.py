# # chatbot.py
# from django.db.models import Q
# from .models import Language, MenuOption, BotResponse, Product, ChatSession, ChatMessage

# class ChatBot:
#     def __init__(self, session_id=None):
#         self.session_id = session_id
#         self.session = None
#         if session_id:
#             self._load_session()
    
#     def _load_session(self):
#         try:
#             self.session = ChatSession.objects.get(session_id=self.session_id)
#         except ChatSession.DoesNotExist:
#             self.session = None
    
#     def start_new_session(self):
#         """Create a new chat session"""
#         import uuid
#         self.session_id = str(uuid.uuid4())
#         self.session = ChatSession.objects.create(session_id=self.session_id)
#         return self.session_id
    
#     def get_language_options(self):
#         """Get available languages for initial selection"""
#         languages = Language.objects.filter(is_active=True)
#         return [
#             {
#                 'code': lang.code,
#                 'name': lang.name,
#                 'option_number': str(idx + 1)
#             }
#             for idx, lang in enumerate(languages)
#         ]
    
#     def set_language(self, language_code):
#         """Set language for the current session"""
#         try:
#             language = Language.objects.get(code=language_code, is_active=True)
#             if self.session:
#                 self.session.language = language
#                 self.session.current_menu = None  # Reset to root menu
#                 self.session.save()
#                 return True
#             return False
#         except Language.DoesNotExist:
#             return False
    
#     def get_welcome_message(self):
#         """Get welcome message based on selected language"""
#         if not self.session or not self.session.language:
#             return None
        
#         welcome_options = MenuOption.objects.filter(
#             parent__isnull=True,
#             language=self.session.language,
#             is_active=True
#         ).order_by('order')
        
#         welcome_text = f"Welcome to My Professional Services!\n\nPlease choose from the options below:\n"
#         welcome_text += "\n".join([
#             f"{opt.option_number}. {opt.menu_text}"
#             for opt in welcome_options
#         ])
        
#         # Store the root menu options as current context
#         self.session.current_menu = None
#         self.session.save()
        
#         return welcome_text
    
#     def process_input(self, user_input):
#         """Process user input and return bot response"""
#         if not self.session or not self.session.language:
#             return "Please select a language first."
        
#         # Clean the input
#         cleaned_input = user_input.strip().lower()
        
#         # Check if user wants to change language
#         if cleaned_input.startswith(('change language', 'switch language')):
#             return self._handle_language_change(cleaned_input)
        
#         # Get current menu context
#         current_menu = self.session.current_menu
        
#         # If no current menu, we're at the root level
#         if not current_menu:
#             return self._handle_root_menu(cleaned_input)
        
#         # Otherwise handle based on current menu context
#         return self._handle_menu_navigation(current_menu, cleaned_input)
    
#     def _handle_language_change(self, input_text):
#         """Handle language change request"""
#         # Extract language code or number from input
#         # This is a simplified version - you might want to enhance it
#         lang_options = self.get_language_options()
#         for lang in lang_options:
#             if lang['name'].lower() in input_text or lang['code'] in input_text:
#                 if self.set_language(lang['code']):
#                     return f"Language changed to {lang['name']}.\n\n{self.get_welcome_message()}"
#         return "Sorry, I didn't understand which language you want to switch to."
    
#     def _handle_root_menu(self, input_text):
#         """Handle input at the root menu level"""
#         # Try to match by option number first
#         menu_options = MenuOption.objects.filter(
#             parent__isnull=True,
#             language=self.session.language,
#             is_active=True
#         ).order_by('order')
        
#         # Check for exact number match
#         matched_option = None
#         for option in menu_options:
#             if input_text == option.option_number.lower():
#                 matched_option = option
#                 break
        
#         # If no number match, try to match by menu text keywords
#         if not matched_option:
#             for option in menu_options:
#                 if option.menu_text.lower() in input_text or input_text in option.menu_text.lower():
#                     matched_option = option
#                     break
        
#         if matched_option:
#             self.session.current_menu = matched_option
#             self.session.save()
#             return self._get_response_for_menu(matched_option)
        
#         return "Sorry, I didn't understand your selection. Please choose a valid option number."
    
#     def _handle_menu_navigation(self, current_menu, input_text):
#         """Handle navigation within submenus"""
#         # Check if user wants to go back
#         if input_text in ('back', 'go back', 'return', 'b', '🔙'):
#             if current_menu.parent:
#                 self.session.current_menu = current_menu.parent
#                 self.session.save()
#                 return self._get_response_for_menu(current_menu.parent)
#             else:
#                 self.session.current_menu = None
#                 self.session.save()
#                 return self.get_welcome_message()
        
#         # Get child options for current menu
#         child_options = MenuOption.objects.filter(
#             parent=current_menu,
#             language=self.session.language,
#             is_active=True
#         ).order_by('order')
        
#         # Try to match by option number
#         matched_option = None
#         for option in child_options:
#             if input_text == option.option_number.lower():
#                 matched_option = option
#                 break
        
#         # If no number match, try to match by menu text keywords
#         if not matched_option:
#             for option in child_options:
#                 if option.menu_text.lower() in input_text or input_text in option.menu_text.lower():
#                     matched_option = option
#                     break
        
#         if matched_option:
#             # If the matched option is a menu, update context
#             if matched_option.response_type == 'menu':
#                 self.session.current_menu = matched_option
#                 self.session.save()
#             return self._get_response_for_menu(matched_option)
        
#         # Handle special cases like product queries
#         if current_menu.menu_text.lower() in ('know about our products', 'products'):
#             return self._handle_product_query(input_text)
        
#         # Handle order tracking
#         if current_menu.menu_text.lower() in ('track existing order', 'track order'):
#             return "Please enter your Order ID or mobile number used during order."
        
#         return "Sorry, I didn't understand your selection. Please choose a valid option number."
    
#     def _get_response_for_menu(self, menu_option):
#         """Get the appropriate response for a menu option"""
#         if menu_option.response_type == 'menu':
#             # Show submenu options
#             child_options = MenuOption.objects.filter(
#                 parent=menu_option,
#                 language=self.session.language,
#                 is_active=True
#             ).order_by('order')
            
#             response_text = f"{menu_option.menu_text}\n\nPlease select from the options below:\n"
#             response_text += "\n".join([
#                 f"{opt.option_number}. {opt.menu_text}"
#                 for opt in child_options
#             ])
#             return response_text
#         else:
#             # Get the predefined response
#             try:
#                 response = BotResponse.objects.get(
#                     menu_option=menu_option,
#                     language=self.session.language
#                 )
#                 return response.response_text
#             except BotResponse.DoesNotExist:
#                 return "Sorry, I don't have a response for that option."
    
#     def _handle_product_query(self, input_text):
#         """Handle product-related queries"""
#         # This is a simplified version - you might want to enhance it
#         products = Product.objects.filter(
#             Q(name__icontains=input_text) | Q(code__iexact=input_text),
#             is_active=True
#         )[:5]  # Limit to 5 results
        
#         if products:
#             response = "Here are the matching products:\n\n"
#             for product in products:
#                 response += f"- {product.name} ({product.code}): ₹{product.price_per_unit}\n"
#             response += "\nFor more details, please select a product number or ask specifically."
#             return response
        
#         return "Sorry, I couldn't find any products matching your query. Please try again."