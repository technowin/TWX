import io
import json
import re
from PIL import Image
from pdf2image import convert_from_bytes
import google.generativeai as genai

class GeminiMetadataExtractor:
    def __init__(self):
        Image.MAX_IMAGE_PIXELS = 200000000  # Allow large images
        api_key = "AIzaSyAJWKnoo45JeoQxcwD5R8RUatPUZmVhEMU"
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.prompt = """
            You are a highly intelligent document and image parser with web-assisted reasoning.

            I will provide you with scanned PDF pages of a book, consisting of both printed and handwritten content. Your job is to extract **accurate metadata** from these pages. The metadata could be located anywhere — in headers, footers, stamps, typed paragraphs, handwritten margins, or titles — and may appear in different formats.

            If **any metadata field** is **unclear or missing** from the images, you must **use your trained knowledge and Google resources** to infer it as accurately as possible (e.g., title, author, publisher, etc.).

            Required output format (JSON):
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

            Important Notes:
            - "Pagination" may appear handwritten, such as: Pg 123, Pg:123, or Pg 123.
            - Use OCR capabilities for handwritten text and analyze all visible marks.
            - If you are unable to find a field from the document, intelligently infer it using your internet-based knowledge of known books.
            - Output should always be in English and in strict JSON format only (no extra text).
            """


    def extract_from_pdf(self, pdf_file, pages_to_process=3):
        try:
            pdf_file.seek(0)
            images = convert_from_bytes(
                pdf_file.read(),
                dpi=200,
                first_page=1,
                last_page=pages_to_process,
                fmt='jpeg',
                thread_count=3
            )
            extracted_data = []

            for image in images:
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG')
                img_bytes = img_byte_arr.getvalue()

                response = self.model.generate_content(
                    [self.prompt, Image.open(io.BytesIO(img_bytes))],
                    generation_config={"temperature": 0.1}
                )

                try:
                    json_str = re.search(r'\{.*\}', response.text, re.DOTALL).group()
                    data = json.loads(json_str)
                    extracted_data.append(data)
                except (AttributeError, json.JSONDecodeError):
                    print("Error parsing response, skipping page.")
                    continue

            return self._combine_results(extracted_data)

        except Exception as e:
            raise Exception(f"PDF processing error: {str(e)}")

    def _combine_results(self, extracted_data):
        if not extracted_data:
            return {k: None for k in [
                "language", "isbn_no", "title", "author", "edition",
                "publisher_name", "publisher_place", "year_of_publication",
                "accession_no", "class_no", "book_no", "pagination"
            ]}

        final = extracted_data[0]
        for entry in extracted_data[1:]:
            for key, value in entry.items():
                if not final.get(key) and value:
                    final[key] = value
        return final
