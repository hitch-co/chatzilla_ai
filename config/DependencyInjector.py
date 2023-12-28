# dependency_injector.py

from classes.MessageHandlerClass import MessageHandler
from classes.BQUploaderClass import TwitchChatBQUploader
from classes.GPTTextToSpeechClass import GPTTextToSpeech
from services.VibecheckService import VibeCheckService

import openai

from my_modules.config import run_config

class DependencyInjector:
    def __init__(self, config):
        self.config = config
        self.tts_data_folder = config['openai-api']['tts_data_folder']
        self.tts_file_name = config['openai-api']['tts_file_name']

        # Create instances of the dependencies
        self.create_dependencies()

    def create_gpt_client(self):
        return openai.OpenAI()

    def create_twitch_chat_uploader(self):
        return TwitchChatBQUploader()

    def create_tts_client(self):
        tts_client = GPTTextToSpeech(
            output_filename=self.tts_file_name,
            output_dirpath=self.tts_data_folder
            )
        return tts_client
    
    def create_message_handler(self):
        return MessageHandler()
    
    def create_vibecheck_service(self, message_handler):
        return VibeCheckService(
            yaml_config=self.config,
            message_handler=message_handler
            )

    def create_dependencies(self):
        self.gpt_client = self.create_gpt_client()
        self.twitch_chat_uploader = self.create_twitch_chat_uploader()
        self.tts_client = self.create_tts_client()

        self.message_handler = self.create_message_handler()

def main():
    yaml_data = run_config()

    dependencies = DependencyInjector(yaml_data)
    dependencies.create_dependencies()

    print(dependencies.create_gpt_client)
    print(dependencies.message_handler)
    print(dependencies.vibecheck_service)
    print(dependencies.twitch_chat_uploader)
    print(dependencies.tts_client)

if __name__ == '__main__':
    main()