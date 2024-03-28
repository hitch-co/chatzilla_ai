# dependency_injector.py

from classes.MessageHandlerClass import MessageHandler
from classes.BQUploaderClass import BQUploader
from classes.GPTTextToSpeechClass import GPTTextToSpeech
from classes.GPTAssistantManagerClass import GPTBaseClass, GPTThreadManager

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

    # # NiU: Optoinal instaed of creating client inside of BQUploader()
    # def create_bq_client(self)
    #     bq_client = bigquery.Client()
    #     return bq_client
    
    def create_bq_uploader(self):
        return BQUploader()

    def create_tts_client(self,):
        tts_client = GPTTextToSpeech(
            openai_client=self.gpt_client
            )
        return tts_client

    def create_gpt_thread_manager(self):
        gpt_thread_manager = GPTThreadManager(
            gpt_client=self.gpt_client
        )
        return gpt_thread_manager
      
    def create_message_handler(self, gpt_thread_manager):
        message_handler = MessageHandler(
            gpt_thread_mgr=gpt_thread_manager,
            msg_history_limit=self.config.msg_history_limit
        )
        return message_handler
    
    def create_dependencies(self):
        self.gpt_client = self.create_gpt_client()
        self.bq_uploader = self.create_bq_uploader()
        self.tts_client = self.create_tts_client()
        self.gpt_thread_manager = self.create_gpt_thread_manager()
        self.message_handler = self.create_message_handler(gpt_thread_manager=self.gpt_thread_manager)

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