from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from src.utils.gpt import (
    get_conversation_answer,
    get_gpt_title,
    get_simple_answer,
)


@api_view(["GET"])
@permission_classes([AllowAny])
def gpt_root_view(request):
    return JsonResponse({"message": "GPT endpoint works!"})



@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def get_title(request):
    data = request.data or {}
    title = get_gpt_title(data.get("user_question", ""))
    return JsonResponse({"content": title})


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def get_answer(request):
    data = request.data or {}
    return StreamingHttpResponse(
        get_simple_answer(data.get("user_question", ""), stream=True),
        content_type="text/plain",
    )



@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def get_conversation(request):
    data = request.data or {}
    return StreamingHttpResponse(
        get_conversation_answer(
            conversation=data.get("conversation", []),
            model=data.get("model"),
            stream=True,
        ),
        content_type="text/plain",
    )

    return StreamingHttpResponse(
        get_conversation_answer(
            conversation=conversation,
            stream=True,
        ),
        content_type="text/plain",
    )
