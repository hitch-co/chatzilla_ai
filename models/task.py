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
        return {
            "thread_name": self.thread_name
            }

class AddMessageTask(BaseTask):
    def __init__(
            self, thread_name: str, 
            content: str, 
            message_role: str = 'user'
            ):
        super().__init__(thread_name)
        self.content = content
        self.message_role = message_role

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
            send_channel_message=True,
            message_role: str = 'assistant'
            ):
        super().__init__(thread_name)
        self.assistant_name = assistant_name
        self.thread_instructions = thread_instructions
        self.replacements_dict = replacements_dict
        self.tts_voice = tts_voice
        self.send_channel_message = send_channel_message
        self.message_role = message_role

    def to_dict(self) -> dict:
        task_dict = super().to_dict()
        task_dict.update({
            "type": "execute_thread",
            "assistant_name": self.assistant_name,
            "thread_instructions": self.thread_instructions,
            "replacements_dict": self.replacements_dict,
            "tts_voice": self.tts_voice,
            "send_channel_message": self.send_channel_message,
            "message_role": self.message_role
        })
        self.logger.info(f"CreateExecuteThreadTask Dict created: {task_dict}")
        return task_dict