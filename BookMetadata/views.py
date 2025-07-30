from django.shortcuts import render

# Create your views here.
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from .models import BookMetadata
from .forms import BookMetadataForm
from BookMetadata import models

class BookListView(ListView):
    model = BookMetadata
    template_name = 'BookMetadata/book_list.html'
    context_object_name = 'books'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        
        if search_query:
            queryset = queryset.filter(
                models.Q(title__icontains=search_query) |
                models.Q(author__icontains=search_query) |
                models.Q(isbn_no__icontains=search_query) |
                models.Q(publisher_name__icontains=search_query)
            )
        
        return queryset.order_by('-created_at')

class BookCreateView(CreateView):
    model = BookMetadata
    form_class = BookMetadataForm
    template_name = 'BookMetadata/book_form.html'
    success_url = reverse_lazy('book_list')
    success_message = "Book metadata was created successfully"

class BookUpdateView(UpdateView):
    model = BookMetadata
    form_class = BookMetadataForm
    template_name = 'BookMetadata/book_form.html'
    success_url = reverse_lazy('book_list')
    success_message = "Book metadata was updated successfully"

class BookDetailView(DetailView):
    model = BookMetadata
    template_name = 'BookMetadata/book_detail.html'
    context_object_name = 'book'



from django.views.generic import FormView
from django.core.files.base import ContentFile
from .forms import BookUploadForm
from .models import BookMetadata
from .gemini_processor import GeminiMetadataExtractor

class BookUploadView(FormView):
    template_name = 'BookMetadata/upload.html'
    form_class = BookUploadForm
    success_url = reverse_lazy('book_list')
    success_message = "Book metadata extracted and saved successfully"

    def form_valid(self, form):
        try:
            pdf_file = form.cleaned_data['pdf_file']
            pages_to_process = form.cleaned_data['process_pages']
            
            extractor = GeminiMetadataExtractor()
            metadata = extractor.extract_from_pdf(pdf_file, pages_to_process)
            
            # Save the original PDF
            # pdf_file.seek(0)
            # pdf_content = ContentFile(pdf_file.read())
            
            book = BookMetadata(
                is_auto_generated=True,
                **metadata
            )
            book.save()
            
            return super().form_valid(form)
        
        except Exception as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)