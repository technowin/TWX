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
import traceback

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
        
        # except Exception as e:
        #     form.add_error(None, str(e))
        #     return self.form_invalid(form)
        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }, status=500)
        

# views.py
from django.http import JsonResponse
import vertexai
from vertexai.generative_models import GenerativeModel

def test_vertex_ai(request):
    try:
        # Initialize Vertex AI
        vertexai.init(project="powerful-lore-471112-k7", location="us-central1")
        
        # Load Gemini model
        model = GenerativeModel("gemini-2.5-flash")

        # Ask a test prompt
        response = model.generate_content("Hello! Respond with a JSON object: {\"status\": \"ok\", \"message\": \"Vertex AI is working in production\"}")
        
        # Try parsing as JSON if possible
        import json, re
        try:
            json_str = re.search(r"\{.*\}", response.text, re.DOTALL).group()
            data = json.loads(json_str)
        except Exception:
            # Fallback to plain text if not JSON
            data = {"status": "ok", "response": response.text}
        
        return JsonResponse(data, safe=False)
    
    except Exception as e:
        return JsonResponse({"status": "error", "error": str(e)}, status=500)


import mysql.connector
import pyodbc

def copy_users_mysql_to_mssql():
    # --- MySQL connection ---
    mysql_conn = mysql.connector.connect(
        host="13.232.86.95",
        user="root",
        password="Mysql_MH-047319",
        database="twx_db"
    )
    mysql_cursor = mysql_conn.cursor()

    # --- MSSQL connection ---
    mssql_conn = pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=52.172.154.80;"
        "DATABASE=ESIC;"
        "UID=sa;"
        "PWD=ecNlWdur7HpKyZ8zTuLz;"
        "Encrypt=no;"
    )
    mssql_cursor = mssql_conn.cursor()

    # --- Copy rows ---
    mysql_cursor.execute("SELECT full_name, email, phone FROM users LIMIT 10")
    rows = mysql_cursor.fetchall()

    insert_sql = "INSERT INTO test_users (full_name, email, phone) VALUES (?, ?, ?)"
    for row in rows:
        mssql_cursor.execute(insert_sql, row)

    mssql_conn.commit()

    mysql_conn.close()
    mssql_conn.close()

    return f"Copied {len(rows)} rows"



def copy_users_view(request):
    try:
        message = copy_users_mysql_to_mssql()
        return JsonResponse({"status": "success", "message": message})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)