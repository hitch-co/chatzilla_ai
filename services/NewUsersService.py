import asyncio
import random

from classes.ConfigManagerClass import ConfigManager

from my_modules.my_logging import create_logger
from my_modules import utils
runtime_logger_level = 'WARNING'

class NewUsersService:
    def __init__(self):
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

        self.known_bots = utils.load_json(
            dir_path='config',
            file_name='known_bots.json'
            )['known_bots']

    async def get_users_not_yet_sent_message(
            self,
            historic_users_list: list,
            current_users_list: dict,
            users_sent_messages_list: list = None
            ) -> list:
        self.logger.debug("inputs:")
        self.logger.debug(f"historic_users_list: {historic_users_list}")
        self.logger.debug(f"current_users_list: {current_users_list}")
        self.logger.debug(f"users_sent_messages_list: {users_sent_messages_list}")

        #make lowercase prior to comparison
        historic_users_list = [user.lower() for user in historic_users_list]
        current_users_list = [user.lower() for user in current_users_list]

        #set diff from current_user_names and historic_users_list, remove known bots
        current_users_list_excluding_bots = [user for user in current_users_list if user not in self.known_bots]
        current_new_usernames = await utils.find_unique_to_new_list(
            source_list=historic_users_list,
            new_list=current_users_list_excluding_bots
            )

        self.logger.debug(f"Updated items:")
        self.logger.debug(f"known_bots: {self.known_bots}")
        self.logger.debug(f"current_new_usernames (after excluding bots): {current_new_usernames}")

        # If users_sent_messages_list is None, use the class variable
        if users_sent_messages_list is None:
            users_sent_messages_list = self.users_sent_messages_list
        self.logger.debug(f"users_sent_messages_list (after setting None if applicable): {users_sent_messages_list}")

        users_not_yet_sent_message = await utils.find_unique_to_new_list(
            source_list=self.users_sent_messages_list,
            new_list=current_new_usernames
            )
        self.logger.info(f"users_not_yet_sent_message: {users_not_yet_sent_message}")   
        return users_not_yet_sent_message

if __name__ == "__main__":
    print("tests")
    # Test the get_users_not_yet_sent_message() fucntion
    historic_users_list = ['user1', 'user2', 'user3']
    current_users_list = ['user1', 'user2', 'user3', 'user4', 'user5', 'streamlabs']
    new_users_service = NewUsersService()
    print(f"known_bots: {new_users_service.known_bots}")
    result = asyncio.run(new_users_service.get_users_not_yet_sent_message(
        historic_users_list, 
        current_users_list
        ))
    print("result:")
    print(result)