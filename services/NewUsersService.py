import asyncio
import numpy as np
import random

from my_modules.my_logging import create_logger

from services.ChatForMeService import ChatForMeService
runtime_logger_level = 'DEBUG'

class NewUsersService:
    def __init__(
            self,
            botclass
            ):

        self.logger = create_logger(
            dirname='log', 
            logger_name='logger_NewUsersService', 
            debug_level=runtime_logger_level,
            mode='w',
            stream_logs=True,
            encoding='UTF-8'
            )

        #create newusers event
        self.newusers_ready_event = asyncio.Event()

        #Bot
        self.botclass = botclass
        
        #chatforme 
        self.chatforme_service = ChatForMeService(self.botclass)

    async def send_message_to_new_users_task(self, interval_seconds):
        while True:
            await asyncio.sleep(interval_seconds)
            await self.send_message_to_new_users()
            
    async def send_message_to_new_users(self):
        # Extract newusers list, each 'user_login' from list and then string of users
        new_users = await self._get_new_users_since_last_session()
        new_user_names = [user['user_login'] for user in new_users]
        new_user_names_str = ', '.join(new_user_names)
        self.new_users_sent_messages_list = []

        #if no new/unique users found
        if new_user_names_str == 'no unique users':
            self.logger.info("No users found, starting chat for me...")
            newusers_nonewusers_prompt = self.botclass.yaml_data['newusers_nonewusers_prompt']
            msg_history = self.botclass.message_handler.chatforme_msg_history 

            #Select prompt from argument and format replacements
            random_letter = random.choice('abcdefghijklmnopqrstuvwxyz')
            replacements_dict = {
                "wordcount_medium": self.botclass.wordcount_medium,
                "random_letter": random_letter
                }
            try:
                gpt_response = await self.chatforme_service.make_msghistory_gpt_response(
                    prompt_text=newusers_nonewusers_prompt,
                    replacements_dict=replacements_dict,
                    msg_history=msg_history
                )
                self.logger.debug(f"'chatforme' completed successfully with response: {gpt_response}.")
            
            except Exception as e:
                self.logger.error(f"Error occurred in 'chatforme': {e}")

        #if no new/unique users found
        else:      
            new_users_prompt = self.botclass.yaml_data['newusers_msg_prompt']
            self.logger.info("New users found, starting new users message...")

            #set diff from new_user_names and new_users_sent_messages_list
            users_not_yet_sent_message = await self._find_unique_to_second_list(
                source_list=new_user_names,
                new_list=self.new_users_sent_messages_list
                )            
            random_new_user = self._select_random_user(users_not_yet_sent_message)
            self.new_users_sent_messages_list.append(random_new_user)

            replacements_dict = {
                "selected_new_user":random_new_user,
                "wordcount_medium":self.botclass.wordcount_medium
            }
            try:
                gpt_response = await self.chatforme_service.make_singleprompt_gpt_response(
                    prompt_text=new_users_prompt,
                    replacements_dict=replacements_dict)
                
                self.logger.info(f"New users: {new_user_names_str}")
                self.logger.info(f"Users sent message: {self.new_users_sent_messages_list}")
                self.logger.info(f"Sent message to: {random_new_user}")
                self.logger.info(f"Message: {gpt_response}")

            except Exception as e:
                self.logger.error(f"Error occurred in 'make_singleprompt_gpt_response': {e}")            

    async def _select_random_user(self, user_list):
        random_user = np.random.rand(user_list)
        return random_user

    async def _find_unique_to_second_list(self, source_list, new_list):
        set1 = set(source_list)
        set2 = set(new_list)
        unique_strings = set2 - set1
        return list(unique_strings)

    async def find_unique_to_second_dict(self, source_dict, new_dict):
        # Assuming the first dictionary in list2 represents the key structure
        keys = new_dict[0].keys()

        # Convert list1 and list2 to sets of a primary key (assuming the first key is unique)
        primary_key = next(iter(keys))
        set1 = {user[primary_key] for user in source_dict}
        set2 = {user[primary_key] for user in new_dict}

        # Find the difference - users in list2 but not in list1
        unique_user_ids = set2 - set1

        # Convert the unique user_ids back to dictionary format
        unique_users = [user for user in new_dict if user[primary_key] in unique_user_ids]

        # Check if unique_users is empty and create a placeholder if it is
        if not unique_users:
            placeholder = {key: "no unique users" for key in keys}
            return [placeholder]

        return unique_users

    async def _get_new_users_since_last_session(self):
        #TODO: Should BQ Uploader be injected instead of the entire botclass?
        self.botclass.current_users_in_session = await self.botclass.message_handler.get_current_users_in_session(
            bearer_token = self.botclass.TWITCH_BOT_ACCESS_TOKEN,
            broadcaster_id = self.botclass.broadcaster_id,
            moderator_id = self.botclass.moderator_id,
            twitch_bot_client_id = self.botclass.twitch_bot_client_id
            )
        new_users_since_last_sesion = await self.find_unique_to_second_dict(
            source_dict = self.botclass.historic_users_at_start_of_session, 
            new_dict = self.botclass.current_users_in_session
            )

        return new_users_since_last_sesion