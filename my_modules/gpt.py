from classes.ArticleGeneratorClass import ArticleGenerator
from classes.ConsoleColoursClass import bcolors, printc
from my_modules.my_logging import my_logger

import os
from my_modules.config import load_env, load_yaml
import random
import requests
import openai
import re
import json

#LOGGING
stream_logs=False

# call to chat gpt for completion TODO: Could add  limits here?
def openai_gpt_chatcompletion(messages_dict_gpt=None,
                              OPENAI_API_KEY=None, 
                              max_characters=500,
                              max_attempts=5,
                              model="gpt-3.5-turbo"): 
    """
    Send a message to OpenAI GPT-3.5-turbo for completion and get the response.

    Parameters:
    - messages_dict_gpt (dict): Dictionary containing the message structure for the GPT prompt.
    - OPENAI_API_KEY (str): API key to authenticate with OpenAI.

    Returns:
    str: The content of the message generated by GPT.
    """     
    openai.api_key = OPENAI_API_KEY

    #setup logger
    logger_gptchatcompletion = my_logger(dirname='log',
                                         logger_name='logger_openai_gpt_chatcompletion',
                                         mode='a',
                                         stream_logs=stream_logs)
    logger_gptchatcompletion.debug("This is the messages_dict_gpt submitted to GPT ChatCompletion")
    logger_gptchatcompletion.debug(messages_dict_gpt)

    for _ in range(max_attempts):
        generated_response = openai.ChatCompletion.create(
            model=model,
            messages=messages_dict_gpt
            )
        gpt_response_text = generated_response.choices[0].message['content']
        gpt_response_text_len = len(gpt_response_text)
        logger_gptchatcompletion.debug(f"\nThe generated_response object is of type {type(generated_response)}")
        logger_gptchatcompletion.debug(f'\nThe --{_}-- call to gpt_chat_completion had a response of {gpt_response_text_len} characters')
        logger_gptchatcompletion.debug(f"The generated_response object is of type {type(gpt_response_text)}")        
        
        if gpt_response_text_len < max_characters:
            logger_gptchatcompletion.info(f'\nOK: The generated message was <{max_characters} characters')
            break  

        else: # Did not get a msg < n chars, try again.
            logger_gptchatcompletion.warning(f'\The generated message was >{max_characters} characters, retrying call to openai_gpt_chatcompletion')
            
            messages_dict_gpt_updated = {'role':'user', 'content':f"Shorten this message to less than 400 characters: {gpt_response_text}"}
            generated_response = openai.ChatCompletion.create(
                model=model,
                messages=[messages_dict_gpt_updated]
                )
            gpt_response_text = generated_response.choices[0].message['content']
            gpt_response_text_len = len(gpt_response_text)

            if gpt_response_text_len > max_characters:
                logger_gptchatcompletion.warning(f'\nThe generated message was gpt_response_text_len characters (>{max_characters}) on the second try, retrying call to openai_gpt_chatcompletion')
            elif gpt_response_text_len < max_characters:
                logger_gptchatcompletion.info(f'\nOK on second try: The generated message was {gpt_response_text_len} characters')
                break
    else:
        message = "Maxium GPT call retries exceeded"
        logger_gptchatcompletion.error(message)        
        raise Exception(message)

    logger_gptchatcompletion.info(f'call to gpt_chat_completion ended with gpt_response_text of {gpt_response_text_len} characters')

    return gpt_response_text


def get_random_rss_article_summary_prompt(newsarticle_rss_feed = 'http://rss.cnn.com/rss/cnn_showbiz.rss',
                                          summary_prompt = 'none',
                                          OPENAI_API_KEY = None):
    
    #Grab a random article                
    article_generator = ArticleGenerator(rss_link=newsarticle_rss_feed)
    random_article_dictionary = article_generator.fetch_random_article()

    #NOTE: rss_article_content is confusing here...
    #replace ouat_news_article_summary_prompt placeholder params
    rss_article_content = random_article_dictionary['content']
    params = {"rss_article_content":rss_article_content}
    random_article_content_prompt = summary_prompt.format(**params)

    #Final prompt dict submitted to GPT
    gpt_prompt_dict = create_custom_gpt_message_dict(random_article_content_prompt,
                                                     role='system')
    random_article_content_prompt_summary = openai_gpt_chatcompletion(gpt_prompt_dict, 
                                                                      OPENAI_API_KEY=OPENAI_API_KEY, 
                                                                      max_characters=2000)
    
    return random_article_content_prompt_summary


#Generates a random prompt based on the list of standardized prompts
def rand_prompt(prompts_list=None):
    automsg_percent_chance_list = []
    automsg_prompt_topics = []
    automsg_prompts = []
    
    for key, value in prompts_list.items():
        automsg_prompt_topics.append(key)
        automsg_prompts.append(value[0])
        automsg_percent_chance_list.append(value[1])

    selected_prompt = random.choices(automsg_prompts, weights=automsg_percent_chance_list, k=1)[0]
    return selected_prompt


def prompt_text_replacement(gpt_prompt_text,
                            replacements_dict):
    prompt_text_replaced = gpt_prompt_text.format(**replacements_dict)   
    return prompt_text_replaced


def create_custom_gpt_message_dict(prompt_text,
                                   role='user',
                                   name='unknown'):
    
    if role == 'system':
        gpt_ready_msg_dict = {'role': role, 'content': f'{prompt_text}'}
    if role in ['user','assistant']:
        gpt_ready_msg_dict = {'role': role, 'content': f'<<<{name}>>>: {prompt_text}'}

    return gpt_ready_msg_dict


def create_gpt_message_dict_from_twitchmessage(message_metadata, 
                                               role='user'):
    """
    Create a dictionary suitable for GPT chat completion.
    
    Args:
    - message_metadata (dict): The original metadata dictionary.
    - role (str, optional): The role (default is 'user').
    
    Returns:
    - dict: A filtered and formatted dictionary.
    """    
    logger_create_gpt_message_dict_from_twitchmsg = my_logger(
        dirname='log', 
        logger_name='logger_create_gpt_message_dict_from_twitchmsg',
        debug_level='DEBUG',
        mode='a',
        stream_logs=stream_logs)

    gpt_ready_msg_dict = {}
    gpt_ready_msg_dict['role'] = role
    gpt_ready_msg_dict['content'] = message_metadata['content']

    logger_create_gpt_message_dict_from_twitchmsg.debug('\nmessage_metadata details:')
    logger_create_gpt_message_dict_from_twitchmsg.debug(message_metadata)
    logger_create_gpt_message_dict_from_twitchmsg.debug('\ncreate_gpt_message_dict_from_twitchmessage details:')
    logger_create_gpt_message_dict_from_twitchmsg.debug(gpt_ready_msg_dict)
    
    return gpt_ready_msg_dict


def combine_msghistory_and_prompttext(prompt_text,
                                      role='user',
                                      name='unknown',
                                      msg_history_list_dict=None,
                                      combine_messages=False) -> [dict]:
    
    #setup logger
    logger_msghistory_and_prompt = my_logger(
        dirname='log',
        logger_name='logger_msghistory_and_prompt',
        debug_level='DEBUG',
        mode='a',
        stream_logs=stream_logs
        )

    #deal with prompt text
    if role == 'system':
        prompt_dict = {'role': role, 'content': f'{prompt_text}'}
    if role in ['user', 'assistant']:
        prompt_dict = {'role': role, 'content': f'<<<{name}>>>: {prompt_text}'}

    if not msg_history_list_dict:
        msg_history_list_dict = [prompt_dict]

    # Check if msg_history_list_dict is the correct data type
    if (msg_history_list_dict is not None and not isinstance(msg_history_list_dict, list)) or \
    (msg_history_list_dict and not all(isinstance(item, dict) for item in msg_history_list_dict)):
        logger_msghistory_and_prompt.debug("msg_history_list_dict is not a list of dictionaries or None")
        raise ValueError("msg_history_list_dict should be a list of dictionaries or None")
    
    else:
        if combine_messages == True:
            msg_history_list_dict = [{
                'role':role, 
                'content':" ".join(item["content"] for item in msg_history_list_dict if item['role'] != 'system')
            }]            
            msg_history_list_dict.append(prompt_dict)
            return msg_history_list_dict
        else:
            msg_history_list_dict.append(prompt_dict) 
            return msg_history_list_dict


def get_models(api_key=None):
    """
    Function to fetch the available models from the OpenAI API.

    Args:
        api_key (str): The API key for the OpenAI API.

    Returns:
        dict: The JSON response from the API containing the available models.
    """
    url = 'https://api.openai.com/v1/models'

    headers = {
        'Authorization': f'Bearer {api_key}'
    }

    response = requests.get(url, headers=headers)

    return response.json()


if __name__ == '__main__':
    yaml_data = load_yaml(yaml_dirname='config')
    load_env(env_dirname='config')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

    #test2 -- Get models
    gpt_models = get_models(OPENAI_API_KEY)
    print("GPT Models:")
    print(json.dumps(gpt_models, indent=4))

    # #test1 -- get_random_rss_article_summary_prompt
    # summary_prompt = yaml_data['ouat_news_article_summary_prompt']
    
    # summary_prompt_response = get_random_rss_article_summary_prompt(
    #     newsarticle_rss_feed='http://rss.cnn.com/rss/cnn_showbiz.rss',
    #     summary_prompt=summary_prompt,
    #     OPENAI_API_KEY=OPENAI_API_KEY
    #     )
    # print("summary_prompt_response:")
    # print(summary_prompt_response)




