import os
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def generate_conversation_summary(messages: list[str]) -> str:
    """
    Generates a short summary from conversation messages
    """
    if not messages:
        return ""

    prompt = (
        "Summarize the following conversation briefly:\n\n"
        + "\n".join(messages)
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=150,
    )
    print("response ======= ",response)
    return response.choices[0].message.content.strip()
