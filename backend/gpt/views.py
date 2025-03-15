from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, StreamingHttpResponse
from rest_framework.decorators import api_view
import openai
import os
from src.utils.gpt import get_conversation_answer, get_gpt_title, get_simple_answer
from rest_framework.response import Response

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"),base_url=os.getenv("OPENAI_BASE"))

@api_view(["POST"])
def chat_with_gpt(request):
    prompt = request.data.get("prompt", "Hello, ChatGPT!")  # Default prompt

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100
        )
        return Response({"response": response.choices[0].message.content})
    except Exception as e:
        return Response({"error": str(e)}, status=500)
    
@api_view(["GET"])
def gpt_root_view(request):
    return JsonResponse({"message": "GPT endpoint works!"})


@login_required
@api_view(["POST"])
def get_title(request):
    data = request.data
    title = get_gpt_title(data["user_question"], data["chatbot_response"])
    return JsonResponse({"content": title})


@login_required
@api_view(["POST"])
def get_answer(request):
    data = request.data
    return StreamingHttpResponse(get_simple_answer(data["user_question"], stream=True), content_type="text/html")


#@login_required
@api_view(["POST"])
def get_conversation(request):
    data = request.data
    return StreamingHttpResponse(
        get_conversation_answer(data["conversation"], data["model"], stream=True), content_type="text/html"
    )
