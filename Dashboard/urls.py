from django.urls import path
from . import views

urlpatterns = [
    path('/dashboard/', views.powerbi_dashboard_view, name='dashboard'),
]