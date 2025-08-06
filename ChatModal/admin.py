# admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import *
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import ChatSession, ChatLog

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

# class ChatLogInline(admin.TabularInline):
#     model = ChatLog
#     extra = 0
#     readonly_fields = ('timestamp', 'user_input', 'bot_response', 'menu_option')

# @admin.register(ChatSession)
# class ChatSessionAdmin(admin.ModelAdmin):
#     list_display = ('REQNO', 'phone_number', 'email', 'language', 'created_at')
#     inlines = [ChatLogInline]
#     search_fields = ('REQNO', 'phone_number', 'email')
#     list_filter = ('language', 'created_at')

# @admin.register(ChatLog)
# class ChatLogAdmin(admin.ModelAdmin):
#     list_display = ('session', 'timestamp', 'short_user_input', 'short_bot_response')
#     list_filter = ('session', 'timestamp')
    
#     def short_user_input(self, obj):
#         return obj.user_input[:50] + '...' if len(obj.user_input) > 50 else obj.user_input
#     short_user_input.short_description = 'User Input'
    
#     def short_bot_response(self, obj):
#         return obj.bot_response[:50] + '...' if len(obj.bot_response) > 50 else obj.bot_response
#     short_bot_response.short_description = 'Bot Response'

class ChatLogInline(admin.TabularInline):
    model = ChatLog
    extra = 0
    readonly_fields = ('timestamp', 'formatted_interaction', 'menu_option', 'is_ai_response')
    fields = ('timestamp', 'formatted_interaction', 'menu_option', 'is_ai_response')
    
    def formatted_interaction(self, obj):
        return format_html(
            '<div style="margin-bottom: 10px; padding: 8px; border-radius: 5px; background-color: #f8f9fa;">'
            '<strong>👤 User:</strong> {}'
            '</div>'
            '<div style="margin-bottom: 10px; padding: 8px; border-radius: 5px; background-color: #e7f5ff;">'
            '<strong>🤖 Bot:</strong> {}'
            '</div>',
            obj.user_input,
            obj.bot_response
        )
    formatted_interaction.short_description = 'Chat Interaction'
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('REQNO', 'phone_link', 'email_link', 'language', 'created_at', 'message_count', 'chat_duration')
    list_filter = ('language', 'created_at')
    search_fields = ('REQNO', 'phone_number', 'email')
    readonly_fields = ('REQNO', 'created_at', 'updated_at', 'message_count', 'chat_duration')
    inlines = [ChatLogInline]
    list_per_page = 20
    
    fieldsets = (
        ('Session Information', {
            'fields': ('REQNO', 'phone_number', 'email', 'language')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('message_count', 'chat_duration'),
            'classes': ('collapse',)
        }),
    )
    
    def phone_link(self, obj):
        return format_html('<a href="tel:{0}">{0}</a>', obj.phone_number)
    phone_link.short_description = 'Phone'
    phone_link.admin_order_field = 'phone_number'
    
    def email_link(self, obj):
        return format_html('<a href="mailto:{0}">{0}</a>', obj.email)
    email_link.short_description = 'Email'
    email_link.admin_order_field = 'email'
    
    def message_count(self, obj):
        count = obj.logs.count()
        url = reverse('admin:chat_chatlog_changelist') + f'?session__id__exact={obj.id}'
        return format_html('<a href="{}">{}</a>', url, count)
    message_count.short_description = 'Messages'
    
    def chat_duration(self, obj):
        logs = obj.logs.order_by('timestamp')
        if logs.exists():
            duration = logs.last().timestamp - logs.first().timestamp
            minutes, seconds = divmod(duration.total_seconds(), 60)
            return f"{int(minutes)}m {int(seconds)}s"
        return "-"
    chat_duration.short_description = 'Duration'

@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ('session_link', 'timestamp', 'user_input_preview', 'bot_response_preview', 'is_ai_response', 'menu_option')
    list_filter = ('is_ai_response', 'timestamp', 'menu_option', 'session__language')
    search_fields = ('user_input', 'bot_response', 'session__REQNO')
    readonly_fields = ('timestamp', 'formatted_interaction')
    list_select_related = ('session', 'menu_option')
    list_per_page = 50
    
    fieldsets = (
        ('Session Information', {
            'fields': ('session_link',)
        }),
        ('Chat Details', {
            'fields': ('formatted_interaction', 'menu_option', 'is_ai_response', 'timestamp')
        }),
    )
    
    def session_link(self, obj):
        url = reverse('admin:chat_chatsession_change', args=[obj.session.id])
        return format_html('<a href="{}">{}</a>', url, obj.session.REQNO)
    session_link.short_description = 'Session'
    
    def user_input_preview(self, obj):
        return format_html(
            '<div style="max-width: 300px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{}">👤 {}</div>',
            obj.user_input, obj.user_input
        )
    user_input_preview.short_description = 'User Input'
    
    def bot_response_preview(self, obj):
        return format_html(
            '<div style="max-width: 300px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{}">🤖 {}</div>',
            obj.bot_response, obj.bot_response
        )
    bot_response_preview.short_description = 'Bot Response'
    
    def formatted_interaction(self, obj):
        return format_html(
            '<div style="margin-bottom: 15px; padding: 10px; border-radius: 5px; background-color: #f8f9fa; border-left: 4px solid #6c757d;">'
            '<strong>👤 User:</strong><br>{}'
            '</div>'
            '<div style="margin-bottom: 15px; padding: 10px; border-radius: 5px; background-color: #e7f5ff; border-left: 4px solid #0d6efd;">'
            '<strong>🤖 Bot:</strong><br>{}'
            '</div>',
            mark_safe(obj.user_input.replace('\n', '<br>')),
            mark_safe(obj.bot_response.replace('\n', '<br>'))
        )
    formatted_interaction.short_description = 'Full Interaction'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('session', 'menu_option')

admin.site.register(Language, LanguageAdmin)
admin.site.register(MenuOption, MenuOptionAdmin)
admin.site.register(BotResponse, BotResponseAdmin)
admin.site.register(Product, ProductAdmin)