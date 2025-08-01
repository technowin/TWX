from django.db import models

from django.db import models
from django.utils.translation import gettext_lazy as _

from django.db import models
class Faq(models.Model):
    id = models.AutoField(primary_key=True)  # Optional, Django does this for you
    question_en = models.TextField(null=True, blank=True)
    answer_en = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'faq'

#

class Language(models.Model):
    """Stores supported languages for the chatbot"""
    code = models.CharField(max_length=10, unique=True, help_text="ISO language code (e.g., en, hi, mr)")
    name = models.CharField(max_length=50, help_text="Display name of the language")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = _("Language")
        verbose_name_plural = _("Languages")
    
    def __str__(self):
        return f"{self.name} ({self.code})"

class MenuOption(models.Model):
    """Hierarchical menu structure for the chatbot"""
    parent_menu = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                                  related_name='children', help_text="Parent menu item")
    language = models.ForeignKey(Language, on_delete=models.CASCADE, help_text="Language for this menu option")
    option_number = models.CharField(max_length=10, help_text="Display number (e.g., 1, 2a, 3b)")
    menu_text = models.TextField(help_text="Text to display for this menu option")
    response_type = models.CharField(max_length=20, choices=[
        ('menu', 'Menu'),
        ('response', 'Response'),
        ('input', 'User Input Required')
    ], default='menu')
    is_active = models.BooleanField(default=True)
    requires_user_input = models.BooleanField(default=False, help_text="Does this option require user input?")
    input_prompt = models.TextField(blank=True, null=True, help_text="Prompt to show when input is required")
    
    class Meta:
        verbose_name = _("Menu Option")
        verbose_name_plural = _("Menu Options")
        unique_together = ('parent_menu', 'language', 'option_number')
        ordering = ['option_number']
    
    def __str__(self):
        return f"{self.option_number}. {self.menu_text} ({self.language.code})"

class BotResponse(models.Model):
    """Stores bot responses for selected menu options"""
    menu_option = models.ForeignKey(MenuOption, on_delete=models.CASCADE, related_name='responses')
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    response_text = models.TextField(help_text="Bot's reply text")
    media_url = models.URLField(blank=True, null=True, help_text="URL for attached media/file")
    additional_actions = models.JSONField(blank=True, null=True, help_text="Additional actions or metadata")
    
    class Meta:
        verbose_name = _("Bot Response")
        verbose_name_plural = _("Bot Responses")
    
    def __str__(self):
        return f"Response for {self.menu_option} in {self.language}"

class Product(models.Model):
    """Stores product information for dynamic queries"""
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, choices=[
        ('pipe', 'Pipe Clamps'),
        ('hydraulic', 'Hydraulic Clamps'),
        ('custom', 'Customized Clamping Systems')
    ])
    product_code = models.CharField(max_length=50, unique=True)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    lead_time_days = models.PositiveIntegerField(help_text="Standard delivery time in days")
    spec_link = models.URLField(blank=True, null=True, help_text="URL for product specifications")
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.product_code})"

class ChatSession(models.Model):
    """Tracks user chat sessions"""
    session_id = models.CharField(max_length=100, unique=True)
    current_language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True)
    current_menu = models.ForeignKey(MenuOption, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user_data = models.JSONField(default=dict, blank=True, help_text="Stores temporary user data during session")
    
    class Meta:
        verbose_name = _("Chat Session")
        verbose_name_plural = _("Chat Sessions")
    
    def __str__(self):
        return f"Session {self.session_id}"

class ChatMessage(models.Model):
    """Stores chat messages for history"""
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    message_text = models.TextField()
    is_user = models.BooleanField(default=False, help_text="Is this message from the user?")
    timestamp = models.DateTimeField(auto_now_add=True)
    menu_option = models.ForeignKey(MenuOption, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = _("Chat Message")
        verbose_name_plural = _("Chat Messages")
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{'User' if self.is_user else 'Bot'}: {self.message_text[:50]}"