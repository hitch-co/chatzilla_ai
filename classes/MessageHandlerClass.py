
from my_modules.config import load_env, load_yaml
from my_modules import my_logging
from my_modules.my_logging import log_as_json

class MessageHandler:
    def __init__(self, gpt_thrd_mgr):
        self.logger = my_logging.create_logger(
            dirname='log', 
            logger_name='logger_MessageHandler',
            debug_level='DEBUG',
            mode='w',
            stream_logs=True
            )
        self.logger.debug('MessageHandler initialized.')

        #Instantiate the gpt_thrd_mgr class for adding messages to gpt thread
        self.gpt_thrd_mgr = gpt_thrd_mgr
         
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

    def _get_message_metadata(self, message) -> None:
        # Collect all metadata
        message_metadata = {
            'badges': getattr(message.tags, 'badges', ''),
            'name': getattr(message.author, 'name', ''),
            'user_id': getattr(message.author, 'id', ''),
            'display_name': getattr(message.author, 'display_name', ''),
            'channel': getattr(message.channel, 'name', ''),
            'timestamp': getattr(message, 'timestamp', None).strftime('%Y-%m-%d %H:%M:%S') if getattr(message, 'timestamp', None) else '',
            'tags': message.tags if hasattr(message, 'tags') else {},
            'content': f'<<<{getattr(message.author, "name", "")}>>>: {getattr(message, "content", "")}',
        }
        return message_metadata

    def _add_user_to_users_list(self, message_metadata: dict) -> None:
        self.users_in_messages_list.append(message_metadata['name'])
        self.users_in_messages_list = list(set(self.users_in_messages_list))

    def _extract_name_from_message(self, message):
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

    def _create_gpt_message_dict_from_strings(self,
                                             content,
                                             role='user',
                                             name='unknown'):
        if role == 'system':
            gpt_ready_msg_dict = {'role': role, 'content': f'{content}'}
        if role in ['user','assistant']:
            gpt_ready_msg_dict = {'role': role, 'content': f'<<<{name}>>>: {content}'}

        return gpt_ready_msg_dict
    
    def _pop_message_from_message_history(self, msg_history_list_dict, msg_history_limit):
        if len(msg_history_list_dict) > msg_history_limit:
            msg_history_list_dict.pop(0)
        return msg_history_list_dict
    
    def add_to_appropriate_message_history(self, message):
        self.logger.info(f"Message content: {message.content}")

        if message.author is not None:
            message_metadata = self._get_message_metadata(message)            
            name = message_metadata['name']
            self._add_user_to_users_list(message_metadata)

            # Add to message_history_raw
            self.logger.debug(f"'{message.author.name}' message_data:")
            self.logger.debug(message_metadata)
            self.message_history_raw.append(message_metadata)

            # Create GPT-ready message dict
            gpt_ready_msg_dict = self._create_gpt_message_dict_from_strings(
                role='user',
                name=message_metadata['name'],
                content=message_metadata['content']
                )
            
            # Append Message history to appropriate bot
            if name in self.bots_automsg or name in self.bots_chatforme:
                self.automsg_temp_msg_history.append(gpt_ready_msg_dict)
                self.chatforme_temp_msg_history.append(gpt_ready_msg_dict)
                self.logger.info("Message dictionary added to automsg_temp_msg_history & chatforme_temp_msg_history")

            if name in self.bots_ouat:    
                #Send message to message history
                self.ouat_temp_msg_history.append(gpt_ready_msg_dict)

                #Send message to GPT thread
                self.gpt_thrd_mgr.add_message_to_thread(
                    thread_id=self.gpt_thrd_mgr.threads['storyteller']['id'], 
                    role='user', 
                    message_content=gpt_ready_msg_dict['content']
                )
                self.logger.info("Message dictionary added to ouat_temp_msg_history and message added to ouat thread")

            if name not in self.known_bots:
                self.nonbot_temp_msg_history.append(gpt_ready_msg_dict)
                self.chatforme_temp_msg_history.append(gpt_ready_msg_dict)
                self.logger.info("Message dictionary added to nonbot_temp_msg_history & chatforme_temp_msg_history")

        elif message.author is None:
            #TODO Add with extract name from message and cleanup the output
            # e.g. make sure self.messaage_history_raw gets a copy of bot data
            # e.g. make sure that message histories are applied correctly
            message_metadata = self._get_message_metadata(message)   
            self.message_history_raw.append(message_metadata)

            self.logger.debug('Here is the raw bot message_metadata:')
            self.logger.debug(message_metadata)
            
            extracted_name = self._extract_name_from_message(message)
            message_metadata = {'name':extracted_name}

            gpt_ready_msg_dict = self._create_gpt_message_dict_from_strings(
                role='assistant',
                name=extracted_name,
                content=message.content
                )

            self._add_user_to_users_list(message_metadata)

            if extracted_name in self.bots_ouat:
                #Send message to message history
                self.ouat_temp_msg_history.append(gpt_ready_msg_dict)

                #Send message to GPT thread
                self.gpt_thrd_mgr.add_message_to_thread(
                    thread_id=self.gpt_thrd_mgr.threads['storyteller']['id'], 
                    role='user', 
                    message_content=gpt_ready_msg_dict['content']
                )
                self.logger.info("Message dictionary added to ouat_temp_msg_history and message added to ouat thread")

            if extracted_name in self.bots_automsg:
                self.automsg_temp_msg_history.append(gpt_ready_msg_dict)
                self.logger.info("Message dictionary added to automsg_temp_msg_history")
            if extracted_name in self.bots_chatforme:
                self.chatforme_temp_msg_history.append(gpt_ready_msg_dict)
                self.logger.info("Message dictionary added to chatforme_temp_msg_history")

        #cleanup msg histories for GPT
        message_histories = [
            (self.ouat_temp_msg_history, 10),
            (self.chatforme_temp_msg_history, 10),
            (self.automsg_temp_msg_history, 10),
            (self.nonbot_temp_msg_history, 10)
        ]
        for msg_history, limit in message_histories:
            self._pop_message_from_message_history(msg_history_list_dict=msg_history, msg_history_limit=limit)

        self.logger.debug(f"message_history_raw:")
        self.logger.debug(self.message_history_raw)
        self.logger.debug("This is the gpt_ready_msg_dict")
        self.logger.debug(gpt_ready_msg_dict)
        #log_as_json(self.logger, gpt_ready_msg_dict)

if __name__ == '__main__':
    print("loaded MessageHandlerClass.py")