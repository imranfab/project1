import os

import openai
from dotenv import load_dotenv

__all__ = ["openai"]
load_dotenv()

openai.api_type = os.getenv("OPENAI_API_TYPE")
openai.api_base = os.getenv("OPENAI_API_BASE")
openai.Model = os.getenv("OPENAI_API_MODEL")
openai.api_key = os.getenv("OPENAI_API_KEY")
