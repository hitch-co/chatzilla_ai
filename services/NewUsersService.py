import asyncio
import numpy as np
import random

from my_modules.my_logging import create_logger

from services.ChatForMeService import ChatForMeService
from classes.ConfigManagerClass import ConfigManager

runtime_logger_level = 'DEBUG'

class NewUsersService:
    def __init__(
            self,
            message_handler,
            chatforme_service
            ):

        self.config = ConfigManager.get_instance()

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
        self.users_sent_messages_list = []
        
        #message handler
        self.message_handler = message_handler

        #chatforme 
        self.chatforme_service = chatforme_service

    async def send_message_to_new_users(
            self,
            historic_users_list: list = None,
            current_users_list: list = None
            ):

        # Extract newusers list, each 'user_login' from list and then string of users
        current_new_users_list = await self._find_unique_to_new_dict(
            source_dict = historic_users_list,
            new_dict = current_users_list, 
            )      
          
        current_user_names = [user['user_login'] for user in current_new_users_list]
        current_user_names_str = ', '.join(current_user_names)

        #set diff from current_user_names and self.users_sent_messages_list
        users_not_yet_sent_message = await self._find_unique_to_new_list(
            source_list=self.users_sent_messages_list,
            new_list=current_user_names
            )      

        #if no new/unique users found
        if current_user_names_str == 'no unique users' or len(users_not_yet_sent_message) == 0:
            self.logger.info("No users found, starting chat for me...")
            newusers_nonewusers_prompt = self.config.newusers_nonewusers_prompt
            msg_history = self.message_handler.chatforme_msg_history 

            try:
                #Select prompt from argument and format replacements
                random_letter = random.choice('abcdefghijklmnopqrstuvwxyz')
                replacements_dict = {
                    "wordcount_medium": self.config.wordcount_medium,
                    "random_letter": random_letter
                    }
                gpt_response = await self.chatforme_service.make_msghistory_gpt_response(
                    prompt_text=newusers_nonewusers_prompt,
                    replacements_dict=replacements_dict,
                    msg_history=msg_history
                )
                self.logger.debug(f"'chatforme' completed successfully with response: {gpt_response}.")
                return  
           
            except Exception as e:
                self.logger.error(f"Error occurred in 'chatforme': {e}")

        #if new/unique users found
        elif len(users_not_yet_sent_message) > 0:      
            new_users_prompt = self.config.newusers_msg_prompt
            self.logger.info("New users found, starting new users message...")
            self.logger.debug(f"Initial value of self.users_sent_messages_list: {self.users_sent_messages_list}")   
            random_new_user = await self._select_random_user(users_not_yet_sent_message)
            self.users_sent_messages_list.append(random_new_user)
            
            try:
                replacements_dict = {
                    "random_new_user":random_new_user,
                    "wordcount_medium":self.config.wordcount_medium
                }
                gpt_response = await self.chatforme_service.make_singleprompt_gpt_response(
                    prompt_text=new_users_prompt,
                    replacements_dict=replacements_dict
                    )
                
                self.logger.debug(f"current_new_users_list: {current_new_users_list}")
                self.logger.debug(f"current_user_names: {current_user_names}")
                self.logger.debug(f"current_user_names_str: {current_user_names_str}")
                self.logger.debug(f"self.users_sent_messages_list: {self.users_sent_messages_list}")
                self.logger.debug(f"users_not_yet_sent_message: {users_not_yet_sent_message}")
                self.logger.info(f"random_new_user: {random_new_user}")
                self.logger.info(f"gpt_response: {gpt_response}")
                return

            except Exception as e:
                self.logger.exception(f"Error occurred in 'make_singleprompt_gpt_response': {e}")            
        
        self.logger.warning(f"The function calls current_user_names_str ({current_user_names_str}) and users_not_yet_sent_message: ({users_not_yet_sent_message}) were not met.")
        return
    
    async def _select_random_user(self, user_list):
        random_user = random.choice(user_list)
        return random_user

    async def _find_unique_to_new_list(
            self, 
            source_list, 
            new_list
            ) -> list:
        set1 = set(source_list)
        set2 = set(new_list)
        unique_strings = set2 - set1
        unique_list = list(unique_strings)

        self.logger.debug("_find_unique_to_new_list inputs/output:")
        self.logger.debug(f"source_list: {source_list}")
        self.logger.debug(f"new_list: {new_list}")
        self.logger.debug(f"unique_list: {unique_list}")
        return unique_list

    async def _find_unique_to_new_dict(
            self, 
            source_dict, 
            new_dict
            ) -> dict:
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