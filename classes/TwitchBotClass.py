runtime_logger_level = 'INFO'

import asyncio
from twitchio.ext import commands as twitch_commands

import random
import os

from my_modules.gpt import openai_gpt_chatcompletion
from my_modules.gpt import prompt_text_replacement, combine_msghistory_and_prompttext
from my_modules.gpt import ouat_gpt_response_cleanse, chatforme_gpt_response_cleanse, botthot_gpt_response_cleanse

from my_modules.my_logging import create_logger
from my_modules.twitchio_helpers import get_string_of_users
from my_modules.config import load_yaml, load_env
from my_modules.text_to_speech import generate_t2s_object, play_t2s_object, play_local_mp3
from my_modules import utils

from classes.ConsoleColoursClass import bcolors, printc
from classes import ArticleGeneratorClass
from classes.CustomExceptions import BotFeatureNotEnabledException
from classes.MessageHandlerClass import MessageHandler
from classes.BQUploaderClass import TwitchChatBQUploader
from classes.PromptHandlerClass import PromptHandler
from classes.ArgsConfigManagerClass import ArgsConfigManager
from classes import GPTTextToSpeechClass

class Bot(twitch_commands.Bot):
    loop_sleep_time = 4

    def __init__(self, TWITCH_BOT_ACCESS_TOKEN, yaml_data):
        super().__init__(
            token=TWITCH_BOT_ACCESS_TOKEN,
            name=yaml_data['twitch-app']['twitch_bot_username'],
            prefix='!',
            initial_channels=[yaml_data['twitch-app']['twitch_bot_channel_name']],
            nick = 'chatforme_bot'
            #NOTE/QUESTION:what other variables should be set here?
        )

        #instantiate amessage handler class
        self.message_handler = MessageHandler()
        self.args_config = ArgsConfigManager()
        self.twitch_chat_uploader = TwitchChatBQUploader() #TODO should be instantiated with a access token

        #setup logger
        self.logger = create_logger(
            dirname='log', 
            logger_name='logger_BotClass', 
            debug_level=runtime_logger_level,
            mode='a',
            stream_logs=True,
            encoding='UTF-8'
            )

        #load cofiguration
        self.yaml_data = self.run_configuration()
        
        #Google Service Account Credentials
        google_application_credentials_file = yaml_data['twitch-ouat']['google_service_account_credentials_file']
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_application_credentials_file

        #BQ Table IDs
        self.userdata_table_id=self.yaml_data['twitch-ouat']['talkzillaai_userdata_table_id']
        self.usertransactions_table_id=self.yaml_data['twitch-ouat']['talkzillaai_usertransactions_table_id']

        #TTS Details
        self.tts_data_folder = yaml_data['openai-api']['tts_data_folder']
        self.tts_file_name = yaml_data['openai-api']['tts_file_name']
        
        #TTS Client
        self.tts_client = GPTTextToSpeechClass.GPTTextToSpeech(
            output_filename=self.tts_file_name,
            output_dirpath=self.tts_data_folder
            )

        #Taken from app authentication class()
        self.TWITCH_BOT_ACCESS_TOKEN = TWITCH_BOT_ACCESS_TOKEN

        #Set default loop state
        self.is_ouat_loop_active = False  # controls if the loop should runZ

        #counters
        self.ouat_counter = 0

    def run_configuration(self) -> dict:

        #load yaml/env
        self.yaml_data = load_yaml(yaml_filename='config.yaml', yaml_dirname="config")
        load_env(env_filename=self.yaml_data['env_filename'], env_dirname=self.yaml_data['env_dirname'])

        #Twitch Bot Details
        self.twitch_bot_channel_name = self.yaml_data['twitch-app']['twitch_bot_channel_name']
        self.twitch_bot_username = self.yaml_data['twitch-app']['twitch_bot_username']

        #Eleven Labs / OpenAI
        self.ELEVENLABS_XI_API_KEY = os.getenv('ELEVENLABS_XI_API_KEY')
        self.ELEVENLABS_XI_VOICE = os.getenv('ELEVENLABS_XI_VOICE')
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

        #runtime arguments
        self.args_include_sound = str.lower(self.args_config.include_sound)
        self.args_include_automsg = str.lower(self.args_config.include_automsg)
        self.args_automsg_prompt_list_name = str.lower(self.args_config.prompt_list_automsg)

        #TODO self.args_include_chatforme = str.lower(args.include_chatforme)
        self.args_chatforme_prompt_name = str.lower(self.args_config.prompt_list_chatforme)
        self.args_botthot_prompt_name = 'botthot'
        self.args_include_ouat = str.lower(self.args_config.include_ouat)        
        self.args_ouat_prompt_name = str.lower(self.args_config.prompt_list_ouat)

        #News Article Feed/Prompts
        self.newsarticle_rss_feed = self.yaml_data['twitch-ouat']['newsarticle_rss_feed']
        self.ouat_news_article_summary_prompt = self.yaml_data['ouat_prompts']['ouat_news_article_summary_prompt'] 

        #OUAT base prompt and start/progress/end story prompts
        self.gpt_ouat_prompt_begin = self.yaml_data['ouat_prompts'][self.args_ouat_prompt_name]
        self.ouat_prompt_startstory = self.yaml_data['ouat_prompts']['ouat_prompt_startstory']
        self.ouat_prompt_progression = self.yaml_data['ouat_prompts']['ouat_prompt_progression']
        self.ouat_prompt_endstory = self.yaml_data['ouat_prompts']['ouat_prompt_endstory']
        self.ouat_prompt_addtostory_prefix = self.yaml_data['ouat_prompts']['ouat_prompt_addtostory_prefix']

        #OUAT Progression flow / Config
        self.ouat_message_recurrence_seconds = self.yaml_data['ouat_message_recurrence_seconds']
        self.ouat_story_progression_number = self.yaml_data['ouat_story_progression_number']
        self.ouat_story_max_counter = self.yaml_data['ouat_story_max_counter']
        self.ouat_wordcount = self.yaml_data['ouat_wordcount']

        #Generic config itrems
        self.num_bot_responses = self.yaml_data['num_bot_responses']
        
        #AUTOMSG
        self.automsg_prompt_lists = self.yaml_data['automsg_prompt_lists']
        self.automsg_prompt_list = self.automsg_prompt_lists[self.args_automsg_prompt_list_name]
        self.automsg_prompt_prefix = self.yaml_data['automsg_prompt_prefix']

        #GPT Prompt
        self.gpt_prompt = ''  

        # Load settings and configurations from a YAML file
        # TODO: Can be moved into the load_configurations() function
        self.chatforme_message_wordcount = str(self.yaml_data['chatforme_message_wordcount'])
        self.formatted_gpt_chatforme_prompt_prefix = str(self.yaml_data['formatted_gpt_chatforme_prompt_prefix'])
        self.formatted_gpt_chatforme_prompt_suffix = str(self.yaml_data['formatted_gpt_chatforme_prompt_suffix'])
        self.formatted_gpt_chatforme_prompts = self.yaml_data['formatted_gpt_chatforme_prompts']
        self.logger.info("Configuration attributes loaded/refreshed from YAML/env variables")  
        
        return self.yaml_data 

    #Executes once the bot is ready
    async def event_ready(self):
        self.channel = self.get_channel(self.twitch_bot_channel_name)
        print(f'Ready | {self.twitch_bot_username} (nick:{self.nick})')
        args_list = [
            "args_include_automsg",
            "args_automsg_prompt_list_name",
            "args_include_ouat",
            "args_ouat_prompt_name",
            "args_chatforme_prompt_name",
            "args_include_sound"
            ]
        await self.print_runtime_params(args_list=args_list)

        #start loop
        self.loop.create_task(self.ouat_storyteller())

    #Excecutes everytime a message is received
    async def event_message(self, message):
        self.logger.info("--------- Message received ---------")
        
        #This is the control flow function for creating message histories
        self.message_handler.add_to_appropriate_message_history(message)
        
        #Get chatter data, store in queue, generate query for sending to BQ
        channel_viewers_queue_query = self.twitch_chat_uploader.get_process_queue_create_channel_viewers_query(
            table_id=self.userdata_table_id,
            bearer_token=self.TWITCH_BOT_ACCESS_TOKEN)

        #Send the data to BQ
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
                table_id=self.usertransactions_table_id,
                records=viewer_interaction_records
                )

            #clear the queues
            self.message_handler.message_history_raw.clear()
            self.twitch_chat_uploader.channel_viewers_queue.clear()
            self.logger.info("message history and users in viewers queue sent to BQ and cleared")

        # self.handle_commands runs through bot commands
        if message.author is not None:
            await self.handle_commands(message)

    #controls ouat_storyteller()
    async def start_ouat_storyteller_msg_loop(self):
        self.is_ouat_loop_active = True
        self.run_configuration()
        if not any([self.args_include_automsg == 'yes', self.args_include_ouat == 'yes']):
            self.logger.error("Neither automsg or ouat enabled with app argument")
            raise BotFeatureNotEnabledException("Neither automsg or ouat enabled with app argument")

    @twitch_commands.command(name='startstory')
    async def startstory(self, message, *args):
        if self.ouat_counter == 0:
            user_requested_plotline = ' '.join(args)

            # Capture writing tone/style/theme and randomly select one item from each list
            writing_tone_values = list(self.yaml_data['ouat-writing-parameters']['writing_tone'].values())
            self.selected_writing_tone = random.choice(writing_tone_values)

            writing_style_values = list(self.yaml_data['ouat-writing-parameters']['writing_style'].values())
            self.selected_writing_style = random.choice(writing_style_values)

            theme_values = list(self.yaml_data['ouat-writing-parameters']['theme'].values())
            self.selected_theme = random.choice(theme_values)

            # Fetch random article
            self.random_article_content = self.article_generator.fetch_random_article_content(article_char_trunc=300)                    
            
            # Populate text replacement
            replacements_dict = {"random_article_content":self.random_article_content,
                                 "user_requested_plotline":user_requested_plotline}
            self.random_article_content = prompt_text_replacement(
                gpt_prompt_text=self.ouat_news_article_summary_prompt,
                replacements_dict=replacements_dict
                )
            
            gpt_ready_dict = PromptHandler.create_gpt_message_dict_from_strings(
                self,
                content = self.random_article_content,
                role = 'user',
                name = self.twitch_bot_username
            )
            gpt_ready_list_dict = [gpt_ready_dict]

            self.logger.debug("THIS IS GPT_READ_LIST_DICT:")
            self.logger.debug(gpt_ready_list_dict)

            self.random_article_content_prompt_summary = openai_gpt_chatcompletion(
                messages_dict_gpt=gpt_ready_list_dict, 
                OPENAI_API_KEY=self.OPENAI_API_KEY, 
                max_characters=1200
                )

            self.logger.info("this is the random_article_content_prompt_summary:")
            self.logger.info(self.random_article_content_prompt_summary)

            await self.start_ouat_storyteller_msg_loop()
            
            printc(f"A story was started by {message.author.name} ({message.author.id})", bcolors.WARNING)
            printc(f"Theme: {self.selected_theme}", bcolors.OKBLUE)
            printc(f"Writing Tone: {self.selected_writing_tone}", bcolors.OKBLUE)
            printc(f"Writing Style: {self.selected_writing_style}", bcolors.OKBLUE)

    @twitch_commands.command(name='addtostory')
    async def add_to_story_ouat(self, ctx,  *args):
        author=ctx.message.author.name
        prompt_text = ' '.join(args)
        prompt_text_prefix = f"{self.ouat_prompt_addtostory_prefix}:'{prompt_text}'"
        gpt_ready_msg_dict = PromptHandler.create_gpt_message_dict_from_strings(
            self,
            content=prompt_text_prefix,
            role='user',
            name=author
            )
        self.message_handler.ouat_temp_msg_history.append(gpt_ready_msg_dict)
        
        printc(f"A story was added to by {ctx.message.author.name} ({ctx.message.author.id}): '{prompt_text}'", bcolors.WARNING)

    @twitch_commands.command(name='extendstory')
    async def extend_story(self, ctx, *args) -> None:
        self.ouat_counter = 2
        printc(f"Story extension requested by {ctx.message.author.name} ({ctx.message.author.id}), self.ouat_counter has been set to {self.ouat_counter}", bcolors.WARNING)

    @twitch_commands.command(name='stopstory')
    async def stop_story(self, ctx):
        await self.channel.send("ToBeCoNtInUeD")
        await self.stop_loop()

    @twitch_commands.command(name='endstory')
    async def endstory(self, ctx):
        self.ouat_counter = self.ouat_story_max_counter
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
        self.ouat_counter = 0

    async def print_runtime_params(self, args_list=None):        
        self.logger.info("These are the runtime params for this bot:")
        for arg in args_list:
            self.logger.info(f"{arg}: {getattr(self, arg)}")

    async def ouat_storyteller(self):
        #self.yaml_data = self.run_configuration()
    
        #load article links (prepping for reading random article)
        if self.args_include_ouat == 'yes' and self.args_ouat_prompt_name.startswith('newsarticle'):
            self.article_generator = ArticleGeneratorClass.ArticleGenerator(rss_link=self.newsarticle_rss_feed)
            self.article_generator.fetch_articles()
        else: 
            self.logger.warning("Neither self.args_include_ouat or self.args_ouat_prompt_name conditions were met")

        #This is the while loop that generates the occurring GPT response
        while True:
            if self.is_ouat_loop_active is False:
                await asyncio.sleep(self.loop_sleep_time)
                continue
                      
            else:
                self.logger.info(f"The story has been initiated with the following storytelling parameters:\n-{self.selected_writing_style}\n-{self.selected_writing_tone}\n-{self.selected_theme}")
                replacements_dict = {"ouat_wordcount":self.ouat_wordcount,
                                     'twitch_bot_username':self.twitch_bot_username,
                                     'num_bot_responses':self.num_bot_responses,
                                     'rss_feed_article_plot':self.random_article_content_prompt_summary,
                                     'writing_style': self.selected_writing_style,
                                     'writing_tone': self.selected_writing_tone,
                                     'writing_theme': self.selected_theme,
                                     'param_in_text':'variable_from_scope'} #for future use}

                #######################################
                if self.args_include_ouat == 'yes':
                    self.logger.debug(f"ouat_counter is: {self.ouat_counter}")

                    if self.ouat_counter == 0:
                        gpt_prompt_final = prompt_text_replacement(gpt_prompt_text=self.ouat_prompt_startstory,
                                                                   replacements_dict=replacements_dict)         

                    if self.ouat_counter < self.ouat_story_progression_number:
                        gpt_prompt_final = prompt_text_replacement(gpt_prompt_text=self.gpt_ouat_prompt_begin,
                                                                   replacements_dict=replacements_dict)         

                    elif self.ouat_counter < self.ouat_story_max_counter:
                        gpt_prompt_final = prompt_text_replacement(gpt_prompt_text=self.ouat_prompt_progression,
                                                                   replacements_dict=replacements_dict) 
                        
                    elif self.ouat_counter == self.ouat_story_max_counter:
                        gpt_prompt_final = prompt_text_replacement(gpt_prompt_text=self.ouat_prompt_endstory,
                                                                   replacements_dict=replacements_dict)
                                                        
                    elif self.ouat_counter > self.ouat_story_max_counter:
                        await self.stop_loop()
                        continue
                
                else: 
                    self.logger.error("Neither automsg or ouat enabled with app startup argument")

                self.logger.info(f"The self.ouat_counter is currently at {self.ouat_counter}")
                self.logger.debug(f'OUAT gpt_prompt_final: {gpt_prompt_final}')

                messages_dict_gpt = combine_msghistory_and_prompttext(prompt_text=gpt_prompt_final,
                                                                      prompt_text_role='system',
                                                                      msg_history_list_dict=self.message_handler.ouat_temp_msg_history,
                                                                      combine_messages=False)

                ##################################################################################
                gpt_response_text = openai_gpt_chatcompletion(messages_dict_gpt=messages_dict_gpt, 
                                                                OPENAI_API_KEY=self.OPENAI_API_KEY,
                                                                max_attempts=3)
                gpt_response_clean = ouat_gpt_response_cleanse(gpt_response_text)

                if self.ouat_counter == self.ouat_story_max_counter:
                    self.logger.info(f"That was the final message (self.ouat_counter == {self.ouat_story_max_counter})")  

                self.logger.debug(f"This is the messages_dict_gpt (self.ouat_counter = {self.ouat_counter}:")
                self.logger.debug(messages_dict_gpt)
                self.logger.info(f"FINAL gpt_response_clean (type: {type(gpt_response_clean)}): \n{gpt_response_clean}")  

                if self.args_include_sound == 'yes':
                    # Generate speech object and create .mp3:
                    output_filename = 'ouat_'+self.tts_file_name
                    self.tts_client.workflow_t2s(
                        text_input=gpt_response_clean,
                        voice_name='shimmer',
                        output_dirpath=self.tts_data_folder,
                        output_filename=output_filename
                        )
                
                #send twitch message and generate/play local mp3 if applicable
                await self.channel.send(gpt_response_clean)

                if self.args_include_sound == 'yes':
                    play_local_mp3(
                        dirpath=self.tts_data_folder, 
                        filename=output_filename
                        )                

                self.ouat_counter += 1   

            await asyncio.sleep(int(self.ouat_message_recurrence_seconds))

    @twitch_commands.command(name='chatforme')
    async def chatforme(self, ctx):
        """
        A Twitch bot command that interacts with OpenAI's GPT API.
        It takes in chat messages from the Twitch channel and forms a GPT prompt for a chat completion API call.
        """
        self.run_configuration()
        request_user_name = ctx.message.author.name

        # Extract usernames from previous chat messages stored in chatforme_temp_msg_history.
        users_in_messages_list_text = get_string_of_users(usernames_list=self.message_handler.users_in_messages_list)

        #Select prompt from argument, build the final prompt textand format replacements
        formatted_gpt_chatforme_prompt = self.formatted_gpt_chatforme_prompts[self.args_chatforme_prompt_name]
        chatgpt_chatforme_prompt = self.formatted_gpt_chatforme_prompt_prefix + formatted_gpt_chatforme_prompt + self.formatted_gpt_chatforme_prompt_suffix
        replacements_dict = {
            "twitch_bot_username":self.twitch_bot_username,
            "num_bot_responses":self.num_bot_responses,
            "request_user_name":request_user_name,
            "users_in_messages_list_text":users_in_messages_list_text,
            "chatforme_message_wordcount":self.chatforme_message_wordcount
        }
        chatgpt_chatforme_prompt = prompt_text_replacement(
            gpt_prompt_text=chatgpt_chatforme_prompt,
            replacements_dict = replacements_dict
            )

        messages_dict_gpt = combine_msghistory_and_prompttext(prompt_text = chatgpt_chatforme_prompt,
                                                              prompt_text_role='system',
                                                              msg_history_list_dict=self.message_handler.chatforme_temp_msg_history,
                                                              combine_messages=False)
        
        # Execute the GPT API call to get the chatbot response
        gpt_response = openai_gpt_chatcompletion(messages_dict_gpt=messages_dict_gpt, 
                                                 OPENAI_API_KEY=self.OPENAI_API_KEY)
        gpt_response_clean = chatforme_gpt_response_cleanse(gpt_response)

        if self.args_include_sound == 'yes':
            # Generate speech object and create .mp3:
            output_filename = 'chatforme_'+self.tts_file_name
            self.tts_client.workflow_t2s(text_input=gpt_response_clean,
                                            voice_name='onyx',
                                        output_dirpath=self.tts_data_folder,
                                        output_filename=output_filename)
        
        #send twitch message and generate/play local mp3 if applicable
        await self.channel.send(gpt_response_clean)

        if self.args_include_sound == 'yes':
            play_local_mp3(
                dirpath=self.tts_data_folder, 
                filename=output_filename
                )

    @twitch_commands.command(name='botthot')
    async def botthot(self, ctx):
        """
        A Twitch bot command that interacts with OpenAI's GPT API.
        It takes in chat messages from the Twitch channel and forms a GPT prompt for a chat completion API call.
        """
        self.run_configuration()
        request_user_name = ctx.message.author.name

        # Extract usernames from previous chat messages stored in chatforme_temp_msg_history.
        users_in_messages_list_text = get_string_of_users(usernames_list=self.message_handler.users_in_messages_list)

        #Select the prompt, build the chatgpt_chatforme_prompt to be added as role: system to the 
        # chatcompletions endpoint
        formatted_gpt_chatforme_prompt = self.formatted_gpt_chatforme_prompts[self.args_botthot_prompt_name]
        chatgpt_chatforme_prompt = self.formatted_gpt_chatforme_prompt_prefix + formatted_gpt_chatforme_prompt + self.formatted_gpt_chatforme_prompt_suffix
        replacements_dict = {
            "twitch_bot_username":self.twitch_bot_username,
            "num_bot_responses":self.num_bot_responses,
            "request_user_name":request_user_name,
            "users_in_messages_list_text":users_in_messages_list_text,
            "chatforme_message_wordcount":self.chatforme_message_wordcount
        }
        chatgpt_chatforme_prompt = prompt_text_replacement(
            gpt_prompt_text=formatted_gpt_chatforme_prompt,
            replacements_dict=replacements_dict
            )

        # # Combine the chat history with the new system prompt to form a list of messages for GPT.
        messages_dict_gpt = combine_msghistory_and_prompttext(prompt_text=chatgpt_chatforme_prompt,
                                                              prompt_text_role='system',
                                                              prompt_text_name='unknown',
                                                              msg_history_list_dict=self.message_handler.chatforme_temp_msg_history,
                                                              combine_messages=False)
        
        # Execute the GPT API call to get the chatbot response
        gpt_response = openai_gpt_chatcompletion(messages_dict_gpt=messages_dict_gpt, OPENAI_API_KEY=self.OPENAI_API_KEY)
        gpt_response_clean = botthot_gpt_response_cleanse(gpt_response)

        if self.args_include_sound == 'yes':
            # Generate speech object and create .mp3:
            output_filename = 'botthot_'+self.tts_file_name
            self.tts_client.workflow_t2s(text_input=gpt_response_clean,
                                            voice_name='onyx',
                                        output_dirpath=self.tts_data_folder,
                                        output_filename=output_filename)
        
        #send twitch message and generate/play local mp3 if applicable
        await self.channel.send(gpt_response_clean)

        if self.args_include_sound == 'yes':
            play_local_mp3(
                dirpath=self.tts_data_folder, 
                filename=output_filename
                )                 