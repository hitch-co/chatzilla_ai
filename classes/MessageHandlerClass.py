
from my_modules.config import load_env, load_yaml
from my_modules import my_logging
from my_modules.my_logging import log_as_json

runtime_logger_level = 'DEBUG'

class MessageHandler:
    def __init__(self):
        self.logger = my_logging.create_logger(
            dirname='log', 
            logger_name='logger_MessageHandler',
            debug_level=runtime_logger_level,
            mode='w',
            stream_logs=True
            )
        self.logger.debug('MessageHandler initialized.')

        #run config
        self.yaml_data = load_yaml()
        load_env(env_filename=self.yaml_data['env_filename'], env_dirname=self.yaml_data['env_dirname'])

        #Bots Lists
        self.bots_automsg = self.yaml_data['twitch-bots']['automsg']
        self.bots_chatforme = self.yaml_data['twitch-bots']['chatforme']
        self.bots_ouat = self.yaml_data['twitch-bots']['onceuponatime']    
        self.bots_vibecheck = self.yaml_data['twitch-bots']['vibecheck']    
        
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
        self.vc_temp_msg_history = []

        #Message History Lists
        self.ouat_temp_msg_history = []
        self.automsg_temp_msg_history = []
        self.chatforme_temp_msg_history = []
        self.nonbot_temp_msg_history = []

    def _get_message_metadata(self, message) -> None:
        # Collect all metadata
        message_metadata = {
            'badges': getattr(message.tags, 'badges', '_none'),
            'name': getattr(message.author, 'name', '_unknown'),
            'user_id': getattr(message.author, 'id', ''),
            'display_name': getattr(message.author, 'display_name', '_unknown'),
            'channel': getattr(message.channel, 'name', '_unknown'),
            'timestamp': getattr(message, 'timestamp', None).strftime('%Y-%m-%d %H:%M:%S') if getattr(message, 'timestamp', None) else '',
            'tags': message.tags if hasattr(message, 'tags') else {},
            # 'content': f'<<<{getattr(message.author, "name", "")}>>>: {getattr(message, "content", "")}',
            'content': f'{getattr(message, "content", "")}',
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
            self.logger.debug(f"No message_extracted_name found.  This is message.raw_data:")
            self.logger.debug(message.raw_data)
            return 'unknown_name - see message.raw_data for details'
        else:
            message_extracted_name = message_rawdata[start_index:end_index]
            self.logger.debug(f"This is the message_extracted_name: {message_extracted_name} and message.raw_data:")
            self.logger.debug(message.raw_data)
            return message_extracted_name

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
        self.logger.info(f"----------------------------------")

        #Grab metadata
        message_metadata = self._get_message_metadata(message)
        self.logger.debug(message_metadata)

        if message.author is not None:          
            message_metadata_name = message_metadata['name']
            self._add_user_to_users_list(message_metadata)
            self.logger.info("message.author is not 'None'")
            self.logger.debug(f"message.author.name: {message.author.name}")
            self.logger.debug(f"message_metadata_name: {message_metadata_name}")
            self.logger.info(f"message.content: {message.content}")
            self.logger.info(f"message_metadata['content']: {message_metadata['content']}")

            gpt_ready_msg_dict = self._create_gpt_message_dict_from_strings(
                role='user',
                name=message_metadata_name,
                content=message_metadata['content']
                )

            # Append every message to these message histories
            self.message_history_raw.append(message_metadata)
            self.vc_temp_msg_history.append(gpt_ready_msg_dict)

            # TODO: Append Message history to appropriate bot. This control flow is redundant under the pretense there will only ever be one bot
            if message_metadata_name in self.bots_automsg or message_metadata_name in self.bots_chatforme:
                self.automsg_temp_msg_history.append(gpt_ready_msg_dict)
                self.chatforme_temp_msg_history.append(gpt_ready_msg_dict)
                self.logger.info("Message dictionary added to automsg_temp_msg_history & chatforme_temp_msg_history")

            # Add Message history to GPT thread
            if message_metadata_name in self.bots_ouat:    
                self.ouat_temp_msg_history.append(gpt_ready_msg_dict)
                self.logger.info("Message dictionary added to ouat_temp_msg_history and message added to ouat thread")

            if message_metadata_name not in self.known_bots:
                self.nonbot_temp_msg_history.append(gpt_ready_msg_dict)
                self.chatforme_temp_msg_history.append(gpt_ready_msg_dict)
                self.logger.info("Message dictionary added to nonbot_temp_msg_history & chatforme_temp_msg_history")

        elif message.author is None: 
            message_extracted_name = self._extract_name_from_message(message)
            message_metadata['name'] = message_extracted_name
            self._add_user_to_users_list(message_metadata)

            self.logger.info("message.author is 'None'")
            self.logger.debug(f"message_extracted_name: {message_extracted_name}")
            self.logger.debug(f"message.content: {message.content}")

            gpt_ready_msg_dict = self._create_gpt_message_dict_from_strings(
                role='assistant',
                name=message_extracted_name,
                content=message.content
                )

            self.message_history_raw.append(message_metadata)
            self.vc_temp_msg_history.append(gpt_ready_msg_dict)

            # TODO: Append Message history to appropriate bot. This control flow is redundant under the pretense there will only ever be one bot
            # NOTE: Be careful of how you capture these, bots from outside of this ecosystems responses won't be captured
            # if message_extracted_name in self.bots_ouat:
            self.ouat_temp_msg_history.append(gpt_ready_msg_dict)
            self.logger.info("Message dictionary added to ouat_temp_msg_history")
            # if message_extracted_name in self.bots_automsg:
            self.automsg_temp_msg_history.append(gpt_ready_msg_dict)
            self.logger.info("Message dictionary added to automsg_temp_msg_history")
            # if message_extracted_name in self.bots_chatforme:
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

        #log 
        # self.logger.debug(f"message_history_raw:")
        # self.logger.debug(self.message_history_raw)
        self.logger.debug(f"self.vc_temp_msg_history:") 
        self.logger.debug(self.vc_temp_msg_history)
        self.logger.debug("This is the gpt_ready_msg_dict")
        self.logger.debug(gpt_ready_msg_dict)

if __name__ == '__main__':
    print("loaded MessageHandlerClass.py")