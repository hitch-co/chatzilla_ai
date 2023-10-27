import os
from my_modules.utils import get_datetime_formats
from my_modules.config import load_env, load_yaml
import json

from my_modules import my_logging
from my_modules.my_logging import log_dynamic_dict

from my_modules.utils import write_json_to_file, write_query_to_file

from classes.PromptHandlerClass import PromptHandler

class MessageHandler:
    def __init__(self):
        self.logger = my_logging.my_logger(dirname='log', 
                                           logger_name='logger_MessageHandler',
                                           debug_level='DEBUG',
                                           mode='w',
                                           stream_logs=True)
        self.logger.debug('MessageHandler initialized.')

        self.yaml_data = load_yaml(yaml_filename='config.yaml', yaml_dirname='config')
        load_env(env_filename='config.env', env_dirname='config')

        #Users in message history
        self.users_in_messages_list = []

        #Message History Lists
        self.ouat_temp_msg_history = []
        self.automsg_temp_msg_history = []
        self.chatforme_temp_msg_history = []
        self.nonbot_temp_msg_history = []

        #Bots Lists
        self.bots_automsg = self.yaml_data['twitch-bots']['automsg']
        self.bots_chatforme = self.yaml_data['twitch-bots']['chatforme']
        self.bots_ouat = self.yaml_data['twitch-bots']['onceuponatime']        
        
        #Known Bots
        self.known_bots = []
        for key in self.yaml_data['twitch-bots']:
            self.known_bots.extend(self.yaml_data['twitch-bots'][key])
        self.known_bots = list(set(self.known_bots))
        self.logger.debug("these are the self.known_bots")
        self.logger.debug(self.known_bots)
        
        
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

    def add_to_message_history(self, message_history: list[dict], 
                               message_metadata: dict) -> None:
        message_history.append(message_metadata)
        self.message_history = message_history

    def add_user_to_users_list(self, message_metadata: dict) -> None:
        self.users_in_messages_list.append(message_metadata['name'])
        self.users_in_messages_list = list(set(self.users_in_messages_list))

    def extract_name_from_message(self, message):
        message_rawdata = message.raw_data
        start_index = message_rawdata.find(":") + 1
        end_index = message_rawdata.find("!")
        if start_index == 0 or end_index == -1:
            return 'unknown_name - see message.raw_data for details'
        else:
            return message_rawdata[start_index:end_index]

    def add_to_appropriate_message_history(self, message):

        if message.author is not None:
            #Message Metadata
            message_metadata = self.get_message_metadata(message)            
            name = message_metadata['name']
            self.logger.info("Here is the message_data:")
            self.logger.debug(message_metadata)
            self.add_user_to_users_list(message_metadata)

            # Create GPT-ready message dict
            gpt_ready_msg_dict = PromptHandler.create_gpt_message_dict_from_metadata(self,
                                                                                     message_metadata=message_metadata)
            self.logger.debug("This is the gpt_ready_msg_dict")
            log_dynamic_dict(self.logger, gpt_ready_msg_dict)

            if name in self.bots_automsg or name in self.bots_chatforme:
                self.automsg_temp_msg_history.append(gpt_ready_msg_dict)
                self.chatforme_temp_msg_history.append(gpt_ready_msg_dict)

            if name in self.bots_ouat:    
                self.ouat_temp_msg_history.append(gpt_ready_msg_dict)

            if name not in self.known_bots:
                self.nonbot_temp_msg_history.append(gpt_ready_msg_dict)
                self.chatforme_temp_msg_history.append(gpt_ready_msg_dict)

        elif message.author is None:
            
            extracted_name = self.extract_name_from_message(message)
            message_metadata = {'name':extracted_name}
            gpt_ready_msg_dict = PromptHandler.create_gpt_message_dict_from_strings(self,
                                                                                    role='user',
                                                                                    name=extracted_name,
                                                                                    content=message.content)
            self.add_user_to_users_list(message_metadata)

            if extracted_name in self.bots_ouat:
                self.ouat_temp_msg_history.append(gpt_ready_msg_dict)
            if extracted_name in self.bots_automsg:
                self.automsg_temp_msg_history.append(gpt_ready_msg_dict)
            if extracted_name in self.bots_chatforme:
                self.chatforme_temp_msg_history.append(gpt_ready_msg_dict)
    
if __name__ == '__main__':
    print("loaded MessageHandlerClass.py")