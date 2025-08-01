from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
import json
import google.generativeai as genai
from ChatBot.models import *
import os
from googletrans import Translator  

# Initialize Gemini (replace with your actual API key)
genai.configure(api_key='AIzaSyDYWMDZ25wRJtmAkjMLUH_7Oazrdpocrdc')

translator = Translator()

@csrf_exempt
def get_faq_answer(request):
    try:
        if request.method != 'POST':
            return JsonResponse({'error': 'Only POST requests allowed'}, status=405)

        user_question = request.POST.get('question', '').strip()
        lang = request.POST.get('lang', 'en')  # 'en', 'hi', 'mr'

        if not user_question:
            return JsonResponse({'answer': "❗ Please enter a message."})

        # Detect small talk
        small_talk_triggers = ['hi', 'hello', 'hey', 'thanks', 'thank you', 'ok', 'okay', 'bye']
        if user_question.lower() in small_talk_triggers:
            small_talk_responses = {
                'hi': "👋 Hello! How can I assist you today?",
                'hello': "👋 Hi there! What can I help you with?",
                'hey': "Hey! Need help with anything?",
                'thanks': "You're welcome! 😊",
                'thank you': "You're very welcome! 👍",
                'ok': "Got it! ✅",
                'okay': "Alright! Let me know if you have a question.",
                'bye': "Goodbye! 👋 Have a great day!"
            }
            return JsonResponse({'answer': small_talk_responses.get(user_question.lower())})

        # Translate question to English if needed
        if lang != 'en':
            user_question_translated = translator.translate(user_question, dest='en').text
        else:
            user_question_translated = user_question

        # Check for company-related queries
        company_keywords = ['company', 'your name', 'business', 'organization']
        if any(kw in user_question_translated.lower() for kw in company_keywords):
            company_response = (
                "🏢 Our company name is <strong>Technowin IT Infra Pvt. Ltd.</strong><br>"
                "🌐 Visit: <a href='https://technowinitinfra.com' target='_blank'>technowinitinfra.com</a><br>"
                "📞 Contact: +91-9999999999"
            )
            # Translate back if needed
            if lang != 'en':
                company_response = translator.translate(company_response, dest=lang).text
            return JsonResponse({'answer': company_response})

        # Get FAQs from DB
        faqs = Faq.objects.all()
        if not faqs:
            return JsonResponse({'answer': "📭 No FAQs available at the moment."})

        # Build FAQ context
        faq_text = "\n".join([f"Q: {faq.question_en}\nA: {faq.answer_en}" for faq in faqs])

        # Construct prompt
        prompt = f"""
You are a helpful assistant for Technowin IT Infra Pvt. Ltd.
Based on the FAQ list below, respond to the user's question.
If nothing matches well, say: "I couldn’t find a relevant answer. Please contact our team at 📞 +91-9999999999."

### FAQ List:
{faq_text}

### User Question:
{user_question_translated}

### Answer:
"""

        # Use Gemini
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        answer = response.text.strip()

        if not answer or "no relevant answer" in answer.lower():
            fallback = (
                "Hello. Please contact our team at 📞 "
                "<strong>+91-9999999999</strong>"
            )
            # Translate fallback if needed
            if lang != 'en':
                fallback = translator.translate(fallback, dest=lang).text
            return JsonResponse({'answer': fallback})

        # Translate Gemini answer back if needed
        if lang != 'en':
            answer = translator.translate(answer, dest=lang).text

        return JsonResponse({'answer': answer})

    except Exception as e:
        return JsonResponse({
            'answer': (
                "⚠️ Something went wrong while checking your question. Contact support at 📞 "
                "<strong>+91-9999999999</strong>"
            ),
            'error': str(e)
        })