# admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import *

class LanguageAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('name', 'code')

class MenuOptionAdmin(admin.ModelAdmin):
    list_display = ('menu_text', 'option_number', 'parent', 'language', 'response_type', 'is_active')
    list_filter = ('language', 'parent', 'response_type', 'is_active')
    search_fields = ('menu_text', 'option_number')
    list_editable = ('is_active', 'option_number', 'response_type')
    raw_id_fields = ('parent',)

class BotResponseAdmin(admin.ModelAdmin):
    list_display = ('menu_option', 'truncated_response')
    list_filter = ('media_url','menu_option')
    search_fields = ('response_text', 'menu_option__menu_text')
    
    def truncated_response(self, obj):
        return obj.response_text[:50] + '...' if len(obj.response_text) > 50 else obj.response_text
    truncated_response.short_description = _('Response')

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'category', 'price_per_unit', 'lead_time_days', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'code')
    list_editable = ('price_per_unit', 'lead_time_days', 'is_active')

class ChatLogInline(admin.TabularInline):
    model = ChatLog
    extra = 0
    readonly_fields = ('timestamp', 'user_input', 'bot_response', 'menu_option')

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('REQNO', 'phone_number', 'email', 'language', 'created_at')
    inlines = [ChatLogInline]
    search_fields = ('REQNO', 'phone_number', 'email')
    list_filter = ('language', 'created_at')

@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ('session', 'timestamp', 'short_user_input', 'short_bot_response')
    list_filter = ('session', 'timestamp')
    
    def short_user_input(self, obj):
        return obj.user_input[:50] + '...' if len(obj.user_input) > 50 else obj.user_input
    short_user_input.short_description = 'User Input'
    
    def short_bot_response(self, obj):
        return obj.bot_response[:50] + '...' if len(obj.bot_response) > 50 else obj.bot_response
    short_bot_response.short_description = 'Bot Response'

admin.site.register(Language, LanguageAdmin)
admin.site.register(MenuOption, MenuOptionAdmin)
admin.site.register(BotResponse, BotResponseAdmin)
admin.site.register(Product, ProductAdmin)