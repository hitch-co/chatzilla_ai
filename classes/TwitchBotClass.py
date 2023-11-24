runtime_logger_level = 'DEBUG'

import asyncio
from twitchio.ext import commands as twitch_commands

import random
import os
import openai
from datetime import datetime

from my_modules.gpt import openai_gpt_chatcompletion
from my_modules.gpt import prompt_text_replacement, combine_msghistory_and_prompttext
from my_modules.gpt import ouat_gpt_response_cleanse, chatforme_gpt_response_cleanse, botthot_gpt_response_cleanse

from my_modules.my_logging import create_logger
from my_modules.twitchio_helpers import get_string_of_users
from my_modules.text_to_speech import play_local_mp3
from my_modules import utils

from classes.ConfigManagerClass import ConfigManager
from classes.ConsoleColoursClass import bcolors, printc
from classes.ArticleGeneratorClass import ArticleGenerator
from classes.MessageHandlerClass import MessageHandler
from classes.BQUploaderClass import TwitchChatBQUploader
from classes.ArgsConfigManagerClass import ArgsConfigManager
from classes import GPTTextToSpeechClass

class Bot(twitch_commands.Bot):
    loop_sleep_time = 4

    #init/config
    def __init__(self, TWITCH_BOT_ACCESS_TOKEN, yaml_data):
        super().__init__(
            token=TWITCH_BOT_ACCESS_TOKEN,
            name=yaml_data['twitch-app']['twitch_bot_username'],
            prefix='!',
            initial_channels=[yaml_data['twitch-app']['twitch_bot_channel_name']],
            nick = 'chatforme_bot'
            #NOTE/QUESTION:what other variables should be set here?
        )

        #setup logger
        self.logger = create_logger(
            dirname='log', 
            logger_name='logger_BotClass', 
            debug_level=runtime_logger_level,
            mode='a',
            stream_logs=True,
            encoding='UTF-8'
            )

        # load args and config
        self.args_config = ArgsConfigManager()

        # Create instance of configmanager
        self.config = ConfigManager(yaml_filepath='.\config', yaml_filename='config.yaml')
        
        # Assigned in twitch_bot.py
        self.TWITCH_BOT_ACCESS_TOKEN = TWITCH_BOT_ACCESS_TOKEN

        # instance of client, thread, and manager
        self.gpt_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        # instance of message handler and BQ uplaoder classeses
        self.message_handler = MessageHandler()
        self.twitch_chat_uploader = TwitchChatBQUploader() #TODO should be instantiated with a access token

        self.tts_client = GPTTextToSpeechClass.GPTTextToSpeech(
            tts_file_name=self.config.tts_file_name,
            tts_data_folder=self.config.tts_data_folder
            )
        
        #Google Service Account Credentials
        google_application_credentials_file = yaml_data['twitch-ouat']['google_service_account_credentials_file']
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_application_credentials_file

        #Set default loop state
        self.is_ouat_loop_active = False

        #counters
        self.ouat_counter = 1

    #twitch built-ins
    async def event_ready(self):
        self.channel = self.get_channel(self.config.twitch_bot_channel_name)
        print(f'TwitchBot ready | {self.config.twitch_bot_username} (nick:{self.nick})')

        #start loop
        self.loop.create_task(self.ouat_storyteller())

    #twitch built-ins
    async def event_message(self, message):
        self.logger.info("--------- Message received ---------")
        
        #This is the control flow function for creating message histories
        self.message_handler.add_to_appropriate_message_history(message)
        
        #Get chatter data, store in queue, generate query for sending to BQ
        channel_viewers_queue_query = self.twitch_chat_uploader.get_process_queue_create_channel_viewers_query(
            table_id=self.config.userdata_table_id,
            bearer_token=self.TWITCH_BOT_ACCESS_TOKEN)

        #Send the data to BQ when queue is full.  Clear queue when done
        if len(self.message_handler.message_history_raw)==5:
            self.logger.debug("channel_viewers_query")
            self.logger.debug(channel_viewers_queue_query)
            
            #execute channel viewers query
            self.twitch_chat_uploader.send_queryjob_to_bq(query=channel_viewers_queue_query)            

            #generate and execute user interaction query
            self.logger.debug("These are the message_history_raw:")
            self.logger.debug(self.message_handler.message_history_raw)
            viewer_interaction_records = self.twitch_chat_uploader.generate_bq_user_interactions_records(records=self.message_handler.message_history_raw)
            self.logger.debug("These are the viewer_interaction_records:")
            self.logger.debug(viewer_interaction_records)

            self.twitch_chat_uploader.send_recordsjob_to_bq(
                table_id=self.config.usertransactions_table_id,
                records=viewer_interaction_records
                )

            #clear the queues
            self.message_handler.message_history_raw.clear()
            self.twitch_chat_uploader.channel_viewers_queue.clear()
            self.logger.info("message history and users in viewers queue sent to BQ and cleared")

        # self.handle_commands runs through bot commands
        if message.author is not None:
            await self.handle_commands(message)

    #commands - startstory
    @twitch_commands.command(name='startstory')
    async def startstory(self, message, *args):
        if self.ouat_counter == 1:
            user_requested_plotline = ' '.join(args)

            # Capture writing tone/style/theme and randomly select one item from each list
            writing_tone_values = list(self.config.writing_tone.values())
            self.selected_writing_tone = random.choice(writing_tone_values)

            writing_style_values = list(self.config.writing_style.values())
            self.selected_writing_style = random.choice(writing_style_values)

            theme_values = list(self.config.writing_theme.values())
            self.selected_writing_theme = random.choice(theme_values)

            # Fetch random article and populate text replacement
            self.random_article_content = self.article_generator.fetch_random_article_content(article_char_trunc=300)                    
            replacements_dict = {"random_article_content":self.random_article_content,
                                 "user_requested_plotline":user_requested_plotline}
            self.random_article_content = prompt_text_replacement(
                gpt_prompt_text=self.config.ouat_news_article_summary_prompt,
                replacements_dict=replacements_dict
                )

            gpt_ready_dict = MessageHandler._create_gpt_message_dict_from_strings(
                self,
                content = self.random_article_content,
                role = 'user',
                name = self.config.twitch_bot_username
            )
            gpt_ready_list_dict = [gpt_ready_dict]

            self.random_article_content_plot_summary = openai_gpt_chatcompletion(
                messages_dict_gpt=gpt_ready_list_dict, 
                max_characters=1200
                )

            self.is_ouat_loop_active = True
            # await self.start_ouat_storyteller_msg_loop()
            
            printc(f"A story was started by {message.author.name} ({message.author.id})", bcolors.WARNING)
            printc(f"random_article_content_plot_summary: {self.random_article_content_plot_summary}", bcolors.OKBLUE)
            printc(f"Theme: {self.selected_writing_theme}", bcolors.OKBLUE)
            printc(f"Writing Tone: {self.selected_writing_tone}", bcolors.OKBLUE)
            printc(f"Writing Style: {self.selected_writing_style}", bcolors.OKBLUE)

    @twitch_commands.command(name='addtostory')
    async def add_to_story_ouat(self, ctx,  *args):
        author=ctx.message.author.name
        prompt_text = ' '.join(args)
        prompt_text_prefix = f"{self.config.ouat_prompt_addtostory_prefix}:'{prompt_text}'"

        #workflow1: get gpt_ready_msg_dict and add message to message history        
        gpt_ready_msg_dict = MessageHandler._create_gpt_message_dict_from_strings(
            self,
            content=prompt_text_prefix,
            role='user',
            name=author
            )
        self.message_handler.ouat_temp_msg_history.append(gpt_ready_msg_dict)

        self.logger.warning(f"A story was added to by {ctx.message.author.name} ({ctx.message.author.id}): '{prompt_text}'")

    @twitch_commands.command(name='extendstory')
    async def extend_story(self, ctx, *args) -> None:
        self.ouat_counter = 2
        printc(f"Story extension requested by {ctx.message.author.name} ({ctx.message.author.id}), self.ouat_counter has been set to {self.ouat_counter}", bcolors.WARNING)

    @twitch_commands.command(name='stopstory')
    async def stop_story(self, ctx):
        await self.channel.send("to be continued...")
        await self.stop_loop()

    @twitch_commands.command(name='endstory')
    async def endstory(self, ctx):
        self.ouat_counter = self.config.ouat_story_max_counter
        printc(f"Story is being forced to end by {ctx.message.author.name} ({ctx.message.author.id}), counter is at {self.ouat_counter}", bcolors.WARNING)

    async def stop_loop(self) -> None:
        self.is_ouat_loop_active = False
        
        utils.write_msg_history_to_file(
            logger=self.logger,
            msg_history=self.message_handler.ouat_temp_msg_history, 
            variable_name_text='ouat_temp_msg_history',
            dirname='log/ouat_story_history'
            )
        self.message_handler.ouat_temp_msg_history.clear()
        self.ouat_counter = 1

    async def print_runtime_params(self, args_list=None):        
        self.logger.info("These are the runtime params for this bot:")
        for arg in args_list:
            self.logger.info(f"{arg}: {getattr(self, arg)}")

    async def ouat_storyteller(self):
        self.article_generator = ArticleGenerator(rss_link=self.config.newsarticle_rss_feed)
        self.article_generator.fetch_articles()

        #This is the while loop that generates the occurring GPT response
        while True:
            if self.is_ouat_loop_active is False:
                await asyncio.sleep(self.loop_sleep_time)
                continue

            else:
                self.logger.warning(f"Starting cycle #{self.ouat_counter} of the OUAT Storyteller") 
                
                #TODO: Turn this into a function up to the 'continue'
                replacements_dict = {"ouat_wordcount":self.config.ouat_wordcount,
                                     'twitch_bot_username':self.config.twitch_bot_username,
                                     'num_bot_responses':self.config.num_bot_responses,
                                     'rss_feed_article_plot':self.random_article_content_plot_summary,
                                     'writing_style': self.selected_writing_style,
                                     'writing_tone': self.selected_writing_tone,
                                     'writing_theme': self.selected_writing_theme,
                                     'param_in_text':'variable_from_scope'} #for future use}

                #storystarter
                if self.ouat_counter == 1:
                    gpt_prompt_final = prompt_text_replacement(gpt_prompt_text=self.config.storyteller_storystarter_prompt,
                                                                replacements_dict=replacements_dict)         
                #storyprogressor
                if self.ouat_counter <= self.config.ouat_story_progression_number:
                    gpt_prompt_final = prompt_text_replacement(gpt_prompt_text=self.config.storyteller_storyprogressor_prompt,
                                                                replacements_dict=replacements_dict)         

                #storyfinisher
                elif self.ouat_counter < self.config.ouat_story_max_counter:
                    gpt_prompt_final = prompt_text_replacement(gpt_prompt_text=self.config.storyteller_storyfinisher_prompt,
                                                                replacements_dict=replacements_dict) 
                #storyender
                elif self.ouat_counter == self.config.ouat_story_max_counter:
                    gpt_prompt_final = prompt_text_replacement(gpt_prompt_text=self.config.storyteller_storyender_prompt,
                                                                replacements_dict=replacements_dict)
                                                    
                elif self.ouat_counter > self.config.ouat_story_max_counter:
                    await self.stop_loop()
                    continue
                
                self.logger.info("OUAT details:")
                self.logger.info(f"The self.ouat_counter is currently at {self.ouat_counter} (self.config.ouat_story_max_counter={self.config.ouat_story_max_counter})")
                self.logger.info(f"The story has been initiated with the following storytelling parameters:\n-{self.selected_writing_style}\n-{self.selected_writing_tone}\n-{self.selected_writing_theme}")
                self.logger.info(f"OUAT gpt_prompt_final: '{gpt_prompt_final}'")
                
                messages_dict_gpt = combine_msghistory_and_prompttext(prompt_text=gpt_prompt_final,
                                                                      prompt_text_role='system',
                                                                      msg_history_list_dict=self.message_handler.ouat_temp_msg_history,
                                                                      combine_messages=False)

                gpt_response_text = openai_gpt_chatcompletion(messages_dict_gpt=messages_dict_gpt, 
                                                                max_attempts=3)
                
                messages_dict_gpt = combine_msghistory_and_prompttext(prompt_text=gpt_prompt_final,
                                                                      prompt_text_role='system',
                                                                      msg_history_list_dict=self.message_handler.ouat_temp_msg_history,
                                                                      combine_messages=False)

                gpt_response_text = openai_gpt_chatcompletion(messages_dict_gpt=messages_dict_gpt,
                                                                max_attempts=3)
                gpt_response_clean = ouat_gpt_response_cleanse(gpt_response_text)

                self.logger.debug(f"This is the messages_dict_gpt:")
                self.logger.debug(messages_dict_gpt)
                self.logger.info(f"FINAL gpt_response_clean (type: {type(gpt_response_clean)}): \n{gpt_response_clean}")  

                if self.config.include_sound == 'yes':
                    # Generate speech object and create .mp3:
                    output_filename = f"ouat_{str(self.ouat_counter)}_{self.config.tts_file_name}"
                    self.tts_client.workflow_t2s(
                        text_input=gpt_response_clean,
                        voice_name='shimmer',
                        tts_data_folder=self.config.tts_data_folder,
                        tts_file_name=output_filename
                        )
                
                #send twitch message and generate/play local mp3 if applicable
                await self.channel.send(gpt_response_clean)

                if self.config.include_sound == 'yes':
                    play_local_mp3(
                        dirpath=self.config.tts_data_folder, 
                        filename=output_filename
                        )                
                self.ouat_counter += 1   

            await asyncio.sleep(int(self.config.ouat_message_recurrence_seconds))

    #commands - chatforme
    @twitch_commands.command(name='chatforme')
    async def chatforme(self, ctx):
        """
        A Twitch bot command that interacts with OpenAI's GPT API.
        It takes in chat messages from the Twitch channel and forms a GPT prompt for a chat completion API call.
        """
        datetime_string = datetime.now().strftime("%Y%m%d_%H%M%S")
        request_user_name = ctx.message.author.name

        # Extract usernames from previous chat messages stored in chatforme_temp_msg_history.
        users_in_messages_list_text = get_string_of_users(usernames_list=self.message_handler.users_in_messages_list)

        #Select prompt from argument, build the final prompt textand format replacements
        formatted_gpt_chatforme_prompt = self.config.formatted_gpt_chatforme_prompts[self.args_config.prompt_list_chatforme]
        chatgpt_chatforme_prompt = self.config.formatted_gpt_chatforme_prompt_prefix+" "+formatted_gpt_chatforme_prompt+" "+self.config.formatted_gpt_chatforme_prompt_suffix
        replacements_dict = {
            "twitch_bot_username":self.config.twitch_bot_username,
            "num_bot_responses":self.config.num_bot_responses,
            "request_user_name":request_user_name,
            "users_in_messages_list_text":users_in_messages_list_text,
            "chatforme_message_wordcount":self.config.chatforme_message_wordcount
        }
        chatgpt_chatforme_prompt = prompt_text_replacement(
            gpt_prompt_text=chatgpt_chatforme_prompt,
            replacements_dict = replacements_dict
            )

        #TODO: GPTAssistant Manager #######################################################################
        messages_dict_gpt = combine_msghistory_and_prompttext(prompt_text = chatgpt_chatforme_prompt,
                                                              prompt_text_role='system',
                                                              msg_history_list_dict=self.message_handler.chatforme_temp_msg_history,
                                                              combine_messages=False)
        
        gpt_response = openai_gpt_chatcompletion(messages_dict_gpt=messages_dict_gpt)
        gpt_response_clean = chatforme_gpt_response_cleanse(gpt_response)

        if self.config.include_sound == 'yes':
            # Generate speech object and create .mp3:
            output_filename = "chatforme_"+"_"+datetime_string+"_"+self.config.tts_file_name
            self.tts_client.workflow_t2s(
                text_input=gpt_response_clean,
                voice_name='onyx',
                tts_data_folder=self.config.tts_data_folder,
                tts_file_name=output_filename
                )
        
        #send twitch message and generate/play local mp3 if applicable
        await self.channel.send(gpt_response_clean)

        if self.config.include_sound == 'yes':
            play_local_mp3(
                dirpath=self.config.tts_data_folder, 
                filename=output_filename
                )

    #commands - botthot
    @twitch_commands.command(name='botthot')
    async def botthot(self, ctx):
        """
        A Twitch bot command that interacts with OpenAI's GPT API.
        It takes in chat messages from the Twitch channel and forms a GPT prompt for a chat completion API call.
        """
        request_user_name = ctx.message.author.name

        # Extract usernames from previous chat messages stored in chatforme_temp_msg_history.
        users_in_messages_list_text = get_string_of_users(usernames_list=self.message_handler.users_in_messages_list)

        #Select the prompt, build the chatgpt_chatforme_prompt to be added as role: system to the 
        # chatcompletions endpoint
        formatted_gpt_chatforme_prompt = self.config.formatted_gpt_botthot_prompts[self.config.prompt_list_name_botthot]
        chatgpt_chatforme_prompt = self.config.formatted_gpt_chatforme_prompt_prefix + formatted_gpt_chatforme_prompt + self.config.formatted_gpt_chatforme_prompt_suffix
        replacements_dict = {
            "twitch_bot_username":self.config.twitch_bot_username,
            "num_bot_responses":self.config.num_bot_responses,
            "request_user_name":request_user_name,
            "users_in_messages_list_text":users_in_messages_list_text,
            "chatforme_message_wordcount":self.config.chatforme_message_wordcount
        }
        chatgpt_chatforme_prompt = prompt_text_replacement(
            gpt_prompt_text=formatted_gpt_chatforme_prompt,
            replacements_dict=replacements_dict
            )

        #TODO: GPTAssistant Manager #######################################################################
        # # Combine the chat history with the new system prompt to form a list of messages for GPT.
        messages_dict_gpt = combine_msghistory_and_prompttext(prompt_text=chatgpt_chatforme_prompt,
                                                              prompt_text_role='system',
                                                              prompt_text_name='unknown',
                                                              msg_history_list_dict=self.message_handler.chatforme_temp_msg_history,
                                                              combine_messages=False)
        
        gpt_response = openai_gpt_chatcompletion(messages_dict_gpt=messages_dict_gpt)
        gpt_response_clean = botthot_gpt_response_cleanse(gpt_response)

        if self.config.include_sound == 'yes':
            # Generate speech object and create .mp3:
            output_filename = 'botthot_'+self.config.tts_file_name
            self.tts_client.workflow_t2s(
                text_input=gpt_response_clean,
                voice_name='onyx',
                tts_data_folder=self.config.tts_data_folder,
                tts_file_name=output_filename
                )
        
        #send twitch message and generate/play local mp3 if applicable
        await self.channel.send(gpt_response_clean)

        if self.config.include_sound == 'yes':
            play_local_mp3(
                dirpath=self.config.tts_data_folder, 
                filename=output_filename
                )                 
            
# Create instance of configmanager
config = ConfigManager(yaml_filepath='.\config', yaml_filename='config.yaml')
config.prompt_list_name_ouat