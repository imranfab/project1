import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_summary(text: str) -> str:
    if not text.strip():
        return ""

    response = client.chat.completions.create(
       model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),



        messages=[
            {"role": "system", "content": "Summarize the conversation briefly."},
            {"role": "user", "content": text},
        ],
        max_tokens=120,
        temperature=0.3,
    )

    return response.choices[0].message.content.strip()


def get_conversation_answer(conversation, model=None, stream=False):
    """
    Respond ONLY to the latest user message.
    Prevents merging AI responses with user input.
    """

    if not conversation or not isinstance(conversation, list):
        return ""

    #  Find the LAST user message
    last_user_message = None
    for msg in reversed(conversation):
        if msg.get("role") == "user":
            last_user_message = msg.get("content", "")
            break

    if not last_user_message:
        return ""

    # Generate response ONLY for that message
    return generate_summary(last_user_message)



def get_simple_answer(prompt: str):
    return generate_summary(prompt)


def get_gpt_title(user_question: str) -> str:
    if not user_question:
        return "New Conversation"

    return generate_summary(user_question)


