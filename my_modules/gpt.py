import os
import requests
import openai
import tiktoken
from typing import List
import re
import copy
import json

from classes.ConfigManagerClass import ConfigManager

from my_modules import utils
from my_modules.my_logging import create_logger

#LOGGING
stream_logs = True
runtime_logger_level = 'INFO'

#Config
config = ConfigManager.get_instance()

gpt_model = config.gpt_model
shorten_message_prompt = config.shorten_response_length

logger = create_logger(
    dirname='log',
    logger_name='logger_gpt',
    debug_level=runtime_logger_level,
    mode='w',
    stream_logs=stream_logs
    )

def create_gpt_client():
    client = openai.OpenAI(api_key = config.openai_api_key)
    return client

def _strip_prefix(text):
    # Regular expression pattern to match the prefix <<<[some_name]>>>:
    pattern = r'<<<[^>]*>>>'
    
    # Use re.sub() to replace the matched pattern with an empty string
    stripped_text = re.sub(pattern, '', text)
    
    return stripped_text

# call to chat gpt for completion TODO: Could add  limits here?
def openai_gpt_chatcompletion(
        messages_dict_gpt:list[dict],
        max_characters=300,
        max_attempts=3,
        model=gpt_model,
        frequency_penalty=1,
        presence_penalty=1,
        temperature=0.6
        ) -> str: 
    """
    Sends a list of messages to the OpenAI GPT model and retrieves a generated response.

    This function interacts with the OpenAI GPT model to generate responses based on the provided message structure. It attempts to ensure the response is within a specified character limit, retrying up to a maximum number of attempts if necessary.

    Parameters:
    - messages_dict_gpt (list[dict]): A list of dictionaries, each representing a message in the conversation history, formatted for the GPT prompt.
    - max_characters (int): Maximum allowed character count for the generated response. Default is 200 characters.
    - max_attempts (int): Maximum number of attempts to generate a response within the character limit. Default is 5 attempts.
    - model: The specific GPT model used for generating the response.
    - frequency_penalty (float): The frequency penalty parameter to control repetition in the response. Default is 1.
    - presence_penalty (float): The presence penalty parameter influencing the introduction of new concepts in the response. Default is 1.
    - temperature (float): Controls randomness in the response generation. Lower values make responses more deterministic. Default is 0.6.

    Returns:
    - str: The content of the message generated by the GPT model. If the maximum number of attempts is exceeded without generating a response within the character limit, an exception is raised.

    Raises:
    - ValueError: If the initial message exceeds a token limit after multiple attempts to reduce its size.
    - Exception: If the maximum number of retries is exceeded without generating a valid response.
    """
    #Create Client
    client = create_gpt_client()  

    logger.debug("This is the messages_dict_gpt submitted to GPT ChatCompletion")
    logger.debug(f"The number of tokens included at start is: {_count_tokens_in_messages(messages=messages_dict_gpt)}")
    logger.debug(messages_dict_gpt)

    #Error checking for token length, etc.
    counter=0
    try:
        while _count_tokens_in_messages(messages=messages_dict_gpt) > 2000:
            if counter > 10:
                error_message = f"Error: Too many tokens {token_count} even after 10 attempts to reduce count"
                logger.error(error_message)
                raise ValueError(error_message)
            logger.debug("Entered _count_tokens_in_messages() > ____")
            token_count = _count_tokens_in_messages(messages=messages_dict_gpt)
            logger.warning(f"The messages_dict_gpt contained too many tokens {(token_count)}, .pop(0) first dict")
            messages_dict_gpt.pop(0)
            counter+=1
    except Exception as e:
        logger.error(f"Exception ocurred in openai_gpt_chatcompletion() during _count_tokens_in_messages(): {e}")
    
    logger.debug(f"messages_dict_gpt submitted to GPT ChatCompletion (tokens: {_count_tokens_in_messages(messages=messages_dict_gpt)})")
    logger.debug(messages_dict_gpt)

    #Call to OpenAI #TODO: This loop is wonky.  Should probably divert to a 'while' statement
    for attempt in range(max_attempts):
        logger.debug(f"THIS IS ATTEMPT #{attempt + 1}")
        try:
            generated_response = client.chat.completions.create(
                model=model,
                messages=messages_dict_gpt,
                presence_penalty=presence_penalty,
                frequency_penalty=frequency_penalty,
                temperature=temperature
            )
        except Exception as e:
            logger.error(f"Exception occurred during API call: {e}: Attempt {attempt + 1} of {max_attempts} failed.")
            continue

        logger.debug(f"Completed generated response using client.chat.completions.create")          
        gpt_response_text = generated_response.choices[0].message.content
        gpt_response_text_len = len(gpt_response_text)
  
        logger.debug(f"generated_response type: {type(generated_response)}, length: {gpt_response_text_len}:")

        if gpt_response_text_len < max_characters:
            logger.debug(f'OK: The generated message was <{max_characters} characters')
            logger.debug(f"gpt_response_text: {gpt_response_text}")
            break

        else: # Did not get a msg < n chars, try again.
            logger.warning(f'gpt_response_text_len: >{max_characters} characters, retrying call to openai_gpt_chatcompletion')
            messages_dict_gpt_updated = [{'role':'user', 'content':f"{shorten_message_prompt}: '{gpt_response_text}'"}]
            generated_response = client.chat.completions.create(
                model=model,
                messages=messages_dict_gpt_updated,
                presence_penalty=presence_penalty,
                frequency_penalty=frequency_penalty,
                temperature=temperature
                )
            gpt_response_text = generated_response.choices[0].message.content
            gpt_response_text_len = len(gpt_response_text)

            if gpt_response_text_len > max_characters:
                logger.warning(f'gpt_response_text length was {gpt_response_text_len} characters (max: {max_characters}), trying again...')
            elif gpt_response_text_len < max_characters:
                logger.debug(f"OK on attempt --{attempt}-- gpt_response_text: {gpt_response_text}")
                break
    else:
        message = "Maxium GPT call retries exceeded"
        logger.error(message)        
        raise Exception(message)

    # Strip the prefix from the response
    gpt_response_text = _strip_prefix(gpt_response_text)
    
    return gpt_response_text

def prompt_text_replacement(
        gpt_prompt_text,
        replacements_dict=None
        ) -> str:
    if replacements_dict:
        prompt_text_replaced = gpt_prompt_text.format(**replacements_dict)   
    else:
        prompt_text_replaced = gpt_prompt_text

    logger.debug(f"prompt_text_replaced: {prompt_text_replaced}")
    return prompt_text_replaced

def combine_msghistory_and_prompttext(
        prompt_text,
        prompt_text_role='user',
        prompt_text_name='unknown',
        msg_history_list_dict=None,
        combine_messages=False,
        output_new_list=False
        ) -> list[dict]:
    """
    Merges a given prompt text with an existing message history.

    This function integrates a new prompt text into a provided message history list. It supports different roles for the prompt (e.g., user, assistant), and can either combine all user and assistant messages into a single message or keep them separate.

    Parameters:
    - prompt_text (str): The text of the new prompt to be merged.
    - prompt_text_role (str): The role associated with the prompt text ('user', 'assistant', or 'system'). Default is 'user'.
    - prompt_text_name (str): The name associated with the prompt text, used if role is 'user' or 'assistant'. Default is 'unknown'.
    - msg_history_list_dict (list[dict], optional): The existing list of message dictionaries to merge with. Default is None.
    - combine_messages (bool): If True, combines all user and assistant messages into a single message. Default is False.
    - output_new_list (bool): If True, outputs a new list instead of modifying the existing one. Default is False.

    Returns:
    - list[dict]: A list of dictionaries representing the merged message history and prompt.

    """
    
    if output_new_list == True:
        msg_history_list_dict_temp = copy.deepcopy(msg_history_list_dict)
    else:
        msg_history_list_dict_temp = msg_history_list_dict

    if prompt_text_role == 'system':
        prompt_dict = {'role': prompt_text_role, 'content': f'{prompt_text}'}
    elif prompt_text_role in ['user', 'assistant']:
        prompt_dict = {'role': prompt_text_role, 'content': f'<<<{prompt_text_name}>>>: {prompt_text}'}

    if combine_messages == True:
        msg_history_string = " ".join(item["content"] for item in msg_history_list_dict_temp if item['role'] != 'system')
        reformatted_msg_history_list_dict = [{
            'role': prompt_text_role, 
            'content': msg_history_string
        }]
        reformatted_msg_history_list_dict.append(prompt_dict)
        msg_history_list_dict_temp = reformatted_msg_history_list_dict
    else:
        msg_history_list_dict_temp.append(prompt_dict)

    logger.debug(f"This is the 2 most recent messages in msg_history_list_dict_temp:")
    logger.debug(msg_history_list_dict_temp[-2:])

    utils.write_json_to_file(
        data=msg_history_list_dict_temp, 
        variable_name_text='msg_history_list_dict_temp', 
        dirname='log/get_combine_msghistory_and_prompttext_combined', 
        include_datetime=False
    )
    return msg_history_list_dict_temp

def make_string_gptlistdict(
        prompt_text, 
        prompt_text_role='user'
        ) -> list[dict]:
    """
    Creates a list dictionary format from a single message string.

    This function is used to convert a single message string into a list containing a dictionary, formatted for use with GPT-like models. It is particularly useful for initializing conversation histories or adding new messages to an existing list.

    Parameters:
    - prompt_text (str): The text of the message to be converted.
    - prompt_text_role (str): The role associated with the message ('user' or 'assistant'). Default is 'user'.

    Returns:
    - list[dict]: A list containing a single dictionary with the message text and role.

    """    
    prompt_listdict = [{'role': prompt_text_role, 'content': f'{prompt_text}'}]
    return prompt_listdict

def _count_tokens(text:str, model="gpt-3.5-turbo") -> int:
    try:
        encoding = tiktoken.encoding_for_model(model_name=model)
        tokens_in_text = len(encoding.encode(text))
    except:
        raise ValueError("tiktoken.encoding_for_model() failed")

    return tokens_in_text

def _count_tokens_in_messages(messages: List[dict]) -> int:
    try:
        total_tokens = 0
        for message in messages:
            # Using .get() with default value as an empty string
            role = message.get('role', '')
            content = message.get('content', '')

            # Count tokens in role and content
            total_tokens += _count_tokens(role) + _count_tokens(content)
        logger.debug(f"Total Tokens: {total_tokens}")
        return total_tokens
    except:
        raise ValueError("_count_tokens_in_messages() failed")
    
# def get_models(api_key=None):
#     """
#     Function to fetch the available models from the OpenAI API.

#     Args:
#         api_key (str): The API key for the OpenAI API.

#     Returns:
#         dict: The JSON response from the API containing the available models.
#     """
#     url = 'https://api.openai.com/v1/models'

#     headers = {
#         'Authorization': f'Bearer {api_key}'
#     }

#     response = requests.get(url, headers=headers)

#     return response.json()

if __name__ == '__main__':
    
    ConfigManager.initialize(yaml_filepath=r'C:\Users\Admin\OneDrive\Desktop\_work\__repos (unpublished)\_____CONFIG\chatzilla_ai\config\config.yaml')
    config = ConfigManager.get_instance()
    OPENAI_API_KEY = config.openai_api_key

    # #test2 -- Get models
    # gpt_models = get_models(
    #     api_key=config.openai_api_key
    #     )
    # print("GPT Models:")
    # print(json.dumps(gpt_models, indent=4))

    # test3 -- call to chatgpt chatcompletion
    openai_gpt_chatcompletion(
        messages_dict_gpt=[
            {'role':'user', 'content':'Whats a tall buildings name?'}, 
            {'role':'user', 'content':'Whats a tall Statues name?'}
            ],
        max_characters=250,
        max_attempts=5,
        model=gpt_model,
        frequency_penalty=1,
        presence_penalty=1,
        temperature=0.7
        )