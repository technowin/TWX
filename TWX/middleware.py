# your_app/middleware.py

import time
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse


class AutoLogoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.idle_time = settings.AUTO_LOGOUT.get('IDLE_TIME', 600)

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        current_time = int(time.time())
        last_activity = request.session.get('last_activity', current_time)
        elapsed_time = current_time - last_activity

        if elapsed_time > self.idle_time:
            logout(request)
            request.session.flush()

            if settings.AUTO_LOGOUT.get('REDIRECT_TO_LOGIN_IMMEDIATELY', True):
                message = settings.AUTO_LOGOUT.get('MESSAGE', '')
                if message:
                    messages.warning(request, message)
                return redirect(f"{settings.LOGIN_URL}?next={request.path}")

        request.session['last_activity'] = current_time
        return self.get_response(request)
