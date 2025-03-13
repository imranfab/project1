from dataclasses import dataclass
from src.libs import openai
from chat.models import Conversation

GPT_40_PARAMS = dict(
    temperature=0.7,
    top_p=0.95,
    frequency_penalty=0,
    presence_penalty=0,
    stop=None,
    stream=True,
)

@dataclass
class GPTVersion:
    name: str
    model: str  

GPT_VERSIONS = {
    "gpt35": GPTVersion("gpt35", "gpt-3.5-turbo"),
    "gpt35-16k": GPTVersion("gpt35-16k", "gpt-3.5-turbo-16k"),
    "gpt4": GPTVersion("gpt4", "gpt-4"),
    "gpt4-32k": GPTVersion("gpt4-32k", "gpt-4-32k"),
}



def get_simple_answer(prompt: str, stream: bool = True):
    kwargs = {**GPT_40_PARAMS, **dict(stream=stream)}

    for resp in openai.ChatCompletion.create(
        model=GPT_VERSIONS["gpt35"].model,  
        messages=[{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": prompt}],
        **kwargs,
    ):
        choices = resp.get("choices", [])
        if not choices:
            continue
        chunk = choices.pop()["delta"].get("content")
        if chunk:
            yield chunk



def get_gpt_title(prompt: str, response: str):
    sys_msg: str = (
        "As an AI Assistant your goal is to make very short title, few words max for a conversation between user and "
        "chatbot. You will be given the user's question and chatbot's first response and you will return only the "
        "resulting title. Always return some raw title and nothing more."
    )
    usr_msg = f'user_question: "{prompt}"\n' f'chatbot_response: "{response}"'

    response = openai.ChatCompletion.create(
        model=GPT_VERSIONS["gpt35"].model,  
        messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": usr_msg}],
        **GPT_40_PARAMS,
    )

    result = response["choices"][0]["message"]["content"].replace('"', "")
    return result


def get_conversation_answer(conversation: list[dict[str, str]], model: str, stream: bool = True):
    kwargs = {**GPT_40_PARAMS, **dict(stream=stream)}
    model_name = GPT_VERSIONS[model].model 

    for resp in openai.ChatCompletion.create(
        model=model_name,  
        messages=[{"role": "system", "content": "You are a helpful assistant."}, *conversation],
        **kwargs,
    ):
        choices = resp.get("choices", [])
        if not choices:
            continue
        chunk = choices.pop()["delta"].get("content")
        if chunk:
            yield chunk


# generate summary
def generate_summary(conversation: list[dict[str, str]], model: str):
    sys_msg = "You are an AI that summarizes conversations concisely. Your task is to create a brief summary of the conversation."
    messages = [{"role": "system", "content": sys_msg}] + conversation

    model_name = GPT_VERSIONS[model].model

    response = openai.ChatCompletion.create(
        model=model_name,
        messages=messages,
        **GPT_40_PARAMS,
    )

    summary = response["choices"][0]["message"]["content"].strip()

    return summary

# Function to update the conversation with the summary
def update_conversation_summary(conversation_id: str, model: str):
    conversation = Conversation.objects.get(id=conversation_id)  # Fetch the conversation
    # Assuming that conversation.messages is a list of message dictionaries
    conversation_summary = generate_summary(conversation.messages, model)  # Generate the summary
    conversation.summary = conversation_summary  # Update the summary field
    conversation.save()  # Save the updated conversation
    print(conversation)


def get_conversation_summary(conversation_id: str):
    try:
        conversation = Conversation.objects.get(id=conversation_id)  # Fetch the conversation by its ID
        if conversation.summary:
            print(conversation.summary)
            return conversation.summary  # Return the summary if available
        else:
            return "No summary available."  # Return a default message if no summary exists
    except Conversation.DoesNotExist:
        return "Conversation not found."  # Return an error message if the conversation is not found