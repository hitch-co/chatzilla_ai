
from my_modules.config import load_env, load_yaml
from my_modules import my_logging
from my_modules.my_logging import log_dynamic_dict
from classes.PromptHandlerClass import PromptHandler

class MessageHandler:
    def __init__(self):
        self.logger = my_logging.create_logger(
            dirname='log', 
            logger_name='logger_MessageHandler',
            debug_level='INFO',
            mode='w',
            stream_logs=True
            )
        self.logger.debug('MessageHandler initialized.')

        #run config
        self.yaml_data = load_yaml(yaml_filename='config.yaml', yaml_dirname='config')
        load_env(env_filename='config.env', env_dirname='config')

        #Bots Lists
        self.bots_automsg = self.yaml_data['twitch-bots']['automsg']
        self.bots_chatforme = self.yaml_data['twitch-bots']['chatforme']
        self.bots_ouat = self.yaml_data['twitch-bots']['onceuponatime']        
        
        #Known Bots
        self.known_bots = []
        for key in self.yaml_data['twitch-bots']:
            self.known_bots.extend(self.yaml_data['twitch-bots'][key])
        self.known_bots = list(set(self.known_bots))
        self.logger.info("these are the self.known_bots")
        self.logger.info(self.known_bots)

        #Users in message history
        self.users_in_messages_list = []

        #message_history_raw
        self.message_history_raw = []

        #Message History Lists
        self.ouat_temp_msg_history = []
        self.automsg_temp_msg_history = []
        self.chatforme_temp_msg_history = []
        self.nonbot_temp_msg_history = []

    def get_bot_message_metadata(self, message) -> None:
        message_metadata = {
            'badges': 'unknown', #message.tags.get('badges', 'NULL'),
            'name': self.extract_name_from_message(message=message), #message.author.get('name', 'NULL'),
            'user_id': self.extract_name_from_message(message=message), #message.author.get('id', 'NULL'),
            'display_name': 'unknown', #message.author.get('display_name', 'NULL'),
            'channel': 'unknown', #message.channel.get('name', 'NULL'),
            'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S'), #conv_datetime_formats(message.timestamp),
            'tags': {'color':'unkonwn'}, #message.get('tags', 'NULL'),
            'content': message.content #f'<<<{message.author.get("name", "Unknown Author")}>>>: {message.get("content","No Content")}',
        }
        return message_metadata

    def get_message_metadata(self, message) -> None:
        # Collect all metadata
        message_metadata = {
            'badges': message.tags.get('badges', ''),
            'name': message.author.name,
            'user_id': message.author.id,
            'display_name': message.author.display_name,
            'channel': message.channel.name,
            'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S'), #conv_datetime_formats(message.timestamp),
            'tags': message.tags,
            'content': f'<<<{message.author.name}>>>: {message.content}',
        }
        return message_metadata

    def add_user_to_users_list(self, message_metadata: dict) -> None:
        self.users_in_messages_list.append(message_metadata['name'])
        self.users_in_messages_list = list(set(self.users_in_messages_list))

    def extract_name_from_message(self, message):
        message_rawdata = message.raw_data

        start_index = message_rawdata.find(":") + 1
        end_index = message_rawdata.find("!")

        if start_index == 0 or end_index == -1:
            self.logger.debug(f"No extracted_name found.  This is message.raw_data:")
            self.logger.debug(message.raw_data)
            return 'unknown_name - see message.raw_data for details'
        else:
            extracted_name = message_rawdata[start_index:end_index]
            self.logger.debug(f"This is the extracted_name: {extracted_name} and message.raw_data:")
            self.logger.debug(message.raw_data)
            return extracted_name

    def add_to_appropriate_message_history(self, message):
        self.logger.info(f"Message content: {message.content}")

        if message.author is not None:
            message_metadata = self.get_message_metadata(message)            
            name = message_metadata['name']
            self.add_user_to_users_list(message_metadata)

            # Add to message_history_raw
            self.logger.debug("Here is the USER message_data:")
            self.logger.debug(message_metadata)
            self.message_history_raw.append(message_metadata)

            # Create GPT-ready message dict
            gpt_ready_msg_dict = PromptHandler.create_gpt_message_dict_from_metadata(
                self, 
                role='user',
                message_metadata=message_metadata
                )

            if name in self.bots_automsg or name in self.bots_chatforme:
                self.automsg_temp_msg_history.append(gpt_ready_msg_dict)
                self.chatforme_temp_msg_history.append(gpt_ready_msg_dict)
                self.logger.info("Message dictionary added to automsg_temp_msg_history & chatforme_temp_msg_history")

            if name in self.bots_ouat:    
                self.ouat_temp_msg_history.append(gpt_ready_msg_dict)
                self.logger.info("Message dictionary added to ouat_temp_msg_history")

            if name not in self.known_bots:
                self.nonbot_temp_msg_history.append(gpt_ready_msg_dict)
                self.chatforme_temp_msg_history.append(gpt_ready_msg_dict)
                self.logger.info("Message dictionary added to nonbot_temp_msg_history & chatforme_temp_msg_history")

        elif message.author is None:

            #TODO Add weith xtract name from message and cleanup the output
            # e.g. make sure self.messaage_history_raw gets a copy of bot data
            # e.g. make sure that message histories are applied correctly
            message_metadata = self.get_bot_message_metadata(message)   
            self.message_history_raw.append(message_metadata)

            self.logger.debug('Here is the BOT message_metadata:')
            self.logger.debug(message_metadata)
            
            extracted_name = self.extract_name_from_message(message)
            message_metadata = {'name':extracted_name}

            gpt_ready_msg_dict = PromptHandler.create_gpt_message_dict_from_strings(
                self, role='assistant',
                name=extracted_name,
                content=message.content)

            self.add_user_to_users_list(message_metadata)

            if extracted_name in self.bots_ouat:
                self.ouat_temp_msg_history.append(gpt_ready_msg_dict)
                self.logger.info("Message dictionary added to ouat_temp_msg_history")
            if extracted_name in self.bots_automsg:
                self.automsg_temp_msg_history.append(gpt_ready_msg_dict)
                self.logger.info("Message dictionary added to automsg_temp_msg_history")
            if extracted_name in self.bots_chatforme:
                self.chatforme_temp_msg_history.append(gpt_ready_msg_dict)
                self.logger.info("Message dictionary added to chatforme_temp_msg_history")

        self.logger.debug(f"message_history_raw:")
        self.logger.debug(self.message_history_raw)
        self.logger.debug("This is the gpt_ready_msg_dict")
        log_dynamic_dict(self.logger, gpt_ready_msg_dict)

if __name__ == '__main__':
    print("loaded MessageHandlerClass.py")