from tenacity import retry, stop_after_attempt, wait_fixed
import requests
import traceback

from my_modules import my_logging
from my_modules import utils

runtime_logger_level = 'INFO'

class MessageHandler:
    def __init__(self, msg_history_limit):
        self.logger = my_logging.create_logger(
            dirname='log', 
            logger_name='logger_MessageHandler',
            debug_level=runtime_logger_level,
            mode='w',
            stream_logs=True
            )
        self.msg_history_limit = msg_history_limit

        # Chatters endpoint
        self.twitch_get_chatters_endpoint = 'https://api.twitch.tv/helix/chat/chatters'

        #Users in message history
        self.users_in_messages_list = []
        self.current_users_in_session = []

        #message_history_raw
        self.message_history_raw = []
        self.all_msg_history_gptdict = []

        #Message History Lists
        self.ouat_msg_history = []
        self.chatforme_msg_history = []
        self.nonbot_temp_msg_history = []

        self.logger.info('MessageHandler initialized.')

    def _get_message_metadata(self, message) -> None:

        message_metadata = {
            'badges': getattr(message.tags, 'badges', '_none'),
            'name': getattr(message.author, 'name', '_unknown'),
            'user_id': getattr(message.author, 'id', ''),
            'display_name': getattr(message.author, 'display_name', '_unknown'),
            'channel': getattr(message.channel, 'name', '_unknown'),
            'timestamp': getattr(message, 'timestamp', None).strftime('%Y-%m-%d %H:%M:%S') if getattr(message, 'timestamp', None) else '',
            'tags': message.tags if hasattr(message, 'tags') else {},
            'content': f'{getattr(message, "content", "")}',
            'role': None #generated below
        }

        if message.author is not None:          
            message_metadata['role'] = 'user'
            message_metadata['content'] = message_metadata['content']

        elif message.author is None: 
            message_metadata['name'] = self._extract_name_from_message(message)
            message_metadata['role'] = 'assistant'
            message_metadata['content'] = message.content

        return message_metadata

    def _cleanup_message_history(self):
        # Cleanup message histories for GPT
        message_histories = [
            ("ouat_msg_history", self.ouat_msg_history, self.msg_history_limit),
            ("chatforme_msg_history", self.chatforme_msg_history, self.msg_history_limit),
            ("nonbot_temp_msg_history", self.nonbot_temp_msg_history, self.msg_history_limit),
            ("all_msg_history_gptdict", self.all_msg_history_gptdict, self.msg_history_limit)
        ]
        for name, msg_history, limit in message_histories:
            self._pop_message_from_message_history(msg_history_list_dict=msg_history, msg_history_limit=limit)
            if msg_history:
                self.logger.debug(f"Log history cleaned for {name}. Preview of latest message:")
                self.logger.debug(f"{msg_history[-1]}")
            else:
                self.logger.debug(f"{name}: No messages in history.")

    def _add_user_to_users_in_messages_list(self, message_metadata: dict) -> None:
        self.users_in_messages_list.append(message_metadata['name'])
        self.users_in_messages_list = list(set(self.users_in_messages_list))

    #TODO: get_channel_viewers should probably be a separate helper
    # module/function/class to work with the twitch API directly
    async def get_current_users_in_session(
            self, 
            bearer_token,
            broadcaster_id,
            moderator_id,
            twitch_bot_client_id
            ):

            #Get response/data
            response = await self._get_channel_viewers(
                bearer_token=bearer_token,
                broadcaster_id=broadcaster_id,
                moderator_id=moderator_id,
                twitch_bot_client_id=twitch_bot_client_id
            )
            response_json = response.json()
            current_users_in_session = response_json['data'] #-> list[{user_id, user_login, user_name},{}] 
            
            self.logger.info(f"current_users_in_session: {current_users_in_session}")
            return current_users_in_session 

    #TODO: get_channel_viewers should probably be a separate helper
    # module/function/class to work with the twitch API directly
    def get_string_of_users(self, usernames_list) -> str:
        users_in_users_list = list(set([username for username in usernames_list]))
        users_in_users_list_text = "'"+", ".join(users_in_users_list)+"'"
        self.logger.info(f"These are the users_in_message_list_text: {users_in_users_list_text}")
        return users_in_users_list_text

    #TODO: get_channel_viewers should probably be a separate helper
    # module/function/class to work with the twitch API directly
    @retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
    async def _get_channel_viewers(
        self,
        bearer_token,
        broadcaster_id,
        moderator_id,
        twitch_bot_client_id
        ) -> object:
        try:
            self.logger.debug(f'Getting channel viewers with bearer_token')
            base_url=self.twitch_get_chatters_endpoint
            params = {
                'broadcaster_id': broadcaster_id,
                'moderator_id': moderator_id
            }
            headers = {
                'Authorization': f'Bearer {bearer_token}',
                'Client-Id': twitch_bot_client_id
            }
            response = requests.get(base_url, params=params, headers=headers)
            self.logger.debug(f'Received response: {response}')

            utils.write_json_to_file(
                response.json(), 
                variable_name_text='channel_viewers', 
                dirname='log/get_chatters_data'
                )
            self.logger.debug('Wrote response.json() to file...')

            if response.status_code == 200:
                self.logger.debug("Response.json(): %s", response.json())
            else:
                self.logger.error("Failed: %s, %s", response.status_code, response.text)
                response.raise_for_status()

            return response
        
        except Exception as e:
            self.logger.error(f"An exception occurred: {e}")
            traceback_details = traceback.format_exc()
            self.logger.error(traceback_details)
            raise
    
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
            self.logger.debug(f"This is the message_extracted_name: {message_extracted_name}:")
            self.logger.debug(message.raw_data)
            return message_extracted_name

    def create_gpt_message_dict_from_strings(
            self,
            content,
            role='user',
            name='unknown'
            ):
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
        #Grab and write metadata, add users to users list
        message_metadata = self._get_message_metadata(message)

        message_role = message_metadata['role']
        message_username = message_metadata['name']
        message_content = message_metadata['content']

        self._add_user_to_users_in_messages_list(message_metadata)
        self.message_history_raw.append(message_metadata)
        
        self.logger.debug("This is the message_metadata")
        self.logger.debug(message_metadata)
        self.logger.info(f"message_username: {message_username}")
        self.logger.info(f"message content: {message_content}")

        #Create gpt message dict
        gpt_ready_msg_dict = self.create_gpt_message_dict_from_strings(
            role=message_role,
            name=message_username,
            content=message_content
            )            

        #Apply message dict to msg histories
        self.chatforme_msg_history.append(gpt_ready_msg_dict)
        self.all_msg_history_gptdict.append(gpt_ready_msg_dict)

        if message.author is not None:
            self.nonbot_temp_msg_history.append(gpt_ready_msg_dict)
        elif message.author is None: 
            self.ouat_msg_history.append(gpt_ready_msg_dict)

        #cleanup msg histories for GPT
        self._cleanup_message_history()

        #log 
        # self.logger.debug(f"message_history_raw:")
        # self.logger.debug(self.message_history_raw)
        # self.logger.debug(f"self.all_msg_history_gptdict:") 
        # self.logger.debug(self.all_msg_history_gptdict)
        # self.logger.debug("This is the gpt_ready_msg_dict")
        # self.logger.debug(gpt_ready_msg_dict)

if __name__ == '__main__':
    print("loaded MessageHandlerClass.py")