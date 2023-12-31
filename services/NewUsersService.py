import asyncio
import numpy as np

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
        user_logins = [user['user_login'] for user in new_users]
        user_logins_str = ', '.join(user_logins)

        # New user messages
        self.users_sent_messages_list = []        
        newuser_prompt = self.botclass.yaml_data['newusers_msg_prompt']
        
        #if no unique users found
        if user_logins_str == 'no unique users':
            self.logger.info("No users found, starting chat for me...")
            try:
                await self.chatforme_service.chatforme_logic(ctx=None)
                self.logger.info("'chatforme' completed successfully.")
            
            except Exception as e:
                self.logger.error(f"Error occurred in 'chatforme': {e}")

        #if unique users found
        else:
            self.logger.info("New users found, starting new users message...")

            #set diff from user_logins and users_sent_messages_list
            users_not_yet_sent_message = self.find_unique_to_second_list(
                source_list=user_logins,
                new_list=self.users_sent_messages_list
                )            
            random_new_user = self._select_random_user(users_not_yet_sent_message)
            self.users_sent_messages_list.append(random_new_user)

            replacements_dict = {
                "selected_new_user":random_new_user,
                "wordcount_medium":self.botclass.wordcount_medium
            }
            try:
                await self.chatforme_service.make_singleprompt_gpt_response(
                    prompt_text=newuser_prompt,
                    replacements_dict=replacements_dict)
                self.logger.info("'make_singleprompt_gpt_response' completed successfully.")
            
            except Exception as e:
                self.logger.error(f"Error occurred in 'make_singleprompt_gpt_response': {e}")            

    async def _select_random_user(user_list):
        random_user = np.random.rand(user_list)
        return random_user

    async def find_unique_to_second_list(self, source_list, new_list):
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
        
        self.botclass.current_users_in_session = await self.botclass.message_handler.get_current_users_in_session(
            bearer_token = self.botclass.TWITCH_BOT_ACCESS_TOKEN,
            broadcaster_id = self.botclass.broadcaster_id,
            moderator_id = self.botclass.moderator_id,
            twitch_bot_client_id = self.botclass.twitch_bot_client_id
            )
        self.botclass.new_users_since_last_sesion = await self.find_unique_to_second_dict(
            source_dict = self.botclass.historic_users_at_start_of_session, 
            new_dict = self.botclass.current_users_in_session
            )

        return self.botclass.new_users_since_last_sesion