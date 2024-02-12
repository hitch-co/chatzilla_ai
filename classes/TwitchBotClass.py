import asyncio
from twitchio.ext import commands as twitch_commands

import random
import re
import os
import inspect

from my_modules.my_logging import create_logger
from my_modules import utils
from my_modules import gpt

from classes.ConsoleColoursClass import bcolors, printc
from classes import ArticleGeneratorClass

from services.VibecheckService import VibeCheckService
from services.NewUsersService import NewUsersService
from services.ChatForMeService import ChatForMeService
from services.AudioService import AudioService
from services.BotEars import BotEars
from services.SpeechToTextService import SpeechToTextService

runtime_logger_level = 'DEBUG'
class Bot(twitch_commands.Bot):
    loop_sleep_time = 4

    def __init__(
            self, 
            TWITCH_BOT_ACCESS_TOKEN, 
            config, 
            gpt_client, 
            bq_uploader, 
            tts_client,  
            message_handler
            ):
        super().__init__(
            token=TWITCH_BOT_ACCESS_TOKEN,
            name=config.twitch_bot_username,
            prefix='!',
            initial_channels=[config.twitch_bot_channel_name],
            nick = 'chatzilla_ai'
            #NOTE/QUESTION:what other variables should be set here?
        )

        #setup logger
        self.logger = create_logger(
            dirname='log', 
            logger_name='logger_TwitchBotClass', 
            debug_level=runtime_logger_level,
            mode='w',
            stream_logs=True,
            encoding='UTF-8'
            )

        #TODO: Next up, make this work...
        self.config = config
        # dependencies instances
        self.gpt_client = gpt_client
        self.bq_uploader = bq_uploader 
        self.tts_client = tts_client
        self.message_handler = message_handler

        # TODO: Could be a good idea to inject these dependencies into the services
        # instantiate the ChatForMeService
        self.chatforme_service = ChatForMeService(
            tts_client=self.tts_client,
            send_channel_message=self.send_channel_message_wrapper
            )

        # TODO: Could be a good idea to inject these dependencies into the services
        # instantiate the NewUsersService
        self.newusers_service = NewUsersService(
            message_handler=self.message_handler,
            chatforme_service=self.chatforme_service
        )

        # TODO: Could be a good idea to inject these dependencies into the services
        # instantiate the AudioService and BotEars
        self.audio_service = AudioService(volume=self.config.tts_volume)
        device_name = "Microphone (Yeti Classic), MME"
        self.bot_ears = BotEars(
            config=self.config,
            device_name=device_name,
            #event_loop=self.loop, # Removed 2024-02-10
            buffer_length_seconds=self.config.botears_buffer_length_seconds
            )

        # TODO: Could be a good idea to inject these dependencies into the services
        # Instantiate the speech to text service
        self.s2t_service = SpeechToTextService()
        
        #Taken from app authentication class()
        self.TWITCH_BOT_ACCESS_TOKEN = TWITCH_BOT_ACCESS_TOKEN

        # required config/files
        self.command_spellecheck_terms = utils.load_json(
            self,
            dir_path=self.config.config_dirpath,
            file_name=self.config.command_spellcheck_terms_filename
            )
        
        #Google Service Account Credentials & BQ Table IDs
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.config.google_application_credentials_file
        
        #Get historic stream viewers
        self.historic_users_at_start_of_session = self.bq_uploader.fetch_users(self.config.talkzillaai_userdata_table_id)

        #Set default loop state
        self.is_ouat_loop_active = False
        self.is_vibecheck_loop_active = False

        #counters
        self.ouat_counter = 0

        #NOTE: ARGUABLY DO NOT NEED TO INITIALIZE THESE HERE   
        #vibecheck params
        self.vibechecker_max_interaction_count = self.config.vibechecker_max_interaction_count
        self.formatted_gpt_vibecheck_prompt = self.config.formatted_gpt_vibecheck_prompt
        self.formatted_gpt_viberesult_prompt = self.config.formatted_gpt_viberesult_prompt
        self.vibechecker_max_interaction_count = self.config.vibechecker_max_interaction_count

        #NOTE: ARGUABLY DO NOT NEED TO INITIALIZE THESE HERE
        # BQ Table IDs
        self.userdata_table_id=self.config.talkzillaai_userdata_table_id
        self.usertransactions_table_id=self.config.talkzillaai_usertransactions_table_id
        
        #NOTE: ARGUABLY DO NOT NEED TO INITIALIZE THESE HERE
        # Response wordcounts
        self.wordcount_short = self.config.wordcount_short
        self.wordcount_medium = self.config.wordcount_medium
        self.wordcount_long = self.config.wordcount_long

        #NOTE: ARGUABLY DO NOT NEED TO INITIALIZE THESE HERE
        self.broadcaster_id = self.config.twitch_broadcaster_author_id
        self.moderator_id = self.config.twitch_bot_moderator_id
        self.twitch_bot_client_id = self.config.twitch_bot_client_id

        #NOTE: ARGUABLY DO NOT NEED TO INITIALIZE THESE HERE
        #newusers params
        self.newusers_sleep_time = self.config.newusers_sleep_time 

    async def event_ready(self):
        self.channel = self.get_channel(self.config.twitch_bot_channel_name)
        print(f'TwitchBot ready | {self.config.twitch_bot_username} (nick:{self.nick})')

        # initialize the event loop
        self.loop = asyncio.get_event_loop()

        # start OUAT loop
        self.loop.create_task(self.ouat_storyteller())

        # Start bot ears streaming
        self.loop.create_task(self.bot_ears.start_stream())

        # start newusers loop
        self.loop.create_task(self.send_message_to_new_users_task())

        # Say hello to the chat 
        if self.config.gpt_hello_world == True:
            replacements_dict = {
                "helloworld_message_wordcount":self.config.helloworld_message_wordcount,
                'twitch_bot_display_name':self.config.twitch_bot_display_name,
                'twitch_bot_channel_name':self.config.twitch_bot_channel_name,
                'param_in_text':'variable_from_scope'
                }
            prompt_text = self.config.hello_assistant_prompt

            gpt_response = await self.chatforme_service.make_singleprompt_gpt_response(
                prompt_text=prompt_text, 
                replacements_dict=replacements_dict,
                incl_voice='yes'
                )
            self.logger.debug(f"This is the final gpt response for the hello_world: {gpt_response}")

    async def event_message(self, message):

        def clean_message_content(content, command_spellings):
            for correct_command, misspellings in command_spellings.items():
                for misspelled in misspellings:
                    # Using a regular expression to match whole commands only
                    pattern = r'(^|\s)' + re.escape(misspelled) + r'(\s|$)'
                    content = re.sub(pattern, r'\1' + correct_command + r'\2', content)
            return content

        self.logger.info("-------------------------------------")
        self.logger.info("------ Msg received, processing -----")
        self.logger.info("-------------------------------------")
        self.logger.debug(message)
        self.logger.info(f"message.content: {message.content}")
        
        # 1. This is the control flow function for creating message histories
        self.message_handler.add_to_appropriate_message_history(message)
        
        # 2. Process the message through the vibecheck service         
        if hasattr(self, 'vibecheck_service') and self.vibecheck_service is not None:
            self.vibecheck_service.process_vibecheck_message(self.message_handler.message_history_raw[-1]['name'])
        
        # 3. Get chatter data, store in queue, generate query for sending to BQ
        channel_viewers_queue_query = self.bq_uploader.get_process_queue_create_channel_viewers_query(
            table_id=self.userdata_table_id,
            bearer_token=self.TWITCH_BOT_ACCESS_TOKEN
            )

        # 4. Send the data to BQ when queue is full.  Clear queue when done
        if len(self.message_handler.message_history_raw)>=5:
            self.bq_uploader.send_queryjob_to_bq(query=channel_viewers_queue_query)            
            viewer_interaction_records = self.bq_uploader.generate_bq_user_interactions_records(records=self.message_handler.message_history_raw)
            
            self.bq_uploader.send_recordsjob_to_bq(
                table_id=self.usertransactions_table_id,
                records=viewer_interaction_records
                )
            self.logger.debug("These are the viewer_interaction_records:")
            self.logger.debug(viewer_interaction_records[0:2])

            self.logger.info(f"Succesfully sent {len(viewer_interaction_records)} records to BQ.  Clearing message_history_raw and channel_viewers_queue.")
            self.message_handler.message_history_raw.clear()
            self.bq_uploader.channel_viewers_queue.clear()

        # 5. self.handle_commands runs through bot commands
        if message.author is not None:
            message.content = clean_message_content(
                message.content,
                self.command_spellecheck_terms
                )
            await self.handle_commands(message)

        self.logger.info("-------------------------------------") 
        self.logger.info("----- ...finished processing msg ----")
        self.logger.info("-------------------------------------\n")        

    async def send_channel_message_wrapper(self, message):
        await self.channel.send(message)

    async def check_mod(self, ctx, command) -> bool:
        is_sender_mod = False
        command_name = inspect.currentframe().f_back.f_code.co_name
        if not ctx.author.is_mod:
            await ctx.send(f"Oops, the {command_name} is for mods...")
        else:
            is_sender_mod = True
        return is_sender_mod

    @twitch_commands.command(name='what')
    async def what(self, ctx):
        #add format for concat with filename in trext format       
        path = os.path.join(self.config.botears_audio_path)
        filename = self.config.botears_audio_filename + ".wav"
        filepath = os.path.join(path, filename)
  
        await self.bot_ears.save_last_n_seconds(
            filepath=filepath, 
            saved_seconds=self.config.botears_save_length_seconds
            )
        
        # Translate the audio to text
        text = self.s2t_service.convert_audio_to_text(filepath)

        # feed the text to the GPT model for a response
        prompt_text = self.config.botears_prompt
        replacements_dict = {
            "wordcount_medium": self.wordcount_medium,
            "botears_questioncomment": text
        }
        await self.chatforme_service.make_msghistory_gpt_response(
            prompt_text=prompt_text,
            replacements_dict=replacements_dict,
            msg_history=self.message_handler.chatforme_msg_history,
            incl_voice='yes'
        )

    @twitch_commands.command(name='commands')
    async def showcommands(self, ctx):
        await self.send_channel_message_wrapper("Commands include: !what, !chat, !todo, !startstory, !addtostory, !extendstory")

    @twitch_commands.command(name='discord')
    async def discord(self, ctx):
        await self.send_channel_message_wrapper("ughhhhh, don't mind the mess: https://discord.gg/XdHSKaMFvG")


    @twitch_commands.command(name='updatetodo')
    async def updatetodo(self, ctx, *args):
            is_sender_mod = self.check_mod(ctx)

            if is_sender_mod == True:
                updated_string = ' '.join(args)
                self.config.gpt_todo_prompt = updated_string
                self.logger.info(f"updated todo list: {updated_string}")

    @twitch_commands.command(name='todo')
    async def todo(self, ctx):
        replacements_dict = {
            "wordcount_short": self.wordcount_short,
            'param_in_text':'variable_from_scope'
            }
        prompt_text = self.config.gpt_todo_prompt_prefix + self.config.gpt_todo_prompt + self.config.gpt_todo_prompt_suffix

        await self.chatforme_service.make_singleprompt_gpt_response(
            prompt_text=prompt_text, 
            replacements_dict=replacements_dict,
            incl_voice='yes'
            )

    @twitch_commands.command(name='chat')
    async def chatforme(self, ctx):
        """
        A Twitch bot command that interacts with OpenAI's GPT API.
        It takes in chat messages from the Twitch channel and forms a GPT prompt for a chat completion API call.
        """

        # Select random voice from the list of voices
        tts_voice = random.choice(random.choice(list(self.config.tts_voices.values())))

        # Extract usernames from previous chat messages stored in chatforme_msg_history.
        users_in_messages_list_text = self.message_handler.get_string_of_users(usernames_list=self.message_handler.users_in_messages_list)

        #Select prompt from argument, build the final prompt textand format replacements
        chatforme_prompt = self.config.chatforme_prompt
        replacements_dict = {
            "twitch_bot_display_name":self.config.twitch_bot_display_name,
            "num_bot_responses":self.config.num_bot_responses,
            "users_in_messages_list_text":users_in_messages_list_text,
            "wordcount_medium":self.config.wordcount_medium,
            "bot_operatorname":self.config.twitch_bot_operatorname,
            "twitch_bot_channel_name":self.config.twitch_bot_channel_name
        }

        try:
            await self.chatforme_service.make_msghistory_gpt_response(
                prompt_text=chatforme_prompt,
                replacements_dict=replacements_dict,
                msg_history=self.message_handler.chatforme_msg_history,
                voice_name=tts_voice
            )
            return self.logger.info("chatforme has run successfully.")
        except Exception as e:
            return self.logger.error(f"error with chatforme in twitchbotclass: {e}")

    @twitch_commands.command(name='vc')
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
                await self.send_channel_message_wrapper("No valid user to be vibechecked, try again after they send a message")
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
            vibechecker_players=self.vibechecker_players,
            send_channel_message=self.send_channel_message_wrapper
            )
        self.vibecheck_service.start_vibecheck_session()

    @twitch_commands.command(name='startstory')
    async def startstory(self, message, *args):
        self.ouat_counter += 1

        if self.ouat_counter == 1:
            self.message_handler.ouat_msg_history.clear()
            user_requested_plotline_str = ' '.join(args)
            self.current_story_voice = random.choice(random.choice(list(self.config.tts_voices.values())))
            
            # Randomly select tone/style/theme from list, set replacements dictionary
            writing_tone_values = list(self.config.writing_tone.values())
            self.selected_writing_tone = random.choice(writing_tone_values)

            writing_style_values = list(self.config.writing_style.values())
            self.selected_writing_style = random.choice(writing_style_values)

            theme_values = list(self.config.writing_theme.values())
            self.selected_theme = random.choice(theme_values)

            self.logger.info(f"A story was started by {message.author.name} ({message.author.id})")
            self.logger.info(f"selected_writing_tone: {self.selected_writing_tone}")
            self.logger.info(f"selected_writing_style: {self.selected_writing_style}")
            self.logger.info(f"selected_theme: {self.selected_theme}")

            ####################################
            ####################################
            if user_requested_plotline_str:
                #
                user_requested_plotline_gptlistdict = self.chatforme_service.make_string_gptlistdict(
                    prompt_text = user_requested_plotline_str, 
                    prompt_text_role='user'
                    )

                replacements_dict = {
                    "user_requested_plotline":user_requested_plotline_str,
                    "wordcount_short":self.wordcount_short
                    }
                
                create_bullet_list_promp_text = gpt.prompt_text_replacement(
                    gpt_prompt_text=self.config.story_user_bullet_list_summary_prompt + self.config.storyteller_storysuffix_prompt,
                    replacements_dict = replacements_dict
                    )
                
                bullet_list_and_user_plotline_listdict = self.chatforme_service.combine_msghistory_and_prompttext(
                    prompt_text = create_bullet_list_promp_text,
                    prompt_text_role='user',
                    prompt_text_name=message.author.name,
                    msg_history_list_dict=user_requested_plotline_gptlistdict,
                    combine_messages=False,
                    output_new_list=False
                    )
                
                new_plotline = gpt.openai_gpt_chatcompletion(
                    max_characters=2000,
                    messages_dict_gpt=bullet_list_and_user_plotline_listdict
                    )
                
                new_plotline_gptlistdict = self.chatforme_service.make_string_gptlistdict(
                    prompt_text = new_plotline, 
                    prompt_text_role='user'
                    )

                self.random_article_content_plot_summary = await self.chatforme_service.make_msghistory_gpt_response(
                    prompt_text=self.config.storyteller_storystarter_prompt,
                    replacements_dict=replacements_dict,
                    msg_history=new_plotline_gptlistdict,
                    incl_voice='yes',
                    voice_name=self.current_story_voice
                    )  

                self.logger.debug(f"This is the user_requested_plotline_str: {user_requested_plotline_str}")
                self.logger.debug(f"This is the create_bullet_list_promp_text: {create_bullet_list_promp_text}")
                self.logger.debug(f"This is the new_plotline: {new_plotline}")
                self.logger.debug(f"This is the self.random_article_content_plot_summary: {self.random_article_content_plot_summary}")

            ####################################
            ####################################
            else:
                self.random_article_content = self.article_generator.fetch_random_article_content(article_char_trunc=500)                    

                article_content_plotline_gptlistdict = self.chatforme_service.make_string_gptlistdict(
                    prompt_text = self.random_article_content, 
                    prompt_text_role='user'
                    )
                
                replacements_dict = {
                    "random_article_content":self.random_article_content,
                    "user_requested_plotline":article_content_plotline_gptlistdict,
                    "wordcount_short":self.wordcount_short,
                    }
                create_bullet_list_promp_text = gpt.prompt_text_replacement(
                    gpt_prompt_text=self.config.story_article_bullet_list_summary_prompt,
                    replacements_dict = replacements_dict
                    )

                # combine the random_article_content_gptlistdict with the prompt 
                #  text into a new list[dict]
                self.story_bulleted_plotline = self.chatforme_service.combine_msghistory_and_prompttext(
                    prompt_text = create_bullet_list_promp_text,
                    prompt_text_role = 'user',
                    prompt_text_name = message.author.name,
                    msg_history_list_dict = article_content_plotline_gptlistdict,
                    output_new_list = True
                    )
                    
                #TODO: Probably shouldn't be sending an output and maybe just generating a GPT message dictionary
                self.random_article_content_plot_summary = await self.chatforme_service.make_msghistory_gpt_response(
                    prompt_text=self.config.storyteller_storystarter_prompt,
                    replacements_dict=replacements_dict,
                    msg_history = self.story_bulleted_plotline,
                    incl_voice='yes',
                    voice_name=self.current_story_voice
                )      
                self.logger.debug(f"This is the article_content_plotline_gptlistdict: {article_content_plotline_gptlistdict}")
                self.logger.debug(f"This is the create_bullet_list_promp_text: {create_bullet_list_promp_text}")
                self.logger.debug(f"This is the self.story_bulleted_plotline: {self.story_bulleted_plotline}")
                self.logger.debug(f"There was no user_requested_plotline_str, so the prompt_text is: {self.config.storyteller_storystarter_prompt}")
                self.logger.debug(f"This is the final response, aka the self.random_article_content_plot_summary: {self.random_article_content_plot_summary}")

            self.is_ouat_loop_active = True

            # printc(f"A story was started by {message.author.name} ({message.author.id})", bcolors.WARNING)
            # printc(f"This is the article_content_plotline_gptlistdict: {article_content_plotline_gptlistdict}", bcolors.OKBLUE)
            # printc(f"This is the create_bullet_list_promp_text: {create_bullet_list_promp_text}", bcolors.OKBLUE)
            # printc(f"This is the self.story_bulleted_plotline: {self.story_bulleted_plotline}", bcolors.OKBLUE)
            # printc(f"There was no user_requested_plotline_str, so the prompt_text is: {self.config.storyteller_storystarter_prompt}, bcolors.OKBLUE")
            # printc(f"This is the final response, aka the self.random_article_content_plot_summary: {self.random_article_content_plot_summary}, bcolors.OKBLUE")

    @twitch_commands.command(name='addtostory')
    async def add_to_story_ouat(self, ctx,  *args):
        author=ctx.message.author.name
        prompt_text = ' '.join(args)
        prompt_text_prefix = f"{self.config.ouat_prompt_addtostory_prefix}:'{prompt_text}'"
        
        #workflow1: get gpt_ready_msg_dict and add message to message history        
        gpt_ready_msg_dict = self.message_handler._create_gpt_message_dict_from_strings(
            content=prompt_text_prefix,
            role='user',
            name=author
            )
        self.message_handler.ouat_msg_history.append(gpt_ready_msg_dict)

        self.logger.info(f"A story was added to by {ctx.message.author.name} ({ctx.message.author.id}): '{prompt_text}'")

    @twitch_commands.command(name='extendstory')
    async def extend_story(self, ctx, *args) -> None:
        self.ouat_counter = self.config.ouat_story_progression_number
        self.logger.info(f"Story extension requested by {ctx.message.author.name} ({ctx.message.author.id}), self.ouat_counter has been set to {self.ouat_counter}", bcolors.WARNING)

    @twitch_commands.command(name='stopstory')
    async def stop_story(self, ctx):
        await self.send_channel_message_wrapper("to be continued...")
        await self.stop_ouat_loop()

    @twitch_commands.command(name='endstory')
    async def endstory(self, ctx):
        self.ouat_counter = self.config.ouat_story_max_counter
        self.logger.info(f"Story is being forced to end by {ctx.message.author.name} ({ctx.message.author.id}), counter is at {self.ouat_counter}")

    async def send_message_to_new_users_task(self):

        #TODO: Implement a way of doing this on command as well, making use of 
        # a newly created new_users_loop_active var. 
        while True:
            await asyncio.sleep(self.newusers_sleep_time)

            #TODO: get_current_users_in_session should be a method of the 
            # NewUsersService or a twitch specific service
            current_users_list = await self.message_handler.get_current_users_in_session(
                bearer_token = self.TWITCH_BOT_ACCESS_TOKEN,
                broadcaster_id = self.broadcaster_id,
                moderator_id = self.moderator_id,
                twitch_bot_client_id = self.twitch_bot_client_id
                )
            
            await self.newusers_service.send_message_to_new_users(
                historic_users_list = self.historic_users_at_start_of_session,
                current_users_list = current_users_list
            )

    async def stop_vibechecker_loop(self) -> None:
        self.is_vibecheck_loop_active = False
        self.vibechecker_task.cancel()
        try:
            await self.vibechecker_task  # Await the task to ensure it's fully cleaned up
        except asyncio.CancelledError:
            self.logger.debug("(message from stop_vibechecker_loop()) -- Task was cancelled and cleanup is complete")

    async def stop_ouat_loop(self) -> None:
        self.is_ouat_loop_active = False
        self.ouat_counter = 0

        utils.write_msg_history_to_file(
            logger=self.logger,
            msg_history=self.message_handler.ouat_msg_history, 
            variable_name_text='ouat_msg_history',
            dirname='log/ouat_story_history'
            )
        self.message_handler.ouat_msg_history.clear()

    async def ouat_storyteller(self):
        self.article_generator = ArticleGeneratorClass.ArticleGenerator(rss_link=self.config.newsarticle_rss_feed)
        self.article_generator.fetch_articles()

        #This is the while loop that generates the occurring GPT response
        while True:
            if self.is_ouat_loop_active is False:
                await asyncio.sleep(self.loop_sleep_time)
                continue
                      
            else:
                self.logger.info(f"OUAT details: Starting cycle #{self.ouat_counter} of the OUAT Storyteller") 

                #storystarter
                if self.ouat_counter == 1:
                    gpt_prompt_final = self.config.storyteller_storystarter_prompt

                #storyprogressor
                if self.ouat_counter <= self.config.ouat_story_progression_number:
                    gpt_prompt_final = self.config.storyteller_storyprogressor_prompt

                #storyfinisher
                elif self.ouat_counter < self.config.ouat_story_max_counter:
                    gpt_prompt_final = self.config.storyteller_storyfinisher_prompt

                #storyender
                elif self.ouat_counter == self.config.ouat_story_max_counter:
                    gpt_prompt_final = self.config.storyteller_storyender_prompt
                                                    
                elif self.ouat_counter > self.config.ouat_story_max_counter:
                    await self.stop_ouat_loop()
                    continue

                # Combine prefix and meat
                gpt_prompt_final = self.config.storyteller_storysuffix_prompt + " " + gpt_prompt_final

                self.logger.info(f"The self.ouat_counter is currently at {self.ouat_counter} (self.config.ouat_story_max_counter={self.config.ouat_story_max_counter})")
                self.logger.info(f"The story has been initiated with the following storytelling parameters:\n-{self.selected_writing_style}\n-{self.selected_writing_tone}\n-{self.selected_theme}")
                self.logger.info(f"OUAT gpt_prompt_final: '{gpt_prompt_final}'")

                replacements_dict = {
                    "wordcount_short":self.wordcount_short,
                    'twitch_bot_display_name':self.config.twitch_bot_display_name,
                    'num_bot_responses':self.config.num_bot_responses,
                    'rss_feed_article_plot':self.random_article_content_plot_summary,
                    'writing_style': self.selected_writing_style,
                    'writing_tone': self.selected_writing_tone,
                    'writing_theme': self.selected_theme,
                    'param_in_text':'variable_from_scope' #for future use
                    }
  
                gpt_response = await self.chatforme_service.make_msghistory_gpt_response(
                    prompt_text = gpt_prompt_final, 
                    replacements_dict=replacements_dict,
                    msg_history=self.message_handler.ouat_msg_history,
                    incl_voice='yes',
                    voice_name=self.current_story_voice
                    )
                self.logger.info(f"OUAT gpt_response for iteration #{self.ouat_counter} of the OUAT Storyteller has been generated successfully: '{gpt_response}'")
                self.ouat_counter += 1

            await asyncio.sleep(int(self.config.ouat_message_recurrence_seconds))
