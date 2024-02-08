# dependency_injector.py

from classes.MessageHandlerClass import MessageHandler
from classes.BQUploaderClass import BQUploader
from classes.GPTTextToSpeechClass import GPTTextToSpeech
from services.VibecheckService import VibeCheckService

import openai

class DependencyInjector:
    def __init__(self, config):
        self.config = config
        self.create_dependencies()

    def create_gpt_client(self):
        gpt_client = openai.OpenAI(
            api_key=self.config.openai_api_key
            )
        return gpt_client

    def create_bq_uploader(self):
        return BQUploader()

    def create_tts_client(self, openai_client):
        tts_client = GPTTextToSpeech(
            openai_client=openai_client,
            config=self.config
            )
        return tts_client
    
    def create_message_handler(self):
        message_handler = MessageHandler(
            config=self.config
        )
        return message_handler

    def create_dependencies(self):
        self.gpt_client = self.create_gpt_client()
        self.bq_uploader = self.create_bq_uploader()
        self.tts_client = self.create_tts_client(openai_client=self.gpt_client)
        self.message_handler = self.create_message_handler()

def main(yaml_filepath):
    from classes.ConfigManagerClass import ConfigManager
    
    ConfigManager.initialize(yaml_filepath)
    config = ConfigManager.get_instance()

    dependencies = DependencyInjector(config=config)
    dependencies.create_dependencies()

    return dependencies

if __name__ == '__main__':
    yaml_filepath = r'C:\Users\Admin\OneDrive\Desktop\_work\__repos (unpublished)\_____CONFIG\chatzilla_ai\config\config.yaml'
    dependencies = main(yaml_filepath)
    print(dependencies.gpt_client)
    print(dependencies.message_handler)
    print(dependencies.bq_uploader)
    print(dependencies.tts_client)