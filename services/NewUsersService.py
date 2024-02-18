import asyncio
import random

from classes.ConfigManagerClass import ConfigManager

from my_modules.my_logging import create_logger

runtime_logger_level = 'INFO'

class NewUsersService:
    def __init__(self):

        self.config = ''#ConfigManager.get_instance()

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

    async def get_users_to_send_message_list(
            self,
            historic_users_list: list,
            current_users_list: dict
            ):

        #set diff from current_user_names and historic_users_list
        users_not_yet_sent_message = await self._get_users_not_yet_sent_message(
            historic_users_list=historic_users_list,
            current_users_list=current_users_list
            )

        return users_not_yet_sent_message

    async def _get_users_not_yet_sent_message(
            self,
            historic_users_list: list,
            current_users_list: dict,
            users_not_yet_sent_message: list = None
            ) -> list:
        self.logger.info(f"historic_users_list: {historic_users_list}")
        self.logger.info(f"current_users_list: {current_users_list}")

        #set diff from current_user_names and historic_users_list
        current_new_usernames = await self._find_unique_to_new_list(
            source_list=historic_users_list,
            new_list=current_users_list
            )
        self.logger.info(f"current_new_usernames: {current_new_usernames}")

        #set diff from current_user_names and self.users_sent_messages_list
        if users_not_yet_sent_message is None:
            users_not_yet_sent_message = self.users_sent_messages_list

        self.logger.info(f"users_not_yet_sent_message: {users_not_yet_sent_message}")
        users_not_yet_sent_message = await self._find_unique_to_new_list(
            source_list=self.users_sent_messages_list,
            new_list=current_new_usernames
            )      
        return users_not_yet_sent_message
    
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
            ) -> list:
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
        self.logger.info("This is the list of unique_users:")
        self.logger.info(unique_users)
        
        return unique_users
    
if __name__ == "__main__":
    print("tests")

    # # Test the _get_users_not_yet_sent_message() fucntion
    # historic_users_list = ['user1', 'user2', 'user3']
    # current_users_list = ['user1', 'user2', 'user3', 'user4', 'user5']
    # users_not_yet_sent_message = ['user4']
    # new_users_service = NewUsersService()
    # new_users_service.config = ''
    # new_users_service.users_sent_messages_list = ['user4']
    # result = asyncio.run(new_users_service._get_users_not_yet_sent_message(
    #     historic_users_list, 
    #     current_users_list, 
    #     users_not_yet_sent_message
    #     ))
    # print("result:")
    # print(result)