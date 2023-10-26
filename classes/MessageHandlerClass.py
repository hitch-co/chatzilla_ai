import os

from my_modules.utils import get_datetime_formats
from my_modules.config import load_env, load_yaml
import json
from my_modules import my_logging
from my_modules.utils import write_json_to_file, write_query_to_file
from my_modules.my_logging import my_logger



class MessageHandler:
    def __init__(self):
        
        load_env()
        
        self.logger = my_logging.my_logger(dirname='log', 
                                           logger_name='logger_MessageHandler',
                                           debug_level='DEBUG',
                                           mode='w',
                                           stream_logs=True)
        self.logger.debug('MessageHandler initialized.')

        self.stream_logs = True

    def get_message_metadata(self, message) -> None:
        # Collect all metadata
        message_metadata = {
            'badges': message.author.badges,
            'name': message.author.name,
            'user_id': message.author.id,
            'display_name': message.author.display_name,
            'channel': message.channel.name,
            'timestamp': message.timestamp,
            'tags': message.tags,
            'content': f'<<<{message.author.name}>>>: {message.content}',
        }
        return message_metadata

    def add_to_message_history(self, 
                               message_history: list[dict], 
                               message_metadata: dict) -> None:
        message_history.append(message_metadata)
        self.message_history = message_history

    def add_user_to_messages_list(self, 
                                  users_in_messages_list, 
                                  message_metadata) -> None:
        users_in_messages_list.append(message_metadata['name'])
        users_in_messages_list = list(set(users_in_messages_list))
        return users_in_messages_list

    def create_gpt_message_dict_from_twitchmessage(self, 
                                                   message_metadata, 
                                                   role='user'):
        """
        Create a dictionary suitable for GPT chat completion.
        
        Args:
        - message_metadata (dict): The original metadata dictionary.
        - role (str, optional): The role (default is 'user').
        
        Returns:
        - dict: A filtered and formatted dictionary.
        """    

        gpt_ready_msg_dict = {}
        gpt_ready_msg_dict['role'] = role
        gpt_ready_msg_dict['content'] = message_metadata['content']

        self.logger.debug('message_metadata details:')
        self.logger.debug(message_metadata)
        self.logger.debug('create_gpt_message_dict_from_twitchmessage details:')
        self.logger.debug(gpt_ready_msg_dict)
        
        return gpt_ready_msg_dict
    
    def message_history_creation_workflow():
        print('rename this')
    
if __name__ == '__main__':
    message_handler = MessageHandler()