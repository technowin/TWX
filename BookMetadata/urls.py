from django.urls import path
from .views import (BookListView, BookCreateView, BookUpdateView, BookDetailView
)
from .views import BookUploadView

urlpatterns = [
    path('book_list/', BookListView.as_view(), name='book_list'),
    path('create/', BookCreateView.as_view(), name='book_create'),
    path('<int:pk>/', BookDetailView.as_view(), name='book_detail'),
    path('<int:pk>/edit/', BookUpdateView.as_view(), name='book_update'),
    path('upload/', BookUploadView.as_view(), name='book_upload'),
]