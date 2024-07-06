import asyncio
from twitchio.ext import commands as twitch_commands

import random
import re
import json
import os
import inspect
import time

from models.task import AddMessageTask, CreateExecuteThreadTask

from my_modules.my_logging import create_logger
import modules.adjustable_sleep_task as adjustable_sleep_task

from classes.TwitchAPI import TwitchAPI

# from classes.ConsoleColoursClass import bcolors, printc
from classes import ArticleGeneratorClass
from classes.GPTChatCompletionClass import GPTChatCompletion

from services.VibecheckService import VibeCheckService
from services.NewUsersService import NewUsersService
from services.ChatForMeService import ChatForMeService
from services.AudioService import AudioService
from services.BotEarsService import BotEars
from services.SpeechToTextService import SpeechToTextService
from services.ExplanationService import ExplanationService

runtime_logger_level = 'INFO'
class Bot(twitch_commands.Bot):
    loop_sleep_time = 4

    def __init__(
            self, 
            config, 
            gpt_client, 
            bq_uploader, 
            tts_client, 
            gpt_thread_mgr, 
            gpt_assistant_mgr,
            gpt_response_mgr,
            message_handler,
            twitch_auth
            ):
        
        self.config = config
        self.config.twitch_bot_access_token = os.getenv('TWITCH_BOT_ACCESS_TOKEN')

        super().__init__(
            token=self.config.twitch_bot_access_token,
            name=config.twitch_bot_username,
            prefix='!',
            initial_channels=[self.config.twitch_bot_channel_name],
            nick = 'chatzilla_ai'
        )

        self.logger = create_logger(
            dirname='log', 
            logger_name='TwitchBotClass', 
            debug_level=runtime_logger_level,
            mode='w',
            stream_logs=True,
            encoding='UTF-8'
            )
        
        # dependencies instances
        self.gpt_client = gpt_client
        self.bq_uploader = bq_uploader 
        self.tts_client = tts_client
        self.message_handler = message_handler

        # Initialize the GPTChatCompletion class
        self.gpt_chatcompletion = GPTChatCompletion(
            gpt_client=self.gpt_client,
            yaml_data=self.config
            )
        
        # Initialize the GPTAssistantManager Classes
        self.gpt_assistant_manager = gpt_assistant_mgr
        
        # Create thread manager, Assigning handle_tasks as the callback for when a task is ready
        self.gpt_thread_mgr = gpt_thread_mgr
        self.gpt_thread_mgr.on_task_ready = self.handle_tasks
        self.loop.create_task(self.gpt_thread_mgr.task_scheduler())

        # Create response manager
        self.gpt_response_manager = gpt_response_mgr

        # TODO: Could be a good idea to inject these dependencies into the services
        # instantiate the ChatForMeService
        self.chatforme_service = ChatForMeService(
            tts_client=self.tts_client, #NOTE: Might also be able to use the self.gpt_client here
            send_channel_message=self._send_channel_message_wrapper
            )

        # TODO: Could be a good idea to inject these dependencies into the services
        # instantiate the NewUsersService
        self.newusers_service = NewUsersService()

        # TODO: Could be a good idea to inject these dependencies into the services
        # instantiate the AudioService and BotEars
        self.audio_service = AudioService(volume=self.config.tts_volume)
        device_name = "Microphone (Yeti Classic), MME"
        self.bot_ears = BotEars(
            config=self.config,
            device_name=device_name,
            buffer_length_seconds=self.config.botears_buffer_length_seconds
            )

        # TODO: Could be a good idea to inject these dependencies into the services
        # Instantiate the speech to text service
        self.s2t_service = SpeechToTextService()

        # Instantiate the explanation service
        self.explanation_service = ExplanationService(
            config=self.config,
            gpt_thread_mgr=self.gpt_thread_mgr,
            message_handler=self.message_handler
            )

        #Taken from app authentication class() #TODO: Reudndant with twitchAPI?
        self.twitch_auth = twitch_auth

        # Grab the TwitchAPI class and set the bot/broadcaster/moderator IDs
        self.twitch_api = TwitchAPI()

        #Google Service Account Credentials & BQ Table IDs
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.config.google_application_credentials_file
        
        #Get historic stream viewers (TODO: Should mb be refreshed more frequently)
        self.historic_users_at_start_of_session = self.bq_uploader.fetch_unique_usernames_from_bq_as_list()

        #Set default loop state
        self.is_ouat_loop_active = False
        self.is_vibecheck_loop_active = False

        #counters
        self.ouat_counter = 0


        # Set the thread name and assistant name
        self.ouat_thread_name = 'ouatmsgs'
        self.ouat_assistant_name = 'storyteller'

        #NOTE: ARGUABLY DO NOT NEED TO INITIALIZE THESE HERE
        # BQ Table IDs
        self.userdata_table_id=self.config.talkzillaai_userdata_table_id
        self.usertransactions_table_id=self.config.talkzillaai_usertransactions_table_id

        # Initialize the twitch bot's channel and user IDs
        self.twitch_bot_client_id = self.config.twitch_bot_client_id
        self.logger.info("TwitchBotClass initialized")

        # register commands
        self._register_commands()

    def _register_commands(self):
        # v1. build the decorator, then add the command to the bot directly
        decorator = twitch_commands.command(name='explain', aliases=("p_explain"))
        self.add_command(decorator(self.explanation_service.startexplanation))
        
        # v2. add the command w/ decorator to the bot directly
        decorator = twitch_commands.command(name='stopexplain', aliases=("m_stopexplain", 'stopexplanation', 'endexplain'))
        self.add_command(twitch_commands.command(name='stopexplain', aliases=("m_stopexplain", 'stopexplanation'))(self.explanation_service.stop_explanation))
    
    async def handle_tasks(self, task: dict):
        
        thread_name = task["thread_name"]
        message_role = task["message_role"]

        if task["type"] == "add_message":
            self.logger.debug(f"3. Handling task type 'add_message' for thread: {task['thread_name']}")
            content = task["content"]
            
            try:
                message_object = await self.gpt_response_manager.add_message_to_thread(
                    message_content=content, 
                    thread_name=thread_name,
                    role=message_role
                    )
                self.logger.debug(f"Message object: {message_object}")
            except Exception as e: 
                self.logger.error(f"Error occurred in 'add_message_to_thread': {e}", exc_info=True)
            
        elif task["type"] == "execute_thread":

            # # NOTE: if we decide to bulk add (to reduce api calls and speedup the app), 
            # #  this is where we should dump message queue into thread history
            # await self.message_handler.dump_message_queue_into_thread_history(
            #     thread_name=thread_name
            #     message_history=message_history
            #     )

            self.logger.debug(f"3. Handling task type 'execute_thread' for Assistant/Thread: {task['assistant_name']}, {task['thread_name']}")
            assistant_name = task["assistant_name"]
            thread_instructions = task["thread_instructions"]
            replacements_dict = task["replacements_dict"]
            tts_voice = task["tts_voice"]
            bool_send_channel_message = task["send_channel_message"]          
            
            # Execute the thread
            try:
                gpt_response = await self.gpt_response_manager.execute_thread( 
                    thread_name = thread_name, 
                    assistant_name = assistant_name, 
                    thread_instructions= thread_instructions,
                    replacements_dict=replacements_dict
                )
            except Exception as e:
                self.logger.error(f"Error occurred in 'execute_thread': {e}")
                gpt_response = None

            # Add the GPT response to the appropriate thread history when bool_send_channel_message is False
            if gpt_response is not None and bool_send_channel_message is False:
                await self.message_handler.add_to_specific_thread_history(
                    thread_name=thread_name,
                    message_content=gpt_response
                    )
                self.logger.debug(f"bool_send_channel_message is False, added message to thread for {thread_name}, skipped sending message to channel.")

            # Send the GPT response to the channel when bool_send_channel_message is True
            elif gpt_response is not None and bool_send_channel_message is True:
                try:
                    # Send the GPT response to the channel
                    await self.chatforme_service.send_output_message_and_voice(
                        text=gpt_response,
                        incl_voice=bool_send_channel_message,
                        voice_name=tts_voice
                    )
                except Exception as e:
                    self.logger.error(f"Error occurred in 'send_output_message_and_voice': {e}")
                self.logger.debug("Thread executed...")
                self.logger.debug(f"'{task['type']}' task handled for thread: {thread_name}")   

            # Log an error if the GPT response is None
            elif gpt_response is None:
                self.logger.error(f"Gpt response is None, this should not happen.  Task: {task}")
            else:
                self.logger.error(f"Task type not recognized: {task}")

    async def event_ready(self):
        self.channel = self.get_channel(self.config.twitch_bot_channel_name)
        self.logger.info(f'TwitchBot ready on channel {self.channel} | {self.config.twitch_bot_username} (nick:{self.nick})')

        # initialize the event loop
        self.logger.debug(f"Initializing event loop")
        self.loop = asyncio.get_event_loop()
 
        # send hello world message
        await self._send_hello_world()

        # start OUAT loop
        self.logger.debug(f"Starting OUAT service")
        self.loop.create_task(self.ouat_storyteller_task())

        # Start bot ears streaming
        self.logger.debug(f"Starting bot ears streaming")
        self.loop.create_task(self.bot_ears.start_botears_audio_stream())

        # start newusers loop
        self.logger.debug(f"Starting newusers service")
        self.loop.create_task(self._send_message_to_new_users_task())

        # start authentication refresh loop
        self.logger.debug('Starting the refresh token service')
        self.loop.create_task(self._token_refresh_task())

        # start randomfact loop
        self.logger.debug('Starting the randomfact service')
        self.loop.create_task(self.randomfact_task())

        # start explanation loop
        self.logger.debug('Starting the explanation service')
        self.loop.create_task(self.explanation_service.explanation_task())

        # Create Assistants
        self.assistants_config = self.config.gpt_assistant_prompts
        self.assistants = self.gpt_assistant_manager.create_assistants(
            assistants_config=self.assistants_config
            )

        thread_names = self.config.gpt_thread_names
        self.threads = self.gpt_thread_mgr.create_threads(
            thread_names=thread_names
            )
        
    async def event_message(self, message):
        def clean_message_content(content, command_spellings):
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

        self.logger.info("---------------------------------------")
        self.logger.info("MESSAGE RECEIVED: Processing message...")
        self.logger.info(f"Message from: {message.author}")
        self.logger.info(f"Message content: '{message.content}'")
        self.logger.debug(f"This is the message object:")
        self.logger.debug(message)

        # 1. This is the control flow function for creating message histories
        # NOTE: SHould this be awaited to ensure accurate response from GPT in #1b?
        message.content = clean_message_content(
            message.content,
            self.config.command_spellcheck_terms
            )
        
        # 1b. Add the message to the appropriate thread history
        await self.message_handler.add_to_appropriate_message_history(message)
        await self.message_handler.add_to_appropriate_thread_history(
            message=message
            )

        # 1c. if message contains "@chatzilla_ai" (botname) and does not include "!chat", execute a command...
        if self.config.twitch_bot_username in message.content and "!chat" not in message.content and message.author is not None:
            await self._chatforme_main()

        # 2. Process the message through the vibecheck service.
            #NOTE: Should this be a separate task?    
        self.logger.debug("Processing message through the vibecheck service...")

        if hasattr(self, 'vibecheck_service') and self.vibecheck_service is not None:
            await self.vibecheck_service.process_vibecheck_message(
                message_username=getattr(message.author, 'name', '_unknown'),
                message_content=getattr(message, "content", "")
                )

        #TODO: Steps 3 and 4 should probably be added to a task so they can run on a separate thread
        # 3. Get chatter data, store in queue, generate query for sending to BQ
        # 4. Send the data to BQ when queue is full.  Clear queue when done
        if len(self.message_handler.message_history_raw)>=2:

            channel_viewers_queue_query = await self.twitch_api.process_viewers_for_bigquery(
                table_id=self.userdata_table_id,
                bearer_token=self.config.twitch_bot_access_token
                )

            self.bq_uploader.send_queryjob_to_bq(query=channel_viewers_queue_query)            
            viewer_interaction_records = self.bq_uploader.generate_twitch_user_interactions_records_for_bq(records=self.message_handler.message_history_raw)

            self.logger.debug(f"viewer_interaction_records: {viewer_interaction_records}")

            self.bq_uploader.send_recordsjob_to_bq(
                table_id=self.usertransactions_table_id,
                records=viewer_interaction_records
                )

            self.logger.info(f"Clearing message_history_raw and channel_viewers_queue.")
            self.logger.debug(f"MESSAGE HISTORY RAW PRE-CLEAR: {self.message_handler.message_history_raw}")
            self.logger.debug(f"CHANNEL VIEWERS QUEUE PRE-CLEAR: {self.twitch_api.channel_viewers_queue}")
            
            self.message_handler.message_history_raw.clear()
            self.twitch_api.channel_viewers_queue.clear()

        # 5. self.handle_commands runs through bot commands
        if message.author is not None:
            await self.handle_commands(message)
        
        self.logger.debug("THIS IS THE TASK QUEUE:")
        self.logger.debug(self.gpt_thread_mgr.task_queues)
        self.logger.info("MESSAGE PROCESSED: Processing message...")      
        self.logger.info("---------------------------------------")

    def _get_commands(self):
        commands_info = []
        for command_name, command_obj in self.commands.items():
            aliases = command_obj.aliases
            command_info = {
                "name": command_name,
                "aliases": aliases,
            }
            #has more than just aliases?
            self.logger.info(f"command_obj: {command_obj}")
            
            #result
            self.logger.debug(f"Command info: {command_info}")
            commands_info.append(command_info)
        return commands_info
    
    async def _token_refresh_task(self):
        while True:
            try:
                current_time = time.time()
                if self.twitch_auth.access_token_expiry <= current_time:
                    self.logger.warning("Access Token near expiry, generating new access token using the refresh token...")
                    response = await self.twitch_auth.refresh_access_token()
                    tokens = response.json()
                    
                    # Calculate the new expiry time for the access token
                    new_expiry_time = current_time + int(tokens['expires_in']) - 3600
                    
                    self.twitch_auth.access_token_expiry = new_expiry_time
                    self.twitch_auth.handle_auth_callback(response)
                else:
                    self.logger.debug("Access token not nearing expiry. No need to refresh.")
            except Exception as e:
                self.logger.error(f"Failed to refresh Twitch access token: {e}")
            
            # Wait for 30 minutes before checking again
            await asyncio.sleep(1800)

    async def _send_message_to_new_users_task(self):
        self.current_users_list = []
        tts_voice_selected = self.config.tts_voice_newuser
        thread_name = 'chatformemsgs'
        assistant_name = 'newuser_shoutout'

        while True:
            await adjustable_sleep_task.adjustable_sleep_task(self.config, 'newusers_sleep_time')
            self.logger.debug("---------------------------------------")
            self.logger.info("Checking for new users...")

            # Get the current users in the channel
            try:
                current_users_list = await self.twitch_api.retrieve_active_usernames(
                    bearer_token = self.config.twitch_bot_access_token
                    )
                self.logger.info(f"Current users retrieved: {current_users_list}")  
            except Exception as e:
                self.logger.error(f"Failed to retrieve active users from Twitch API: {e}")
                current_users_list = []
                
            # Add self.current_users_list to self.current_users_list as set to remove duplicates
            self.current_users_list = list(set(self.current_users_list + current_users_list))

            if not self.current_users_list:
                self.logger.info("No users in self.current_users_list, skipping this iteration.")
                continue

            # Identify list of users who are new to the channel and have not yet been sent a message
            users_not_yet_sent_message_info = await self.newusers_service.get_users_not_yet_sent_message(
                historic_users_list = self.historic_users_at_start_of_session,
                current_users_list = self.current_users_list,
                users_sent_messages_list = self.newusers_service.users_sent_messages_list
            )

            self.logger.info("New users found in self.current_users_list, starting new users message...")

            self.logger.debug(f"Long-running Current users list: {current_users_list}")
            self.logger.debug(f"Users sent messages list: {self.newusers_service.users_sent_messages_list}")
            self.logger.debug(f"Users not yet sent message: {users_not_yet_sent_message_info}")

            if users_not_yet_sent_message_info:
                eligible_users = [
                    user for user in users_not_yet_sent_message_info
                    if (user['username'] not in self.newusers_service.known_bots and
                        user['username'] not in self.config.twitch_bot_operatorname and
                        user['username'] not in self.config.twitch_bot_channel_name and
                        user['username'] not in self.config.twitch_bot_username and
                        user['username'] not in self.config.twitch_bot_display_name
                        and user['username'] not in "crubeyawne"
                        #and user['username'] not in "nanovision"
                        #and user['username'] not in mods_list
                        )
                ]
                self.logger.debug(f"Eligible users to send a message: {eligible_users}")
            else:
                self.logger.info("No eligible users to send a message.")
                continue
     
            if eligible_users:
                self.logger.info(f"Eligible users found: {len(eligible_users)}")
                random_user = random.choice(eligible_users)  
                random_user_type = random_user['usertype']
                random_user_name = random_user['username'] 

                self.newusers_service.users_sent_messages_list.append(random_user_name)
                self.logger.debug(f"Selected user: {random_user_name} ({random_user_type})")

                # Get the user's chat history
                if random_user_type == "returning":
                    user_specific_chat_history = self.bq_uploader.fetch_user_chat_history_from_bq(
                        user_login=random_user_name,
                        interactions_table_id=self.config.talkzillaai_usertransactions_table_id,
                        users_table_id=self.config.talkzillaai_userdata_table_id,
                        limit=15
                    )
                else:
                    user_specific_chat_history = "none"

                # Create task to send a message to the selected user
                try:
                    replacements_dict = {
                        "random_new_user": random_user_name,
                        "wordcount_medium": self.config.wordcount_medium,
                        "user_specific_chat_history": user_specific_chat_history
                    }

                    # Select the appropriate prompt based on the user type
                    prompt = self.config.newusers_msg_prompt if random_user_type == "new" else self.config.returningusers_msg_prompt

                    # Add an executeTask to the queue
                    task = CreateExecuteThreadTask(
                        thread_name=thread_name,
                        assistant_name=assistant_name,
                        thread_instructions=prompt,
                        replacements_dict=replacements_dict,
                        tts_voice=tts_voice_selected
                    ).to_dict()

                    self.logger.debug(f"Task to add to queue: {task}")
                    await self.gpt_thread_mgr.add_task_to_queue(thread_name, task)

                    self.logger.debug(f"self.newusers_service.users_sent_messages_list: {self.newusers_service.users_sent_messages_list}")
                    self.logger.debug(f"users_not_yet_sent_message: {users_not_yet_sent_message_info}")
                    self.logger.info(f"Sent {random_user_type} user task for run. random_user: {random_user}")


                except Exception as e:
                    self.logger.exception(f"Error occurred in sending {random_user_type} user message: {e}")
                    continue

            else:
                self.logger.info(f"Eligible users list is empty.  eligible_users: {eligible_users}")
                continue

    async def _send_channel_message_wrapper(self, message):
        await self.channel.send(message)

    async def _check_mod(self, ctx) -> bool:
        is_sender_mod = False
        command_name = inspect.currentframe().f_back.f_code.co_name
        self.logger.info(f"ctx.message.author.is_mod???: {ctx.message.author.is_mod}")
        if not ctx.message.author.is_mod:
            await ctx.send(f"Oops, the {command_name} is for mods...")
        elif ctx.message.author.is_mod:
            is_sender_mod = True
        return is_sender_mod

    async def _send_hello_world(self):
        # Say hello to the chat 
        if self.config.twitch_bot_gpt_hello_world == True:
            gpt_prompt_text = self.config.hello_assistant_prompt
            assistant_name = 'chatforme'
            thread_name = 'chatformemsgs'
            tts_voice = self.config.tts_voice_default

            replacements_dict = {
                "helloworld_message_wordcount":self.config.helloworld_message_wordcount,
                'twitch_bot_display_name':self.config.twitch_bot_display_name,
                'twitch_bot_channel_name':self.config.twitch_bot_channel_name,
                'param_in_text':'variable_from_scope'
                }

            # Add a executeTask to the queue
            task = CreateExecuteThreadTask(
                thread_name=thread_name,
                assistant_name=assistant_name,
                thread_instructions=gpt_prompt_text,
                replacements_dict=replacements_dict,
                tts_voice=tts_voice
            ).to_dict()
            self.logger.debug(f"Task to add to queue: {task}")
        
            await self.gpt_thread_mgr.add_task_to_queue(thread_name, task)

    @twitch_commands.command(name='getstats', aliases=("p_getstats", "stats"))
    async def get_command_stats(self, ctx):
        table_id = self.config.talkzillaai_usertransactions_table_id
        stats_text = self.bq_uploader.fetch_interaction_stats_as_text(table_id)
        await self._send_channel_message_wrapper(stats_text)

    @twitch_commands.command(name='what', aliases=("m_what"))
    async def what(self, ctx):
        gpt_prompt_text = self.config.botears_prompt
        assistant_name = 'chatforme'
        thread_name = 'chatformemsgs'
        tts_voice = self.config.tts_voice_default

        #add format for concat with filename in trext format       
        path = os.path.join(self.config.botears_audio_path)
        filename = self.config.botears_audio_filename + ".wav"
        filepath = os.path.join(path, filename)
  
        await self.bot_ears.save_last_n_seconds(
            filepath=filepath, 
            saved_seconds=self.config.botears_save_length_seconds
            )
        
        # Translate the audio to text
        text = await self.s2t_service.convert_audio_to_text(filepath)
        self.logger.info(f"Transcribed text: {text}")

        # Add to thread (This is done to send the voice message to the GPT thread)
        task = AddMessageTask(thread_name, text).to_dict()
        await self.gpt_thread_mgr.add_task_to_queue(thread_name, task)

        replacements_dict = {
            "wordcount_medium": self.config.wordcount_medium,
            "botears_questioncomment": text
        }

        # Add a executeTask to the queue
        task = CreateExecuteThreadTask(
            thread_name=thread_name,
            assistant_name=assistant_name,
            thread_instructions=gpt_prompt_text,
            replacements_dict=replacements_dict,
            tts_voice=tts_voice
        ).to_dict()
        self.logger.debug(f"Task to add to queue: {task}")

        await self.gpt_thread_mgr.add_task_to_queue(thread_name, task)

    @twitch_commands.command(name='commands', aliases=["p_commands"])
    async def showcommands(self, ctx):
        results = set()
        commands_info = self._get_commands()
        
        for command in commands_info:
            self.logger.info(f"Command Object: {command}")
            
            command_name = command['name']
            aliases = command['aliases']

            if aliases is None:
                self.logger.info(f"No aliases for command: {command_name}")
                continue

            # Normalize aliases to a list
            if isinstance(aliases, str):
                aliases = [aliases]
            elif isinstance(aliases, tuple):
                aliases = list(aliases)

            for alias in aliases:
                self.logger.info(f"Alias: {alias}")
                
                if not alias.startswith("m_"):
                    results.add(command_name)
                    
        self.logger.info(f"Results: {results}")
        
        results_string = ', '.join(sorted(results))
        self.logger.info(f"Results string: {results_string}")
        
        await self._send_channel_message_wrapper(f"Commands include: {results_string}")

    @twitch_commands.command(name='specs', aliases=("p_specs"))
    async def discord(self, ctx):
        await self._send_channel_message_wrapper("i7-13700K || RTX 4070 Ti OC || 64GB DDR5 6400MHz || ASUS ROG Strix Z790-F")

    @twitch_commands.command(name='discord', aliases=("p_discord"))
    async def discord(self, ctx):
        await self._send_channel_message_wrapper("This is the discord channel, come say hello but, ughhhhh, don't mind the mess: https://discord.gg/XdHSKaMFvG")

    @twitch_commands.command(name='updatetodo', aliases=("m_updatetodo"))
    async def updatetodo(self, ctx, *args):
            is_sender_mod = await self._check_mod(ctx)

            if is_sender_mod == True:
                updated_string = ' '.join(args)
                self.config.gpt_todo_prompt = updated_string
                self.logger.info(f"updated todo list: {updated_string}")

    @twitch_commands.command(name='todo', aliases=("p_todo"))
    async def todo(self, ctx):
        replacements_dict = {
            "wordcount_short": self.config.wordcount_short,
            'param_in_text':'variable_from_scope'
            }
        gpt_prompt_text = self.config.gpt_todo_prompt_prefix + self.config.gpt_todo_prompt + self.config.gpt_todo_prompt_suffix

        todo = await self.gpt_chatcompletion.make_singleprompt_gpt_response(
            prompt_text=gpt_prompt_text, 
            replacements_dict=replacements_dict
            )
        
        return todo

    async def _chatforme_main(self, text_input_from_user=None):
        assistant_name = 'chatforme'
        thread_name = 'chatformemsgs'
        tts_voice = self.config.tts_voice_randomfact
        chatforme_prompt = self.config.chatforme_prompt

        if text_input_from_user is None:
            text_input_from_user = 'none'

        replacements_dict = {
            "twitch_bot_display_name":self.config.twitch_bot_display_name,
            "num_bot_responses":self.config.num_bot_responses,
            "users_in_messages_list_text":self.message_handler.users_in_messages_list_text,
            "wordcount_medium":self.config.wordcount_medium,
            "bot_operatorname":self.config.twitch_bot_operatorname,
            "twitch_bot_channel_name":self.config.twitch_bot_channel_name,
            "text_input_from_user":text_input_from_user,
        }

        # Add a executeTask to the queue
        task = CreateExecuteThreadTask(
            thread_name=thread_name,
            assistant_name=assistant_name,
            thread_instructions=chatforme_prompt,
            replacements_dict=replacements_dict,
            tts_voice=tts_voice
        ).to_dict()
        self.logger.debug(f"Task to add to queue: {task}")

        await self.gpt_thread_mgr.add_task_to_queue(thread_name, task)
        
    @twitch_commands.command(name='chat', aliases=("p_chat"))
    async def chatforme(self, ctx=None, *args):
        if args is None or len(args) == 0:
            text_input_from_user = 'none'
        else:
            text_input_from_user = ' '.join(args)

        self.loop.create_task(self._chatforme_main(text_input_from_user)) #does a task really need to be created here?  Maybe should use process task method instead

    @twitch_commands.command(name='last_message', aliases=("m_last_message",))
    async def last_message(self, ctx, *args):
        # Parse the command arguments
        is_sender_mod = await self._check_mod(ctx)

        if is_sender_mod == True and args is not None:
            if len(args) == 1:
                user_name = args[0]
            else:
                self.logger.warning(f"Incorrect number of arguments ({len(args)} were sent, only 1 required)")

            last_message = self.bq_uploader.fetch_user_chat_history_from_bq(
                user_login=user_name,
                interactions_table_id=self.config.talkzillaai_usertransactions_table_id,
                users_table_id=self.config.talkzillaai_userdata_table_id,
                limit=1
                )
            
            # Get content variable from the last message json string
            last_message = json.loads(last_message)
            last_message_content = last_message[0]['content']

        else:
            self.logger.info(f"Sender is not a mod or incorrect number of arguments {len(args)} were sent, 1 is required.")
        
        await self._send_channel_message_wrapper(f"Last message from {user_name}: {last_message_content}")

    @twitch_commands.command(name='vc', aliases=("m_vc"))
    async def vc(self, message, *args):
        self.vibechecker_interactions_counter = 0
        self.is_vibecheck_loop_active = True
    
        # Extract the bot/checker/checkee (important players) in the convo
        message_to_check = -2

        while True:  # Keep checking messages until a valid one is found
            try:
                most_recent_message = self.message_handler.all_msg_history_gptdict[message_to_check]['content']
                name_start_pos = most_recent_message.find('<<<') + 3
                name_end_pos = most_recent_message.find('>>>', name_start_pos)
                self.vibecheckee_username = most_recent_message[name_start_pos:name_end_pos]

                # Break the loop if the vibecheckee is not 'xyz'
                users_excluded_from_vibecheck = [
                    self.config.twitch_bot_username, 
                    self.config.twitch_bot_display_name,
                    self.config.twitch_bot_operatorname,
                    self.config.twitch_bot_channel_name
                    ]
                if self.vibecheckee_username not in users_excluded_from_vibecheck:
                    break

                # Move to the previous message if the current vibecheckee is 'xyz'
                message_to_check -= 1

            except IndexError:
                # Handle the case where there are no more messages to check
                await self._send_channel_message_wrapper(f"You're the only one here, {self.config.twitch_bot_display_name}")
                return

        # Proceed with the rest of the function after finding a valid vibecheckee
        self.vibechecker_username = message.author.name
        self.vibecheckbot_username = self.config.twitch_bot_display_name

        self.vibechecker_players = {
            'vibecheckee_username': self.vibecheckee_username,
            'vibechecker_username': self.vibechecker_username,
            'vibecheckbot_username': self.vibecheckbot_username
        }

        # Start the vibecheck service and then the session
        self.vibecheck_service = VibeCheckService(
            message_handler=self.message_handler,
            gpt_assistant_mgr=self.gpt_assistant_manager,
            gpt_thread_mgr=self.gpt_thread_mgr,
            gpt_response_mgr=self.gpt_response_manager,
            chatforme_service=self.chatforme_service,
            vibechecker_players=self.vibechecker_players,
            send_channel_message=self._send_channel_message_wrapper
            )
        self.vibecheck_service.start_vibecheck_session()

    async def stop_vibechecker_loop(self) -> None:
        self.is_vibecheck_loop_active = False
        self.vibechecker_task.cancel()
        try:
            await self.vibechecker_task  # Await the task to ensure it's fully cleaned up
        except asyncio.CancelledError:
            self.logger.debug("(message from stop_vibechecker_loop()) -- Task was cancelled and cleanup is complete")

    #NOTE: Start story should always have it's own unique thread every time it is run
    @twitch_commands.command(name='startstory', aliases=("p_startstory"))
    async def startstory(self, message, *args):
        self.logger.info(f"Starting story, self.ouat_counter={self.ouat_counter}")
        if self.ouat_counter == 0:
            self.message_handler.ouat_msg_history.clear()

            # Extract the user requested plotline and if '' or ' ', etc. then set to None
            user_requested_plotline_str = ' '.join(args)
            if user_requested_plotline_str in ['', ' ', None]:
                user_requested_plotline_str = None

            # Randomly select voice/tone/style/theme from list, set replacements dictionary
            self.current_story_voice = self.config.tts_voice_story

            writing_tone_values = list(self.config.writing_tone.values())
            self.selected_writing_tone = random.choice(writing_tone_values)

            writing_style_values = list(self.config.writing_style.values())
            self.selected_writing_style = random.choice(writing_style_values)

            theme_values = list(self.config.writing_theme.values())
            self.selected_theme = random.choice(theme_values)

            # Log the story details
            self.logger.info(f"...A story was started by {message.author.name} ({message.author.id})")
            self.logger.info(f"...thread_name and assistant_name: {self.ouat_thread_name}, {self.ouat_assistant_name}")
            self.logger.info(f"...user_requested_plotline_str: {user_requested_plotline_str}")
            self.logger.info(f"...current_story_voice: {self.current_story_voice}")
            self.logger.info(f"...selected_writing_tone: {self.selected_writing_tone}")
            self.logger.info(f"...selected_writing_style: {self.selected_writing_style}")
            self.logger.info(f"...selected_theme: {self.selected_theme}")

            if user_requested_plotline_str is not None:
                self.ouat_counter += 1
                submitted_plotline = user_requested_plotline_str      
                self.logger.info(f"Scheduler-2: This is the submitted plotline: {submitted_plotline}")
                send_channel_message = True

            elif user_requested_plotline_str is None:
                submitted_plotline = self.article_generator.fetch_random_article_content(article_char_trunc=1000)                    
                self.logger.info(f"Scheduler-2: This is the random article plotline: {submitted_plotline}")
                send_channel_message = False

            gpt_prompt_text = self.config.story_user_opening_scene_summary_prompt + " " + self.config.storyteller_storysuffix_prompt    
            replacements_dict = {
                "user_requested_plotline":submitted_plotline,
                "wordcount_short":self.config.wordcount_short,
                "wordcount_medium":self.config.wordcount_medium,
                "wordcount_long":self.config.wordcount_long,
                "ouat_counter":self.ouat_counter,
                "max_ouat_counter":self.config.ouat_story_max_counter,
                }

            # Add executeTask to the queue
            task = CreateExecuteThreadTask(
                thread_name=self.ouat_thread_name,
                assistant_name=self.ouat_assistant_name,
                thread_instructions=gpt_prompt_text,
                replacements_dict=replacements_dict,
                tts_voice=self.current_story_voice,
                send_channel_message=send_channel_message
                ).to_dict()
            self.logger.debug(f"Task to add to queue: {task}")

            # Add the bullet list to the 'ouatmsgs' thread via queue
            await self.gpt_thread_mgr.add_task_to_queue(self.ouat_thread_name, task)
            self.is_ouat_loop_active = True
            self.logger.info(f"The story has been initiated with the following storytelling parameters:\n-{self.selected_writing_style}\n-{self.selected_writing_tone}\n-{self.selected_theme}")
            self.logger.info(f"OUAT submitted_plotline: '{submitted_plotline}'")
            self.logger.warning(f"End of start story command: The OUAT counter is currently at {self.ouat_counter} (ouat_story_max_counter={self.config.ouat_story_max_counter})")

    async def ouat_storyteller_task(self):
        self.article_generator = ArticleGeneratorClass.ArticleGenerator(rss_link=self.config.newsarticle_rss_feed)
        self.article_generator.fetch_articles()

        #This is the while loop that generates the occurring GPT response
        while True:
            if self.is_ouat_loop_active is False:
                self.logger.warning(f"startstory task: self.is_ouat_loop_active is False, self.ouat_counter={self.ouat_counter}")
                await asyncio.sleep(self.loop_sleep_time)
                continue

            if self.is_ouat_loop_active is True:
                self.logger.warning(f"startstory task: self.is_ouat_loop_active is True")
                self.ouat_counter += 1
                self.logger.warning(f"self.ouat_counter={self.ouat_counter} (after increment)")
                self.logger.info(f"OUAT details: Starting cycle #{self.ouat_counter} of the OUAT Storyteller") 

                #storystarter
                if self.ouat_counter == 1:
                    self.logger.warning(f"self.ouat_counter check1: self.ouat_counter={self.ouat_counter}")
                    gpt_prompt_final = self.config.storyteller_storystarter_prompt

                #storyprogressor
                elif self.ouat_counter <= self.config.ouat_story_progression_number:
                    self.logger.warning(f"self.ouat_counter check2: self.ouat_counter={self.ouat_counter}")
                    gpt_prompt_final = self.config.storyteller_storyprogressor_prompt

                #storyfinisher
                elif self.ouat_counter < self.config.ouat_story_max_counter:
                    self.logger.warning(f"self.ouat_counter check3: self.ouat_counter={self.ouat_counter}")
                    gpt_prompt_final = self.config.storyteller_storyfinisher_prompt

                #storyender
                elif self.ouat_counter >= self.config.ouat_story_max_counter:
                    self.logger.warning(f"self.ouat_counter check4: self.ouat_counter={self.ouat_counter}")
                    gpt_prompt_final = self.config.storyteller_storyender_prompt

                # Combine prefix and final article content
                gpt_prompt_final = self.config.storyteller_storysuffix_prompt + " " + gpt_prompt_final
                self.logger.info(f"OUAT gpt_prompt_final: '{gpt_prompt_final}'")

                replacements_dict = {
                    "wordcount_short":self.config.wordcount_short,
                    "wordcount_long":self.config.wordcount_long,
                    'twitch_bot_display_name':self.config.twitch_bot_display_name,
                    'num_bot_responses':self.config.num_bot_responses,
                    'writing_style': self.selected_writing_style,
                    'writing_tone': self.selected_writing_tone,
                    'writing_theme': self.selected_theme,
                    "ouat_counter":self.ouat_counter,
                    "max_ouat_counter":self.config.ouat_story_max_counter,
                    'param_in_text':'variable_from_scope'
                    }

                # Add a executeTask to the queue
                task = CreateExecuteThreadTask(
                    thread_name=self.ouat_thread_name,
                    assistant_name=self.ouat_assistant_name,
                    thread_instructions=gpt_prompt_final,
                    replacements_dict=replacements_dict,
                    tts_voice=self.current_story_voice
                ).to_dict()
                self.logger.debug(f"Task to add to queue: {task}")

                await self.gpt_thread_mgr.add_task_to_queue(self.ouat_thread_name, task)

            if self.ouat_counter >= self.config.ouat_story_max_counter:
                self.logger.warning(f"self.ouat_counter check5: self.ouat_counter={self.ouat_counter}")
                await self.stop_ouat_loop()
                continue
            else:
                await asyncio.sleep(int(self.config.ouat_message_recurrence_seconds))

    @twitch_commands.command(name='addtostory', aliases=("p_addtostory"))
    async def add_to_story_ouat(self, ctx,  *args):
        self.ouat_counter = self.config.ouat_story_progression_number
        
        author=ctx.message.author.name
        gpt_prompt_text = ' '.join(args)
        prompt_text_with_prefix = f"{self.config.ouat_prompt_addtostory_prefix}:'{gpt_prompt_text}'"
        
        #workflow1: get gpt_ready_msg_dict and add message to message history        
        gpt_ready_msg_dict = self.message_handler.create_gpt_message_dict_from_strings(
            content=prompt_text_with_prefix,
            role='user',
            name=author
            )
        self.message_handler.ouat_msg_history.append(gpt_ready_msg_dict)

        # Add the bullet list to the 'ouatmsgs' thread via queue
        thread_name = 'ouatmsgs'
        task = AddMessageTask(thread_name, gpt_prompt_text).to_dict()

        await self.gpt_thread_mgr.add_task_to_queue(thread_name, task)
        self.logger.info(f"A story was added to by {ctx.message.author.name} ({ctx.message.author.id}): '{gpt_prompt_text}'")

    @twitch_commands.command(name='extendstory', aliases=("p_extendstory"))
    async def extend_story(self, ctx, *args) -> None:
        self.ouat_counter = self.config.ouat_story_progression_number
        self.logger.info(f"Story extension requested by {ctx.message.author.name} ({ctx.message.author.id}), self.ouat_counter has been set to {self.ouat_counter}")

    @twitch_commands.command(name='stopstory', aliases=("m_stopstory"))
    async def stop_story(self, ctx):
        await self.stop_ouat_loop()
        await self._send_channel_message_wrapper("to be continued...")

    @twitch_commands.command(name='endstory', aliases=("m_endstory"))
    async def endstory(self, ctx):
        self.ouat_counter = self.config.ouat_story_max_counter
        self.logger.warning(f"Story is being forced to end by {ctx.message.author.name} ({ctx.message.author.id}), self.ouat_counter is at {self.ouat_counter}")

    async def stop_ouat_loop(self) -> None:
        self.is_ouat_loop_active = False
        self.ouat_counter = 0
        self.logger.warning(f"OUAT loop has been stopped, self.ouat_counter has been reset to {self.ouat_counter}")
        self.message_handler.ouat_msg_history.clear()

    async def _factcheck_main(self, text_input_from_user=None):

        assistant_name = 'factchecker'
        thread_name = 'chatformemsgs'
        tts_voice = self.config.tts_voice_randomfact

        if text_input_from_user is None:
            text_input_from_user = "none"

        # select a random number/item based on the number of items inside of self.config.factchecker_prompts.values()
        random_number = random.randint(0, len(self.config.factchecker_prompts.values())-1)
        chatforme_factcheck_prompt = list(self.config.factchecker_prompts.values())[random_number]

        replacements_dict = {
            "twitch_bot_display_name":self.config.twitch_bot_display_name,
            "num_bot_responses":self.config.num_bot_responses,
            "users_in_messages_list_text":self.message_handler.users_in_messages_list_text,
            "wordcount":self.config.wordcount_medium,
            "bot_operatorname":self.config.twitch_bot_operatorname,
            "twitch_bot_channel_name":self.config.twitch_bot_channel_name,
            "factual_claim_input":text_input_from_user
        }

        try:
            
            # Add a executeTask to the queue
            task = CreateExecuteThreadTask(
                thread_name=thread_name,
                assistant_name=assistant_name,
                thread_instructions=chatforme_factcheck_prompt,
                replacements_dict=replacements_dict,
                tts_voice=tts_voice
            ).to_dict()
            self.logger.debug(f"Task to add to queue: {task}")

            await self.gpt_thread_mgr.add_task_to_queue(thread_name, task)

        except Exception as e:
            return self.logger.error(f"error with chatforme in twitchbotclass: {e}")

    @twitch_commands.command(name='factcheck', aliases=("p_factcheck"))
    async def factcheck(self, ctx, *args):
        if args is not None and len(args) > 0:
            text_input_from_user = ' '.join(args)
        else:
            text_input_from_user = 'none'
        self.loop.create_task(self._factcheck_main(text_input_from_user))

    @twitch_commands.command(name='update_config', aliases=("m_update_config",))
    async def update_config(self, ctx, *args):
        
        is_sender_mod = await self._check_mod(ctx)
        if not is_sender_mod:
            self.logger.debug("Requester was not a mod... nothing happened")
            return

        # Validate input
        if len(args) < 2:
            await self.channel.send("Usage: !update_config [config_var] [value]")
            return

        # Extract the config variable and value from the command arguments
        config_var = args[0]
        value = ' '.join(args[1:])

        # If the value is true or false, make sure that the setatt() method is used to set the value to a boolean
        if value.lower() in ['true', 'false']:
            self.logger.debug(f"Value '{value}' is a boolean. It will be set as a boolean.")
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False

        # If the value is an integer, make sure that the setatt() method is used to set the value to an integer
        try:
            value = int(value)
        except ValueError:
            self.logger.debug(f"Value '{value}' could not be converted to an integer. It will be set as a string.")   
            pass

        # # Dictionary of allowed config variables and their expected types
        # config_vars = {
        #     'tts_include_voice': str,
        #     'randomfact_selected_game': str,
        #     'another_config_var': int,  # Add more config variables as needed
        # }

        # # Check if the config variable is allowed
        # if config_var not in config_vars:
        #     await self.channel.send(f"Invalid config variable: {config_var}")
        #     return

        # Attempt to update the config variable
        try:
            # expected_type = config_vars[config_var]
            # if expected_type == int:
            #     value = int(value)
            # elif expected_type == str:
            #     value = str(value)
            # # Add more type checks as needed

            setattr(self.config, config_var, value)
            self.logger.info(f"Config variable '{config_var}' has been updated to '{value}'")
        # except ValueError:
        #     await self.channel.send(f"Invalid value type for '{config_var}'. Expected {expected_type.__name__}.")
        except Exception as e:
            self.logger.error(f"Error occurred in !update_config: {e}")
            await self.channel.send("No change made, see log for details.")

    def _randomfact_category_picker(self, data: dict):
        # Pick a random category (like 'historicalContexts', 'categories', etc.)
        topic = random.choice(list(data.keys()))
        
        # Pick a random item within the selected category
        subtopic = random.choice(data[topic])
        
        return topic, subtopic

    def _is_valid_json(self, response: str) -> bool:
        try:
            json.loads(response)
            return True
        except json.JSONDecodeError:
            return False
        
    async def randomfact_task(self):

        def format_chat_history(chat_history: list[dict]) -> str:
            formatted_messages = []
            for message in chat_history:
                role = message.get('role', 'unknown')
                content = message.get('content', '')
                formatted_messages.append(f"Role: {role}, Content: {content}")
            return "\n".join(formatted_messages)
        
        while True:
            await adjustable_sleep_task.adjustable_sleep_task(self.config, 'randomfact_sleeptime')

            # Prompt set in os.env on .bat file run
            selected_prompt = self.config.randomfact_prompt
            assistant_name = 'random_fact'
            thread_name = 'chatformemsgs'
            tts_voice = self.config.tts_voice_randomfact

            # Correctly pass the topics data structure to _randomfact_category_picker
            topic, subtopic = self._randomfact_category_picker(data=self.config.randomfact_topics)
            area, subarea = self._randomfact_category_picker(data=self.config.randomfact_areas)

            #Generate random character from a to z
            random_character_a_to_z = random.choice('abcdefghijklmnopqrstuvwxyz')

            # Make singleprompt_gpt_response
            conversation_director_prompt = self.config.randomfact_conversation_director
            chat_history = format_chat_history(self.message_handler.all_msg_history_gptdict)
            replacements_dict={
                'wordcount_short':self.config.wordcount_short,
                'twitch_bot_display_name':self.config.twitch_bot_display_name,
                'randomfact_topic':topic,
                'randomfact_subtopic':subtopic,
                'area':area,
                'subarea':subarea,
                'param_in_text':'variable_from_scope',
                'chat_history':chat_history
                }
            
            # Do not make this a task, as clutter in the task queue could make randomfact behave unpredictably
            response_text = await self.gpt_chatcompletion.make_singleprompt_gpt_response(
                prompt_text=conversation_director_prompt,
                replacements_dict=replacements_dict,
                model=self.config.gpt_model_davinci
                )

            # Strip backticks and json tag if present
            response_text = response_text.strip().strip('```').strip('json').strip()

            if self._is_valid_json(response_text):
                response = json.loads(response_text)
                if response['response_type'] == 'respond':
                    selected_prompt = self.config.randomfact_prompt
                elif response['response_type'] == 'fact':
                    selected_prompt = self.config.randomfact_prompt
                else:
                    self.logger.warning(f"Error occurred in 'randomfact_task': response.response_type is not 'respond' or 'fact'")
                    selected_prompt = self.config.randomfact_prompt
            else:
                self.logger.warning("Received response is not valid JSON")
                # Handle the case where the response is not valid JSON
                selected_prompt = "An error occurred while processing the response."

            self.logger.debug(f"Thread Instructions (selected prompt): {selected_prompt[0:50]}")
            self.logger.debug(f"Selected topic: {topic}, Selected subtopic: {subtopic}")
            self.logger.debug(f"Selected area: {area}, Selected subarea: {subarea}")
            self.logger.debug(f"Selected random_character_a_to_z: {random_character_a_to_z}")
            self.logger.debug(f"Selected random voice: {tts_voice}")

            replacements_dict = {
                "wordcount_short":self.config.wordcount_short,
                'twitch_bot_display_name':self.config.twitch_bot_display_name,
                'randomfact_topic':topic,
                'randomfact_subtopic':subtopic,
                'area':area,
                'subarea':subarea,
                'random_character_a_to_z':random_character_a_to_z,
                'selected_game':self.config.randomfact_selected_game,
                'param_in_text':'variable_from_scope'
                }
            self.logger.debug(f"Replacements dict: {replacements_dict}")
            
            # Add a executeTask to the queue
            task = CreateExecuteThreadTask(
                thread_name=thread_name,
                assistant_name=assistant_name,
                thread_instructions=selected_prompt,
                replacements_dict=replacements_dict,
                tts_voice=tts_voice
            ).to_dict()
            self.logger.debug(f"Task to add to queue: {task}")

            await self.gpt_thread_mgr.add_task_to_queue(thread_name, task)