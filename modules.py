# modules.py
from discord.ext import commands
import os
import yaml
import dotenv
import logging
import openai
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)

# call to chat gpt for completion TODO: Could add  limits here?
def openai_gpt_chatcompletion(messages_dict_gpt=None,OPENAI_API_KEY=None): 
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
    print("completion object is of type:",type(completion))
    print("Completion message:")
    print(completion.choices[0].message)

    #send the gpt response as discord bot message
    return gpt_response

#Load parameters from config.yaml
def load_yaml(yaml_filename='config.yaml', yaml_dirname=''):
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
    
    print(yaml_dirname)
    # use the argument instead of hardcoding the path
    yaml_filepath = os.path.join(os.getcwd(), yaml_dirname, yaml_filename)
    print(yaml_filepath)
    with open(yaml_filepath, 'r') as file:
        yaml_config = yaml.safe_load(file)
        logging.info('YAML contents loaded successfully.')
    return yaml_config


#Loads environment variables from config.env
def load_env(env_filename='config.env', env_dirname='config'):
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
