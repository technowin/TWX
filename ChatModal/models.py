from django.db import models

# Create your models here.
# models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import validate_email, RegexValidator

class Faq(models.Model):
    id = models.AutoField(primary_key=True)  # Optional, Django does this for you
    question_en = models.TextField(null=True, blank=True)
    answer_en = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'faq'

# models.py
from django.db import models
from django.utils.translation import gettext_lazy as _

class Language(models.Model):
    """Stores supported languages for the chatbot"""
    code = models.CharField(max_length=10, unique=True, help_text=_("ISO language code (e.g., en, hi, mr)"))
    name = models.CharField(max_length=50, help_text=_("Display name of the language"))
    is_active = models.BooleanField(default=True, help_text=_("Whether this language is available"))
    
    class Meta:
        verbose_name = _("Language")
        verbose_name_plural = _("Languages")
    
    def __str__(self):
        return f"{self.name} ({self.code})"

class MenuOption(models.Model):
    """Hierarchical menu structure for the chatbot"""
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='children',
        help_text=_("Parent menu item, null for root items")
    )
    language = models.ForeignKey(
        Language, 
        on_delete=models.CASCADE,
        help_text=_("Language for this menu option")
    )
    option_number = models.CharField(
        max_length=10,
        help_text=_("Display number (e.g., 1, 2a, 3b)")
    )
    menu_text = models.TextField(help_text=_("Text to display for this menu option"))
    response_type = models.CharField(
        max_length=20,
        choices=[
            ('menu', _('Menu')),
            ('response', _('Response')),
            ('input', _('Requires Input'))
        ],
        default='menu',
        help_text=_("Type of response expected")
    )
    is_active = models.BooleanField(default=True, help_text=_("Whether this menu option is available"))
    order = models.PositiveIntegerField(default=0, help_text=_("Ordering of menu items"))
    
    class Meta:
        verbose_name = _("Menu Option")
        verbose_name_plural = _("Menu Options")
        ordering = ['order', 'option_number']
    
    def __str__(self):
        return f"{self.option_number}. {self.menu_text} ({self.language.code})"

class BotResponse(models.Model):
    """Stores bot responses for menu options"""
    menu_option = models.ForeignKey(
        MenuOption, 
        on_delete=models.CASCADE,
        related_name='responses',
        help_text="Linked menu option"
    )
    response_text = models.TextField(help_text="Bot's reply text")
    media_url = models.URLField(
        max_length=500, 
        null=True, 
        blank=True,
        help_text="URL to media file if attached"
    )
    
    class Meta:
        verbose_name = _("Bot Response")
        verbose_name_plural = _("Bot Responses")
    
    def __str__(self):
        return f"Response for {self.menu_option})"

class Product(models.Model):
    """Stores product information for dynamic queries"""
    CATEGORY_CHOICES = [
        ('pipe', 'Pipe Clamps'),
        ('hydraulic', 'Hydraulic Clamps'),
        ('custom', 'Customized Clamping Systems'),
    ]
    
    name = models.CharField(max_length=200, help_text="Product name")
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        help_text="Product category"
    )
    code = models.CharField(
        max_length=50, 
        unique=True,
        help_text="Product code/SKU"
    )
    price_per_unit = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Price per unit"
    )
    lead_time_days = models.PositiveIntegerField(
        default=7,
        help_text="Standard delivery time in days"
    )
    spec_link = models.URLField(
        max_length=500, 
        null=True, 
        blank=True,
        help_text="URL to product specifications"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this product is available"
    )
    
    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class ChatSession(models.Model):
    REQNO = models.CharField(max_length=20, unique=True, editable=False)
    phone_regex = RegexValidator(
        regex=r'^[6-9]\d{9}$',  # Indian mobile numbers start with 6-9 and have 10 digits
        message="Please enter a valid 10-digit Indian phone number (no country code or special characters)"
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17)
    email = models.EmailField(validators=[validate_email])
    language = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.REQNO:
            last_record = ChatSession.objects.order_by('-id').first()
            last_id = last_record.id if last_record else 0
            self.REQNO = f"REQNO-{last_id + 1}"
        super().save(*args, **kwargs)

class ChatLog(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='logs')
    user_input = models.TextField()
    bot_response = models.TextField()
    menu_option = models.ForeignKey('MenuOption', null=True, blank=True, on_delete=models.SET_NULL)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_ai_response = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['timestamp']



