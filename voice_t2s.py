import os
import argparse 

from elevenlabs import play

from my_modules.config import load_env, load_yaml 
from my_modules.gpt import openai_gpt_chatcompletion
from my_modules.text_to_speech import generate_t2s_object
from my_modules.utils import get_user_input

# Create an argument parser
parser = argparse.ArgumentParser(description="Process some gpt prompt text for text-to-speech.")
parser.add_argument("--text", type=str, help="The gpt prompt text to be processed for text-to-speech.")
args = parser.parse_args()

# Load yaml & environment
yaml_data = load_yaml(yaml_dirname='config', yaml_filename='config.yaml')
env_dirname=yaml_data['env_dirname']
env_filename=yaml_data['env_filename']

load_env(env_filename=env_filename, env_dirname=env_dirname)
ELEVENLABS_XI_API_KEY = os.getenv('ELEVENLABS_XI_API_KEY')
ELEVENLABS_XI_VOICE_ID = os.getenv('ELEVENLABS_XI_VOICE_PERSONAL')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def main():
    # Get user input
    gpt_prompt_text = get_user_input(predefined_text=args.text)
    
    # Generate gpt prompt in correct array({}) format
    gpt_prompt = [
        {'role': 'user', 'name': 'eric', 'content': 'hello'}, 
        {'role': 'system', 'content': gpt_prompt_text}
    ]

    # Generate the gpt prompt response
    generated_message = openai_gpt_chatcompletion(messages_dict_gpt=gpt_prompt,OPENAI_API_KEY=OPENAI_API_KEY)

    # Generate a t2s object
    voice_message_object = generate_t2s_object(
        ELEVENLABS_XI_API_KEY=ELEVENLABS_XI_API_KEY,
        voice_id=ELEVENLABS_XI_VOICE_ID,
        text_to_say=generated_message, 
        is_testing=False)

    # Play the voice
    play(voice_message_object)

if __name__ == "__main__":
    main()