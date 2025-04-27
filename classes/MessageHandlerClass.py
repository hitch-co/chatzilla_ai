from classes.ConfigManagerClass import ConfigManager
from models.task import AddMessageTask
from my_modules import my_logging
import hashlib
import re

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

        # Message_history_raw
        self.message_history_raw = []
        self.all_msg_history_gptdict = []

    def _generate_message_id(self, channel: str, user_id: str, timestamp: str, content: str) -> str:
        unique_string = f"{channel}_{user_id}_{timestamp}_{content}"
        return hashlib.md5(unique_string.encode()).hexdigest()

    def _get_message_metadata(self, message: object, interaction_type='message') -> dict:
        # Pull data off the message object
        badges = getattr(message.tags, 'badges', '_none')
        name = getattr(message.author, 'name', '_unknown')
        user_id = getattr(message.author, 'id', '_unknown')
        message_author = getattr(message, 'author', '_unknown')
        display_name = getattr(message.author, 'display_name', '_unknown')
        channel = getattr(message.channel, 'name', '_unknown')
        timestamp_attr = getattr(message, 'timestamp', None)
        timestamp = timestamp_attr.strftime('%Y-%m-%d %H:%M:%S') if timestamp_attr else ''
        tags = message.tags if hasattr(message, 'tags') else {}
        raw_data = getattr(message, 'raw_data', '_unknown')

        # Clean up message content
        raw_content = getattr(message, 'content', '')
        cleaned_content = self._clean_message_content(content = raw_content)

        # (Optional) Update the message object’s content if desired
        message.content = cleaned_content

        # Generate message_id
        message_id = self._generate_message_id(
            channel=channel,
            user_id=user_id,
            timestamp=timestamp,
            content=cleaned_content
        )

        # Determine interaction_type
        if cleaned_content.startswith('!') or self.config.twitch_bot_display_name in cleaned_content:
            final_interaction_type = 'command'
        else:
            final_interaction_type = interaction_type

        # Determine role and name (if needed) based on the author’s presence
        if message_author is not None:
            role = 'user'
            final_name = name
        else:
            role = 'assistant'
            # Potentially extract name from raw_data if no author object:
            final_name = self._extract_name_from_message(raw_data)

        # Build dictionary in one pass at the end
        message_metadata = {
            'badges': badges,
            'name': final_name,
            'user_id': user_id,
            'display_name': display_name,
            'channel': channel,
            'timestamp': timestamp,
            'tags': tags,
            'content': cleaned_content,
            'role': role,
            'interaction_type': final_interaction_type,
            'raw_data': raw_data,
            'message_author': message_author,
            'message_id': message_id
        }

        return message_metadata

    def _clean_message_content(self, content) -> str:
        content_temp = content
        if content.startswith('!'):
            words = content.split(' ')
            words[0] = words[0].lower()
            content_temp = ' '.join(words)

        for correct_command, misspellings in self.config.command_spellcheck_terms.items():
            for misspelled in misspellings:
                # Using a regular expression to match whole commands only
                pattern = r'(^|\s)' + re.escape(misspelled) + r'(\s|$)'
                cleaned_content = re.sub(pattern, r'\1' + correct_command + r'\2', content_temp)

        return cleaned_content

    def _cleanup_message_history(self):
        # Cleanup message histories for GPT
        message_histories = [
            ("all_msg_history_gptdict", self.all_msg_history_gptdict, self.msg_history_limit)
        ]
        for name, msg_history, limit in message_histories:
            self._pop_message_from_message_history(msg_history_list_dict=msg_history, msg_history_limit=limit)
            if msg_history:
                self.logger.debug(f"Log history cleaned for {name}. Preview of latest message: {msg_history[-1]}")
            else:
                self.logger.debug(f"{name}: No messages in history.")

    def _add_user_to_users_in_messages_list(self, message_metadata: dict) -> None:
        self.users_in_messages_list.append(message_metadata['name'])
        self.users_in_messages_list = list(set(self.users_in_messages_list))

        user_list = list(set([username for username in self.users_in_messages_list]))
        self.users_in_messages_list_text = "'"+", ".join(user_list)+"'"

        self.logger.debug(f"users_in_messages_list: {self.users_in_messages_list}")
        self.logger.debug(f"users_in_messages_list_test: {self.users_in_messages_list_text}")

    def _extract_name_from_message(self, message_rawdata):

        start_index = message_rawdata.find(":") + 1
        end_index = message_rawdata.find("!")

        if start_index == 0 or end_index == -1:
            self.logger.warning(f"No message_extracted_name found.  This is message_rawdata:")
            self.logger.warning(message_rawdata)
            return 'unknown_name - see message_rawdata for details'
        else:
            message_extracted_name = message_rawdata[start_index:end_index]
            self.logger.debug(f"This is the message_extracted_name: {message_extracted_name}:")
            self.logger.debug(message_rawdata)
            return message_extracted_name

    def _transform_content_to_gpt_ready_content(self, name, role, content, timestamp) -> str:
        if role == 'system':
            content = f'<<<{self.config.twitch_bot_display_name or "bot"}>>>: ({timestamp}) {content}'        
        if role in ['user','assistant']:
            content = f'<<<{name}>>>: ({timestamp}) {content}'
        return content

    # Could be it's own "message" class as this represents a single message object
    def _create_gpt_message_dict_from_strings(
            self,
            content,
            role='user',
            name='unknown',
            timestamp='unknown'
            ):
        content = self._transform_content_to_gpt_ready_content(name, role, content, timestamp) 
        gpt_ready_msg_dict = {'role': role, 'content': content}
        return gpt_ready_msg_dict
    
    def _pop_message_from_message_history(self, msg_history_list_dict, msg_history_limit):
        if len(msg_history_list_dict) > msg_history_limit:
            msg_history_list_dict.pop(0)

    async def create_and_queue_message_task(
        self, 
        thread_name, 
        message_metadata: dict,
        model_vendor_config=None
        ):  

        # Grab metadata
        message_role = message_metadata['role']
        message_name = message_metadata['name']
        message_content = message_metadata['content']
        message_timestamp = message_metadata['timestamp']
        self.logger.info("Adding message to queue...")
        self.logger.debug("This is the message_metadata: {}".format(message_metadata))

        # Check for commands that should not be added to the thread history
        if message_content.startswith('!what'):
            self.logger.info(f"Message '{message_content}' is a command and will not be added to the thread history.")
            return

        if model_vendor_config == None: 
            # Decide vendor/model based on whether user is the bot
            if (
                message_metadata['message_author'] 
                and message_name != self.config.twitch_bot_username
                and message_name != "_unknown"
            ):
                vendor = "openai"
                model = "n/a"
                self.logger.info(f"Message author not the bot '{message_name}', message task will be queued with {vendor}.")
            else:
                vendor = "deepseek"
                model = self.config.deepseek_model
                self.logger.info(f"Message author is the bot '{message_name}', message task will be queued with {vendor}.")            
                message_content = f"{message_content}"
        else:
            vendor = model_vendor_config.get('vendor')
            model = model_vendor_config.get('model')
            
        # Create and queue the task
        task = AddMessageTask(
            thread_name,
            message_content=message_content,
            message_role=message_role,
            message_name=message_name,
            message_timestamp=message_timestamp,
            model_vendor_config={"vendor": vendor, "model": model}
        )
        await self.task_manager.add_task_to_queue_and_execute(
            thread_name, 
            task, 
            description=f"Add message to thread history (thread: {thread_name})"
        )

    # TODO: This is almost ready for deprecation.  Need to decide if its possible
    # to use the GPT response manager to handle all message history or optionally
    # use the faiss service to handle message history.
    async def add_to_appropriate_message_history(
            self,
            role,
            name,
            content,
            timestamp
            ):

        self.logger.debug("This is the message_metadata")
        self.logger.debug(f"message_username: {name}")
        self.logger.debug(f"message content: {content}")
        self.logger.debug(f"message_role: {role}")

        #Create gpt message dict
        gpt_ready_msg_dict = self._create_gpt_message_dict_from_strings(
            role=role,
            name=name,
            content=content,
            timestamp=timestamp
            )

        #Apply message dict to msg histories
        self.all_msg_history_gptdict.append(gpt_ready_msg_dict)

        #cleanup msg histories for GPT
        self._cleanup_message_history()
        self.logger.info(f"Message added to message histories.  Total messages: {len(self.all_msg_history_gptdict)}")
        self.logger.info(f"Preview of latest 2 messages in message histories: {self.all_msg_history_gptdict[-2:]}")

if __name__ == '__main__':
    print("loaded MessageHandlerClass.py")