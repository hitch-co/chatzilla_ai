# modules.py
from discord.ext import commands
import os
import yaml
import dotenv
import logging
import openai
import requests
import json
import random

# Set up logging
logging.basicConfig(level=logging.INFO)

# call to chat gpt for completion TODO: Could add  limits here?
def openai_gpt_chatcompletion(messages_dict_gpt=None,OPENAI_API_KEY=None): 

    import openai

    #attach openai api key
    openai.api_key = OPENAI_API_KEY

    #request to openai
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        #model="gpt-4-turbo",
        messages=messages_dict_gpt
    )
    
    #review what's been provided by GPT
    gpt_response = completion.choices[0].message['content']
    print('---------- Prompt Message Dictionary')
    print(messages_dict_gpt)
    print("----------  GPT Response:")
    print(completion.choices[0].message)

    #send the gpt response as discord bot message
    return gpt_response


#Generates a random prompt based on the list of standardized prompts
#NOTE: should this be done here or in the __init__?
def rand_prompt(chatgpt_automated_msg_prompts_list=None):

    import random
    import json

    #################
    #Feature % chance
    automsg_percent_chance_list = []
    automsg_prompt_topics = []
    automsg_prompts = []

    chatgpt_automated_msg_prompts_selected = chatgpt_automated_msg_prompts_list
    print(json.dumps(obj=chatgpt_automated_msg_prompts_selected, indent=4))

    #For each key in yaml_data['chatgpt_automated_msg_prompts']['standard'], 
    # add relevant data to list for applying a random % chance to each prompt
    for key, value in chatgpt_automated_msg_prompts_selected.items():
        automsg_prompt_topics.append(key)
        print(key)
        automsg_prompts.append(value[0])
        automsg_percent_chance_list.append(value[1])

    print(json.dumps(obj=automsg_prompt_topics, indent=4))
    print(json.dumps(obj=automsg_prompts, indent=4))
    print(json.dumps(obj=automsg_percent_chance_list, indent=4))

    # APply a random()+chance function to determine which prompt to input
    weighted_prompt_choice_Final = random.choices(automsg_prompts, weights=automsg_percent_chance_list, k=1)[0]
    print(weighted_prompt_choice_Final)

    return weighted_prompt_choice_Final


#Load parameters from config.yaml
def load_yaml(yaml_filename='config.yaml', yaml_dirname='', is_testing=False):
    import yaml
    import os
    """Load parameters from a yaml file.

    Args:
    yaml_filename (str): Path to the yaml file.

    Returns:
    dict: Dictionary containing parameters loaded from yaml file.
    
    Test:
    yaml_filename = 'config.yaml'
    yaml_dirname ='c:\\Users\\erich\\OneDrive\\Desktop\\_work\\__repos\\discord-chatforme\\config'
    """

    #is_testing = True
    if is_testing == True:
        yaml_dirname='C:\_repos\chatforme_bots\config'
        yaml_filename='config.yaml'

    print(yaml_dirname)
    # use the argument instead of hardcoding the path
    yaml_filepath = os.path.join(os.getcwd(), yaml_dirname, yaml_filename)
    print(yaml_filepath)
    with open(yaml_filepath, 'r') as file:
        yaml_config = yaml.safe_load(file)
        logging.info('YAML contents loaded successfully.')
    return yaml_config


#Loads environment variables from config.env
def load_env(env_filename='config.env', env_dirname='config', is_testing=False):
    import dotenv
    """Load environment variables from a .env file.

    Args:
    env_filename (str): name of the .env file.
    env_filedir (str): path of the directory the .env file is in
    yaml_filename = 'config.yaml'
    yaml_dirname ='c:\\Users\\erich\\OneDrive\\Desktop\\_work\\__repos\\discord-chatforme\\config'
    
    Test:
    env_filename='config.env'
    env_dirname='c:\\Users\\erich\\OneDrive\\Desktop\\_work\\__repos\\discord-chatforme\\config'
    """
    
    #is_testing = True
    if is_testing ==True:
        env_filename='config.env' 
        env_dirname='C:\_repos\chatforme_bots\config'

    env_filepath = os.path.join(os.getcwd(), env_dirname, env_filename)
    print(env_filepath)
    if dotenv.load_dotenv(env_filepath):
        logging.info('Environment file loaded successfully.')
    else:
        logging.error('Failed to load environment file.')


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
