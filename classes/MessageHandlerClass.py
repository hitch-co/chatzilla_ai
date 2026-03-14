from classes.ConfigManagerClass import ConfigManager
from models.task import AddMessageTask
from my_modules import my_logging
import hashlib
import re
import time

runtime_logger_level = 'INFO'

class MessageHandler:
    def __init__(self, task_manager, msg_history_limit):
        self.logger = my_logging.create_logger(
            dirname='log', 
            logger_name='MessageHandlerClass',
            debug_level=runtime_logger_level,
            mode='w',
            stream_logs=True
            )
        
        # Initialize config
        self.config = ConfigManager.get_instance()

        # GPT task Manager
        self.task_manager = task_manager

        # Message History Limit
        self.msg_history_limit = msg_history_limit

        # Users in message history
        self.users_in_messages_list = []

        self.recent_message_metadata = []

        # Message_history_raw
        self.message_history_raw = []
        self.all_msg_history_gptdict = []

    def _generate_message_id(self, channel: str, user_id: str, timestamp: str, content: str) -> str:
        unique_string = f"{channel}_{user_id}_{timestamp}_{content}"
        return hashlib.md5(unique_string.encode()).hexdigest()

    def _get_message_metadata(self, message: object, interaction_type='message') -> dict:
        badges = getattr(message.tags, 'badges', '_none')
        name = getattr(message.author, 'name', '_unknown')
        user_id = getattr(message.author, 'id', '_unknown')
        message_author = getattr(message, 'author', '_unknown')
        display_name = getattr(message.author, 'display_name', '_unknown')  
        channel = getattr(message.channel, 'name', '_unknown')
        timestamp = getattr(message, 'timestamp', None).strftime('%Y-%m-%d %H:%M:%S') if getattr(message, 'timestamp', None) else ''
        tags = message.tags if hasattr(message, 'tags') else {}
        content = f'{getattr(message, "content", "")}'
        raw_data = getattr(message, 'raw_data', '_unknown')
        
        # Clean up message content
        content = self._clean_message_content(content, self.config.command_spellcheck_terms)

        # Generate message_id
        message_id = self._generate_message_id(
            channel=channel,
            user_id=user_id,
            timestamp=timestamp,
            content=content
        )

        message_metadata = {
            'badges': badges,
            'name': name,
            'user_id': user_id,
            'display_name': display_name,
            'channel': channel,
            'timestamp': timestamp,
            'tags': tags,
            'content': content,
            'role': None, #generated below
            'interaction_type': None, #generated below
            'raw_data': raw_data,
            'message_author': message_author,
            'message_id': message_id,
            'is_bot': False
        }
        
        # If message starts with ! or contains @chatzilla_ai, interaction_type is a command 
        if getattr(message, "content", "").startswith('!') or self.config.twitch_bot_display_name in getattr(message, "content", ""):
            message_metadata['interaction_type'] = 'command'
        else:
            message_metadata['interaction_type'] = interaction_type

        if message_author is not None:          
            message_metadata['role'] = 'user'
            message_metadata['content'] = content
            bot_username = (self.config.twitch_bot_username or '').lower()
            message_metadata['is_bot'] = (name or '').lower() == bot_username

        elif message_author is None: 
            message_metadata['name'] = self._extract_name_from_message(raw_data)
            message_metadata['role'] = 'assistant'
            message_metadata['content'] = content
            bot_username = (self.config.twitch_bot_username or '').lower()
            bot_display_name = (self.config.twitch_bot_display_name or '').lower()
            extracted_name = (message_metadata.get('name') or '').lower()
            message_metadata['is_bot'] = extracted_name in {bot_username, bot_display_name}

        return message_metadata

    def _create_recent_message_record(self, message_metadata: dict) -> dict:
        return {
            'name': message_metadata.get('name'),
            'user_id': message_metadata.get('user_id'),
            'timestamp': message_metadata.get('timestamp'),
            'content': message_metadata.get('content'),
            'interaction_type': message_metadata.get('interaction_type'),
            'message_id': message_metadata.get('message_id'),
            'role': message_metadata.get('role'),
            'is_bot': message_metadata.get('is_bot', False),
            'is_planned': message_metadata.get('is_planned', False)
        }

    def _add_to_recent_message_metadata(self, message_metadata: dict) -> None:
        record = self._create_recent_message_record(message_metadata)
        self.recent_message_metadata.append(record)
        if len(self.recent_message_metadata) > self.msg_history_limit:
            self.recent_message_metadata.pop(0)

    def mark_planned_bot_message(self, source: str) -> None:
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        bot_name = (
            self.config.twitch_bot_display_name
            or self.config.twitch_bot_username
            or 'chatzilla_bot'
        )
        message_metadata = {
            'name': bot_name,
            'user_id': self.config.twitch_bot_username or bot_name,
            'timestamp': timestamp,
            'content': f"[planned_bot_response:{source}]",
            'interaction_type': 'planned',
            'message_id': f"planned_{int(time.time() * 1000)}",
            'role': 'assistant',
            'is_bot': True,
            'is_planned': True
        }

        if self.recent_message_metadata and self.recent_message_metadata[-1].get('is_planned'):
            self.recent_message_metadata[-1] = self._create_recent_message_record(message_metadata)
        else:
            self._add_to_recent_message_metadata(message_metadata)

    def mark_confirmed_bot_message(self, source: str, content=None) -> None:
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        bot_name = (
            self.config.twitch_bot_display_name
            or self.config.twitch_bot_username
            or 'chatzilla_bot'
        )
        message_metadata = {
            'name': bot_name,
            'user_id': self.config.twitch_bot_username or bot_name,
            'timestamp': timestamp,
            'content': content or f"[bot_response:{source}]",
            'interaction_type': 'bot_response',
            'message_id': f"bot_{int(time.time() * 1000)}",
            'role': 'assistant',
            'is_bot': True,
            'is_planned': False
        }

        if self.recent_message_metadata and self.recent_message_metadata[-1].get('is_planned'):
            self.recent_message_metadata[-1] = self._create_recent_message_record(message_metadata)
        else:
            self._add_to_recent_message_metadata(message_metadata)

    def get_messages_since_last_bot(self) -> list[dict]:
        if not self.recent_message_metadata:
            return []
        last_bot_index = None
        for idx in range(len(self.recent_message_metadata) - 1, -1, -1):
            if self.recent_message_metadata[idx].get('is_bot'):
                last_bot_index = idx
                break
        if last_bot_index is None:
            return list(self.recent_message_metadata)
        return self.recent_message_metadata[last_bot_index + 1:]

    def get_user_message_count_since_last_bot(self, exclude_commands=True) -> int:
        messages_since = self.get_messages_since_last_bot()
        count = 0
        for msg in messages_since:
            if msg.get('is_bot') or msg.get('role') != 'user':
                continue
            if exclude_commands:
                content = msg.get('content') or ''
                if msg.get('interaction_type') == 'command' or content.startswith('!'):
                    continue
            count += 1
        return count

    def _clean_message_content(self, content, command_spellings: dict) -> str:
        content_temp = content
        if content.startswith('!'):
            words = content.split(' ')
            words[0] = words[0].lower()
            content_temp = ' '.join(words)

        for correct_command, misspellings in command_spellings.items():
            for misspelled in misspellings:
                # Using a regular expression to match whole commands only
                pattern = r'(^|\s)' + re.escape(misspelled) + r'(\s|$)'
                content_temp = re.sub(pattern, r'\1' + correct_command + r'\2', content_temp)
        return content_temp

    def _cleanup_message_history(self):
        # Cleanup message histories for GPT
        message_histories = [
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
        self.logger.debug(f"users_in_messages_list: {self.users_in_messages_list}")

        #String version of users_in_messages_list
        user_list = list(set([username for username in self.users_in_messages_list]))
        users_in_messages_list_text = "'"+", ".join(user_list)+"'"
        self.users_in_messages_list_text = users_in_messages_list_text

    def _extract_name_from_message(self, message_rawdata):

        start_index = message_rawdata.find(":") + 1
        end_index = message_rawdata.find("!")

        if start_index == 0 or end_index == -1:
            self.logger.debug(f"No message_extracted_name found.  This is message_rawdata:")
            self.logger.debug(message_rawdata)
            return 'unknown_name - see message_rawdata for details'
        else:
            message_extracted_name = message_rawdata[start_index:end_index]
            self.logger.debug(f"This is the message_extracted_name: {message_extracted_name}:")
            self.logger.debug(message_rawdata)
            return message_extracted_name

    # Could be it's own "message" class as this represents a single message object
    def _create_gpt_message_dict_from_strings(
            self,
            content,
            role='user',
            name='unknown',
            timestamp='unknown'
            ):
        if role == 'system':
            gpt_ready_msg_dict = {'role': role, 'content': f'<<<bot>>>: ({timestamp}) {content}'}
        if role in ['user','assistant']:
            gpt_ready_msg_dict = {'role': role, 'content': f'<<<{name}>>>: ({timestamp}) {content}'}

        return gpt_ready_msg_dict
    
    def _pop_message_from_message_history(self, msg_history_list_dict, msg_history_limit):
        if len(msg_history_list_dict) > msg_history_limit:
            msg_history_list_dict.pop(0)

    async def add_to_thread_history(
        self, 
        thread_name, 
        message_metadata: dict
        ):  

        # Grab and write metadata, add users to users list
        message_role = message_metadata['role']
        message_username = message_metadata['name']
        message_content = message_metadata['content']
        message_content_w_username = message_username+": "+message_content

        self.logger.info(f"Adding message to queues...")
        self.logger.debug("This is the message_metadata: {}".format(message_metadata))

        # Check for commands that should not be added to the thread history
        if message_content.startswith('!'):
            self.logger.info(f"Message '{message_content}' is a command and will not be added to the thread history.")
            return
    
         # Add user to users list if its not the bot (NOTE: GPT DOES THIS ALREADY FOR BOT RESPONSES, so we don't add bot messages to the message history)
        if message_metadata['message_author'] is not None and message_username != self.config.twitch_bot_username and message_metadata['name'] != "_unknown":
            task = AddMessageTask(thread_name, message_content_w_username, message_role)
            await self.task_manager.add_task_to_queue(thread_name, task)
            self.logger.info(f"Message author not the bot '{message_username}', message task added to queue (thread: {thread_name})")

            # # Wait for the task to complete before continuing
            # Doesn't work because of some async issue
            # await task.future 

        else:
            self.logger.info(f"Message author is the bot '{message_username}', messager not added to queue (already handled by GPT thread)")

    # TODO: This is almost ready for deprecation.  Need to decide if its possible
    # to use the GPT response manager to handle all message history or optionally
    # use the faiss service to handle message history.
    async def add_to_appropriate_message_history(self, message_metadata: dict):

        # Add user to users list
        self._add_user_to_users_in_messages_list(message_metadata)
        self.logger.debug("This is the message_metadata")
        self.logger.debug(f"message_username: {message_metadata['name']}")
        self.logger.debug(f"message content: {message_metadata['content']}")
        self.logger.debug(f"message_role: {message_metadata['role']}")

        #Create gpt message dict
        gpt_ready_msg_dict = self._create_gpt_message_dict_from_strings(
            role=message_metadata['role'],
            name=message_metadata['name'],
            content=message_metadata['content'],
            timestamp=message_metadata['timestamp']
            )

        #Apply message dict to msg histories
        self.message_history_raw.append(message_metadata)
        self.all_msg_history_gptdict.append(gpt_ready_msg_dict)
        self._add_to_recent_message_metadata(message_metadata)

        #cleanup msg histories for GPT
        self._cleanup_message_history()
        self.logger.info("Message added to message histories")
        self.logger.info(f"Preview of latest 2 messages in message histories ({len(self.all_msg_history_gptdict)} total):")

if __name__ == '__main__':
    print("loaded MessageHandlerClass.py")
