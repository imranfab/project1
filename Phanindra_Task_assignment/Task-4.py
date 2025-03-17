import base64
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from google import genai
from google.genai import types

load_dotenv()

def generate():
    client = genai.Client(
        api_key=os.environ.get("GOOGLE_GEMINI__API_KEY"),
    )

    model = "gemini-2.0-flash-exp"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text="""print("Hello World)"""),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        top_k=40,
        max_output_tokens=8192,
        response_mime_type="application/json",
        system_instruction=[
            types.Part.from_text(text="""Hello World"""),
        ],
    )

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        print(chunk.text, end="")

app = FastAPI(
    title="Conversation & Data Analytics API",
    description="API to retrieve conversation summaries, data analytics, and web crawler results.",
    version="1.0.0"
)

# Endpoint: Retrieve conversation summaries.
@app.get("/conversation-summary")
def get_conversation_summary():
    ...
    # return summaries



app = FastAPI(
    title="Conversation & Data Analytics API",
    description="API to retrieve conversation summaries, data analytics, and web crawler results.",
    version="1.0.0"
)

if __name__ == "__main__":
    generate()
