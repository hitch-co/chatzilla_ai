import asyncio

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
        new_users = await self._get_new_users_since_last_session()

        # Extract 'user_login' from each dictionarfy and create a list
        user_logins = [user['user_login'] for user in new_users]

        # Join the list into a single string separated by ', '
        user_logins_str = ', '.join(user_logins)
        if user_logins_str == 'no unique users':
            # await self.botclass.channel.send("Still chillin with the same ol' fam and we're happy to have them :)")
            self.logger.info("No users found, starting chat for me...")
            try:
                await self.chatforme_service.chatforme_logic(ctx=None)
                self.logger.info("'chatforme' completed successfully.")
            except Exception as e:
                self.logger.error(f"Error occurred in 'chatforme': {e}")
        else:
            await self.botclass.channel.send(f"These are the new users in this stream: {user_logins_str}")

    async def _get_new_users_since_last_session(self):

        async def find_users_unique_to_second_list(source_list, new_list):
            # Assuming the first dictionary in list2 represents the key structure
            keys = new_list[0].keys()

            # Convert list1 and list2 to sets of a primary key (assuming the first key is unique)
            primary_key = next(iter(keys))
            set1 = {user[primary_key] for user in source_list}
            set2 = {user[primary_key] for user in new_list}

            # Find the difference - users in list2 but not in list1
            unique_user_ids = set2 - set1

            # Convert the unique user_ids back to dictionary format
            unique_users = [user for user in new_list if user[primary_key] in unique_user_ids]

            # Check if unique_users is empty and create a placeholder if it is
            if not unique_users:
                placeholder = {key: "no unique users" for key in keys}
                return [placeholder]

            return unique_users
        
        self.botclass.current_users_in_session = await self.botclass.message_handler.get_current_users_in_session(
            bearer_token = self.botclass.TWITCH_BOT_ACCESS_TOKEN,
            broadcaster_id = self.botclass.broadcaster_id,
            moderator_id = self.botclass.moderator_id,
            twitch_bot_client_id = self.botclass.twitch_bot_client_id
            )
        self.botclass.new_users_since_last_sesion = await find_users_unique_to_second_list(self.botclass.historic_users_at_start_of_session, self.botclass.current_users_in_session)

        return self.botclass.new_users_since_last_sesion