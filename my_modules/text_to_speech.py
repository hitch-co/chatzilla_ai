import requests
import os
import json

from my_modules.config import load_env, load_yaml

#config yaml
yaml_data = load_yaml(yaml_dirname='config', yaml_filename='config.yaml')

#config env
load_env(env_filename=yaml_data['env_filename'], env_dirname=yaml_data['env_dirname'])
ELEVENLABS_XI_API_KEY = os.getenv('ELEVENLABS_XI_API_KEY')
ELEVENLABS_XI_VOICE_PERSONAL= os.getenv('ELEVENLABS_XI_VOICE_PERSONAL')
ELEVENLABS_XI_VOICE_BUSINESS=''


#####################################################
def generate_t2s_object(ELEVENLABS_XI_API_KEY = None,
                       voice_id = None,
                       text_to_say='this is default text', 
                       is_testing = False):
    """
    Generate a Text-to-Speech audio object using the ElevenLabs API.

    Parameters:
    - ELEVENLABS_XI_API_KEY (str): API key to authenticate with ElevenLabs.
    - voice_id (str): ID of the voice to use for the audio generation.
    - text_to_say (str): The text content to be converted to audio.
    - is_testing (bool): Flag to indicate if the function is being run for testing purposes.

    Returns:
    obj: Audio object of the generated speech.
    """    
    from elevenlabs import set_api_key, generate

    #Testing    
    is_testing = False
    if is_testing == True:
        text_to_say = ''
        voice_id = 'vXUfHpda4drIfuTOY6lg'
        

    #some sample endpoints
    url_base = 'https://api.elevenlabs.io/'
    url_history = 'v1/history'
    url_get_voices = 'v1/voices'

    #API Key for get headers
    headers={'xi-api-key':ELEVENLABS_XI_API_KEY}
    set_api_key(ELEVENLABS_XI_API_KEY)

    audio = generate(text=text_to_say,
                    voice = voice_id)

    return(audio)


####################
def get_voice_ids():
    """
    Fetch available voice IDs from ElevenLabs API.

    Returns:
    str: Formatted JSON string containing the voice IDs.
    """
    
    #some sample endpoints
    url_base = 'https://api.elevenlabs.io/'
    url_history = 'v1/history'
    url_get_voices = 'v1/voices'

    #API Key for get headers
    headers={'xi-api-key':ELEVENLABS_XI_API_KEY}

    #get voice IDs response for 
    response = requests.get(url_base+url_get_voices, headers=headers)

    # Print the content of the response in readable JSON format
    try:
        json_response = json.loads(response.content)
        formatted_json = json.dumps(json_response, indent=4)
        print('Response Content (Formatted JSON):\n', formatted_json)
    except json.JSONDecodeError as e:
        print('Error decoding JSON:', e)

    return formatted_json
    #EoF


########################
def get_voice_history():
    """
    Fetch voice generation history from ElevenLabs API.

    Returns:
    str: Formatted JSON string containing the voice history.
    """    
    #some sample endpoints
    url_base = 'https://api.elevenlabs.io/'
    url_history = 'v1/history'

    #API Key for get headers
    headers={'xi-api-key':ELEVENLABS_XI_API_KEY}

    #get voice IDs response for 
    response = requests.get(url_base+url_history, headers=headers)

    # Print the content of the response in readable JSON format
    try:
        json_response = json.loads(response.content)
        formatted_json = json.dumps(json_response, indent=4)
        print('Response Content (Formatted JSON):\n', formatted_json)
    except json.JSONDecodeError as e:
        print('Error decoding JSON:', e)

    return formatted_json
    #EoF