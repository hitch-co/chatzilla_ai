import os
import json
from my_modules import my_logging

from my_modules.config import load_env, load_yaml

class PromptHandler:
    def __init__(self):
        self.yaml_data = load_yaml(yaml_filename='config.yaml', yaml_dirname='config')
        load_env(env_filename='config.env', env_dirname='config')

        self.logger = my_logging.create_logger(
            dirname='log', 
            logger_name='logger_PromptHandler',
            debug_level='DEBUG',
            mode='w',
            stream_logs=False
            )

        #Users in message history
        self.users_in_messages_list = []

    def create_gpt_message_dict_from_metadata(self, 
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
        self.logger.debug('create_gpt_message_dict_from_metadata details:')
        self.logger.debug(gpt_ready_msg_dict)
        
        return gpt_ready_msg_dict

    def create_gpt_message_dict_from_strings(self,
                                             content,
                                             role='user',
                                             name='unknown'):
        if role == 'system':
            gpt_ready_msg_dict = {'role': role, 'content': f'{content}'}
        if role in ['user','assistant']:
            gpt_ready_msg_dict = {'role': role, 'content': f'<<<{name}>>>: {content}'}

        return gpt_ready_msg_dict

if __name__ == '__main__':
    print("loaded PromptHandlerClass.py")