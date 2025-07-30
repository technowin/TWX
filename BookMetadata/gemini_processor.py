import os
import json
import re
import google.generativeai as genai
from django.conf import settings
from pdf2image import convert_from_bytes
from PIL import Image
import io

class GeminiMetadataExtractor:
    def __init__(self):
        Image.MAX_IMAGE_PIXELS = None  # Disable the check completely (not recommended)
        # OR set a higher limit
        Image.MAX_IMAGE_PIXELS = 200000000 
    
        api_key = "AIzaSyAJWKnoo45JeoQxcwD5R8RUatPUZmVhEMU"
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash') #gemini-2.0-flash
        
        self.prompt = """
                    You are an intelligent document parser. I will provide you with scanned PDF pages of a book that contain both printed and handwritten text.

                    Your task is to extract the following metadata from anywhere in the pages (regardless of order, handwriting, or print). The result should be returned in English only and structured as JSON.

                    Required fields:
                    - Language 
                    - ISBN No
                    - Title
                    - Author
                    - Edition
                    - Publisher Name
                    - Publisher Place
                    - Year of Publication
                    - Accession No
                    - Class No
                    - Book No
                    - Pagination – Extract the total number of pages, which may appear in printed or handwritten form (sometimes written in pencil). It typically starts with a prefix like "Pg" followed by a number (e.g., "Pg 135", "Pg: 135", or "Pg 135"). This information may appear anywhere in the document.

                    Please return the result strictly in the following JSON format:

                    {
                      "language": "",
                      "isbn_no": "",
                      "title": "",
                      "author": "",
                      "edition": "",
                      "publisher_name": "",
                      "publisher_place": "",
                      "year_of_publication": "",
                      "accession_no": "",
                      "class_no": "",
                      "book_no": "",
                      "pagination": ""
                    }
                    """

    def extract_from_pdf(self, pdf_file, pages_to_process=3):
        try:
            pdf_file.seek(0)

            # images = convert_from_bytes(pdf_file.read())
            images = convert_from_bytes(
                pdf_file.read(),
                dpi=200,  # Optimal balance between quality and size
                first_page=1,
                last_page=pages_to_process,
                fmt='jpeg',
                thread_count=4  # Use multiple threads for faster processing
            )
            processed_pages = min(pages_to_process, len(images))
            extracted_data = []
            
            for i in range(processed_pages):
                img_byte_arr = io.BytesIO()
                images[i].save(img_byte_arr, format='JPEG')
                img_byte_arr = img_byte_arr.getvalue()
                
                response = self.model.generate_content(
                    [self.prompt, Image.open(io.BytesIO(img_byte_arr))],
                    generation_config={"temperature": 0.1}
                )
                
                try:
                    json_str = re.search(r'\{.*\}', response.text, re.DOTALL).group()
                    data = json.loads(json_str)
                    extracted_data.append(data)
                except (AttributeError, json.JSONDecodeError):
                    continue
            
            return self._combine_results(extracted_data)
        
        except Exception as e:
            raise Exception(f"PDF processing error: {str(e)}")

    def _combine_results(self, extracted_data):
        if not extracted_data:
            return {
                "language": None,
                "isbn_no": None,
                "title": None,
                "author": None,
                "edition": None,
                "publisher_name": None,
                "publisher_place": None,
                "year_of_publication": None,
                "accession_no": None,
                "class_no": None,
                "book_no": None,
                "pagination": None
            }
        
        final_data = extracted_data[0]
        
        for data in extracted_data[1:]:
            for key, value in data.items():
                if key in final_data and not final_data[key] and value:
                    final_data[key] = value
        
        return final_data