import os

import openai
from dotenv import load_dotenv

__all__ = ["openai"]
load_dotenv()

# TODO: The 'openai.api_base' option isn't read in the client API. You will need to pass it when you instantiate the client, e.g. 'OpenAI(base_url=os.getenv("OPENAI_API_BASE"))'
# openai.api_base = os.getenv("OPENAI_API_BASE")
