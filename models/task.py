import asyncio
from my_modules.my_logging import create_logger

runtime_logger_level = 'INFO'
class BaseTask:
    def __init__(self, thread_name: str):
        self.thread_name = thread_name
        self.future = asyncio.Future()

        self.logger = create_logger(
            dirname='log', 
            logger_name='TaskLogger', 
            debug_level=runtime_logger_level,
            mode='w',
            stream_logs=True,
            encoding='UTF-8'
            )

    def to_dict(self):
        # Ensure the thread_name is always included in the dictionary
        return {
            "thread_name": self.thread_name
        }

class AddMessageTask(BaseTask):
    def __init__(
            self, 
            thread_name: str, 
            content: str, 
            message_role: str = 'user'
            ):
        super().__init__(thread_name)
        self.content = content
        self.message_role = message_role

        # Create task_dict during initialization
        self.task_dict = self.to_dict()

    def to_dict(self) -> dict:
        task_dict = super().to_dict()
        task_dict.update({
            "type": "add_message",
            "content": self.content,
            "message_role": self.message_role
        })
        self.logger.debug(f"AddMessageTask Dict created: {task_dict}")
        return task_dict

class CreateExecuteThreadTask(BaseTask):
    def __init__(
            self, 
            thread_name: str,
            assistant_name: str,
            thread_instructions: str,
            replacements_dict: dict,
            tts_voice: str,
            send_channel_message: bool = True,
            message_role: str = 'assistant',
            model_vendor_config: dict = {"vendor": "openai", "model": "n/a"}
            ):
        super().__init__(thread_name)
        self.assistant_name = assistant_name
        self.thread_instructions = thread_instructions
        self.replacements_dict = replacements_dict
        self.tts_voice = tts_voice
        self.send_channel_message = send_channel_message
        self.message_role = message_role
        self.model_vendor_config = model_vendor_config

        # Create task_dict during initialization
        self.task_dict = self.to_dict()

    def to_dict(self) -> dict:
        task_dict = super().to_dict()
        task_dict.update({
            "type": "execute_thread",
            "assistant_name": self.assistant_name,
            "thread_instructions": self.thread_instructions,
            "replacements_dict": self.replacements_dict,
            "tts_voice": self.tts_voice,
            "send_channel_message": self.send_channel_message,
            "message_role": self.message_role,
            "model_vendor_config": self.model_vendor_config
        })
        self.logger.debug(f"CreateExecuteThreadTask Dict created: {task_dict}")
        return task_dict
    
class CreateSendChannelMessageTask(BaseTask): 
    def __init__(
            self, 
            thread_name: str,
            content: str, 
            tts_voice: str, 
            message_role: str = 'assistant'
            ):
        super().__init__(thread_name)
        self.content = content
        self.tts_voice = tts_voice
        self.message_role = message_role

        # Create task_dict during initialization
        self.task_dict = self.to_dict()

    def to_dict(self) -> dict:
        task_dict = super().to_dict()  
        task_dict.update({
            "type": "send_channel_message",
            "thread_name": self.thread_name,
            "content": self.content,
            "tts_voice": self.tts_voice,
            "message_role": self.message_role
        })
        self.logger.debug(f"CreateSendChannelMessageTask Dict created: {task_dict}")
        return task_dict