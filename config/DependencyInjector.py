# dependency_injector.py
from google.cloud import bigquery
import openai

from classes.MessageHandlerClass import MessageHandler
from classes.BQUploaderClass import BQUploader
from services.GPTTextToSpeechService import GPTTextToSpeech
from classes.GPTAssistantManagerClass import GPTBaseClass, GPTThreadManager, GPTResponseManager, GPTAssistantManager
from classes.GPTAssistantManagerClass import GPTFunctionCallManager
from services.DeepSeekService import AsyncDeepSeekAIClient

from classes.TaskManagerClass import TaskManager
from classes.TaskHandlerClass import TaskHandler


class DependencyInjector:
    def __init__(self, config):
        self.config = config
        self.create_dependencies()

    def create_gpt_client(self):
        gpt_client = openai.OpenAI(
            api_key=self.config.openai_api_key
            )
        return gpt_client

    def create_bq_client(self):
        bq_client = bigquery.Client()
        return bq_client
    
    def create_bq_uploader(self, bq_client):
        return BQUploader(bq_client)

    def create_tts_client(self,):
        tts_client = GPTTextToSpeech(
            openai_client=self.gpt_client
            )
        return tts_client

    def create_task_manager(self):
        task_manager = TaskManager()
        return task_manager
    
    def create_gpt_thread_mgr(self):
        gpt_thread_mgr = GPTThreadManager(
            gpt_client=self.gpt_client
        )
        return gpt_thread_mgr

    def create_gpt_assistant_mgr(self):
        gpt_assistant_mgr = GPTAssistantManager(
            gpt_client=self.gpt_client
        )
        return gpt_assistant_mgr    
    
    def create_gpt_response_mgr(self, gpt_thread_manager, gpt_assistant_manager):
        gpt_response_mgr = GPTResponseManager(
            gpt_client=self.gpt_client,
            gpt_thread_manager=gpt_thread_manager,
            gpt_assistant_manager=gpt_assistant_manager,
            max_waittime_for_gpt_response=self.config.magic_max_waittime_for_gpt_response
        )
        return gpt_response_mgr
    
    def create_gpt_function_call_mgr(self, gpt_thread_manager, gpt_response_manager, gpt_assistant_manager):
        gpt_function_call_mgr = GPTFunctionCallManager(
            gpt_client=self.gpt_client,
            gpt_thread_manager=gpt_thread_manager,
            gpt_response_manager=gpt_response_manager,
            gpt_assistant_manager=gpt_assistant_manager
        )
        return gpt_function_call_mgr

    def create_message_handler(self, task_manager):
        message_handler = MessageHandler(
            task_manager=task_manager,
            msg_history_limit=self.config.msg_history_limit
        )
        return message_handler
    
    def create_deepseek_client(self):
        deepseek_client = AsyncDeepSeekAIClient()
        return deepseek_client
        
    def create_task_handler(self, config, task_manager, gpt_response_manager, deepseek_client, tts_client, message_handler):
        task_handler = TaskHandler(
            config = config,
            task_manager = task_manager,
            gpt_response_manager = gpt_response_manager,
            deepseek_client = deepseek_client,
            tts_client = tts_client,
            message_handler = message_handler
        )
        return task_handler

    
    def create_dependencies(self):
        self.bq_client = self.create_bq_client()
        self.bq_uploader = self.create_bq_uploader(bq_client=self.bq_client)

        # TTS may be same as GPT client
        self.gpt_client = self.create_gpt_client()
        self.tts_client = self.create_tts_client()

        self.gpt_thread_mgr = self.create_gpt_thread_mgr()
        self.gpt_assistant_mgr = self.create_gpt_assistant_mgr()
        self.gpt_response_mgr = self.create_gpt_response_mgr(gpt_thread_manager=self.gpt_thread_mgr, gpt_assistant_manager = self.gpt_assistant_mgr)
        self.gpt_function_call_mgr = self.create_gpt_function_call_mgr(gpt_thread_manager=self.gpt_thread_mgr, gpt_response_manager=self.gpt_response_mgr, gpt_assistant_manager=self.gpt_assistant_mgr)
        
        self.deepseek_client = self.create_deepseek_client()

        self.task_manager = self.create_task_manager()
        self.message_handler = self.create_message_handler(task_manager=self.task_manager)

        self.task_handler = self.create_task_handler(
            config = self.config,
            task_manager = self.task_manager,
            gpt_response_manager = self.gpt_response_mgr,
            deepseek_client = self.deepseek_client,
            tts_client = self.tts_client,
            message_handler = self.message_handler
        )

def main(yaml_filepath):
    from classes.ConfigManagerClass import ConfigManager
    
    ConfigManager.initialize(yaml_filepath)
    config = ConfigManager.get_instance()
    config.aboutme_prompt
    dependencies = DependencyInjector(config=config)
    dependencies.create_dependencies()

    return dependencies

if __name__ == '__main__':
    import os
    import dotenv

    dotenv_load_result = dotenv.load_dotenv(dotenv_path='./config/.env')
    yaml_filepath=os.getenv('CHATZILLA_CONFIG_YAML_FILEPATH')
    dependencies = main(yaml_filepath)

    print(dependencies.gpt_client)
    print(dependencies.message_handler)
    print(dependencies.bq_uploader)
    print(dependencies.tts_client)
    print(dependencies.gpt_thread_mgr)
    print(dependencies.gpt_response_mgr)
    print(dependencies.gpt_assistant_mgr)