#Whether or not to refresh flask app live
use_reloader_bool=False
runtime_logger_level = 'DEBUG'

#imports
import asyncio
from twitchio.ext import commands as twitch_commands
from threading import Thread
from flask import Flask, request
import uuid
import re
import requests
import os
import argparse
import random

from my_modules.gpt import openai_gpt_chatcompletion
from my_modules.gpt import prompt_text_replacement, combine_msghistory_and_prompttext
from my_modules.my_logging import my_logger, log_dynamic_dict
from my_modules.twitchio_helpers import get_string_of_users
from my_modules.config import load_yaml, load_env
from my_modules.text_to_speech import generate_t2s_object, play_t2s_object
from my_modules.utils import write_msg_history_to_file

from classes.ConsoleColoursClass import bcolors, printc
from classes import ArticleGeneratorClass
from classes.CustomExceptions import BotFeatureNotEnabledException
from classes.MessageHandlerClass import MessageHandler
from classes.ChatUploaderClass import TwitchChatData
from classes.PromptHandlerClass import PromptHandler

# configure the root logger
root_logger = my_logger(dirname='log', 
                        logger_name='root_logger', 
                        debug_level=runtime_logger_level,
                        mode='a')
root_logger.info("----- This is the start of an app start root log! -----")

#Start the app
app = Flask(__name__)

#Load yaml file & Load and Store keys/tokens from env
#yaml_data = load_yaml(yaml_filename='config.yaml', yaml_dirname="config")
#load_env(env_filename=yaml_data['env_filename'], env_dirname=yaml_data['env_dirname'])

#Placeholder/junk
TWITCH_CHATFORME_BOT_THREAD = None

###############################
class Bot(twitch_commands.Bot):
    loop_sleep_time = 4

    def __init__(self, TWITCH_BOT_ACCESS_TOKEN, yaml_data, env_vars):
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

        #setup logger
        self.logger = my_logger(dirname='log', 
                                logger_name='logger_BotClass', 
                                debug_level=runtime_logger_level,
                                mode='a',
                                stream_logs=False,
                                encoding='UTF-8')

        #May be redundant.  I think I should leave these here but then need to handle
        # Configuration in the bot(run()) section of the script which is outside both classes
        # and thus might need it's own class
        self.yaml_data = yaml_data
        self.env_vars = env_vars

        #load cofiguration
        self.load_configuration()

        #Google Service Account Credentials
        google_application_credentials_file = yaml_data['twitch-ouat']['google_service_account_credentials_file']
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_application_credentials_file

        #Taken from app authentication class()
        self.TWITCH_BOT_ACCESS_TOKEN = TWITCH_BOT_ACCESS_TOKEN

        #Set default loop state
        self.is_ouat_loop_active = False  # controls if the loop should runZ

        #counters
        self.ouat_counter = 0

    #Load configurations
    def load_configuration(self):
        #load yaml/env
        self.yaml_data = load_yaml(yaml_filename='config.yaml', yaml_dirname="config")
        load_env(env_filename=self.yaml_data['env_filename'], env_dirname=self.yaml_data['env_dirname'])

        #capture yaml/env data from instantiated class
        self.env_vars = self.env_vars
        self.twitch_bot_channel_name = self.yaml_data['twitch-app']['twitch_bot_channel_name']
        self.OPENAI_API_KEY = self.env_vars['OPENAI_API_KEY']
        self.twitch_bot_username = self.yaml_data['twitch-app']['twitch_bot_username']

        #Eleven Labs
        self.ELEVENLABS_XI_API_KEY = self.env_vars['ELEVENLABS_XI_API_KEY']
        self.ELEVENLABS_XI_VOICE = self.env_vars['ELEVENLABS_XI_VOICE']

        #runtime arguments
        self.args_include_sound = str.lower(args.include_sound)
        self.args_include_automsg = str.lower(args.include_automsg)
        self.args_automsg_prompt_list_name = str.lower(args.automated_msg_prompt_name)

        #TODO self.args_include_chatforme = str.lower(args.include_chatforme)
        self.args_chatforme_prompt_name = str.lower(args.chatforme_prompt_name)
        self.args_botthot_prompt_name = 'botthot'
        self.args_include_ouat = str.lower(args.include_ouat)        
        self.args_ouat_prompt_name = str.lower(args.ouat_prompt_name)

        #List for OUAT/newsarticle
        self.ouat_message_recurrence_seconds = self.yaml_data['ouat_message_recurrence_seconds']

        self.ouat_prompts = self.yaml_data['ouat_prompts']
        self.newsarticle_rss_feed = self.yaml_data['twitch-ouat']['newsarticle_rss_feed']
        self.ouat_news_article_summary_prompt = self.yaml_data['ouat_news_article_summary_prompt'] 

        self.gpt_ouat_prompt_begin = self.ouat_prompts[self.args_ouat_prompt_name]
        self.ouat_prompt_startstory = self.yaml_data['ouat_prompt_startstory']
        self.ouat_prompt_progression = self.yaml_data['ouat_prompt_progression']
        self.ouat_prompt_endstory = self.yaml_data['ouat_prompt_endstory']

        self.ouat_story_progression_number = self.yaml_data['ouat_story_progression_number']
        self.ouat_story_max_counter = self.yaml_data['ouat_story_max_counter']

        #AUTOMSG
        self.chatgpt_automated_msg_prompts = self.yaml_data['chatgpt_automated_msg_prompts']
        self.automsg_prompt_list = self.chatgpt_automated_msg_prompts[self.args_automsg_prompt_list_name]
        
        #general config
        self.num_bot_responses = self.yaml_data['num_bot_responses']

        #ouat prompts
        self.ouat_wordcount = self.yaml_data['ouat_wordcount']

        #automsg prompts
        self.automsg_prompt_prefix = self.yaml_data['automsg_prompt_prefix']

        #GPT Prompt
        self.gpt_prompt = ''  

        # Load settings and configurations from a YAML file
        # TODO: Can be moved into the load_configurations() function
        self.chatforme_message_wordcount = str(self.yaml_data['chatforme_message_wordcount'])
        self.formatted_gpt_chatforme_prompt_prefix = str(self.yaml_data['formatted_gpt_chatforme_prompt_prefix'])
        self.formatted_gpt_chatforme_prompt_suffix = str(self.yaml_data['formatted_gpt_chatforme_prompt_suffix'])
        self.formatted_gpt_chatforme_prompts = self.yaml_data['formatted_gpt_chatforme_prompts']

        return self.logger.info("Configuration attributes loaded/refreshed from YAML/env variables")  

    #Set the listener(?) to start once the bot is ready
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

    #controls ouat_storyteller()
    async def start_ouat_storyteller_msg_loop(self):
        self.is_ouat_loop_active = True
        self.load_configuration()
        if not any([self.args_include_automsg == 'yes', self.args_include_ouat == 'yes']):
            self.logger.error("Neither automsg or ouat enabled with app argument")
            raise BotFeatureNotEnabledException("Neither automsg or ouat enabled with app argument")

    @twitch_commands.command(name='get_chatters')
    async def get_chatters(self, ctx):
        try:
            twitchchatdata = TwitchChatData()
            temp_response = twitchchatdata.get_channel_viewers(bearer_token=self.TWITCH_BOT_ACCESS_TOKEN)
            channel_viewers_list_dict = twitchchatdata.process_channel_viewers(response = temp_response)
            table_id=yaml_data['twitch-ouat']['talkzillaai_userdata_table_id']
            channel_viewers_query = twitchchatdata.generate_bq_query(table_id=table_id, channel_viewers_list_dict=channel_viewers_list_dict)
            twitchchatdata.send_to_bq(query=channel_viewers_query)
        except Exception as e:
            self.logger.exception('An error occurred while fetching channel viewers: %s', e)
        return temp_response

    @twitch_commands.command(name='startstory')
    async def startstory(self, message):
        if self.ouat_counter == 0:

            # Capture writing tone/style/theme and randomly select one item from each list
            writing_tone_values = list(yaml_data['ouat-writing-parameters']['writing_tone'].values())
            writing_style_values = list(yaml_data['ouat-writing-parameters']['writing_style'].values())
            theme_values = list(yaml_data['ouat-writing-parameters']['theme'].values())
            self.selected_writing_style = random.choice(writing_style_values)
            self.selected_writing_tone = random.choice(writing_tone_values)
            self.selected_theme = random.choice(theme_values)

            # Fetch random article
            self.random_article_content = self.article_generator.fetch_random_article_content(article_char_trunc=300)                    
            replacements_dict = {"random_article_content":self.random_article_content}

            self.random_article_content = prompt_text_replacement(
                gpt_prompt_text=self.ouat_news_article_summary_prompt,
                replacements_dict=replacements_dict
                )
            gpt_ready_list_dict = combine_msghistory_and_prompttext(
                prompt_text=self.random_article_content,
                name=self.twitch_bot_username,
                msg_history_list_dict=None
                )
            self.random_article_content_prompt_summary = openai_gpt_chatcompletion(
                messages_dict_gpt=gpt_ready_list_dict, 
                OPENAI_API_KEY=self.OPENAI_API_KEY, 
                max_characters=1200
                )

            printc(f"A story was started by {message.author.name} ({message.author.id})", bcolors.WARNING)
            printc(f"Theme: {self.selected_theme}", bcolors.OKBLUE)
            printc(f"Writing Tone: {self.selected_writing_tone}", bcolors.OKBLUE)
            printc(f"Writing Style: {self.selected_writing_style}", bcolors.OKBLUE)
            self.logger.debug(f"A story was started by {message.author.id}")
            self.logger.debug(f'This is the gpt_ready_list_dict:')
            self.logger.debug(gpt_ready_list_dict)  
            self.logger.debug(f'This is the self.random_article_content_prompt_summary:')
            self.logger.debug(self.random_article_content_prompt_summary)

            await self.start_ouat_storyteller_msg_loop()

    @twitch_commands.command(name='addtostory')
    async def add_to_story_ouat(self, ctx,  *args):
        author=ctx.message.author.name
        prompt_text = ' '.join(args)
        gpt_ready_msg_dict = PromptHandler.create_gpt_message_dict_from_strings(
            self,
            content=prompt_text,
            role='user',
            name=author
            )
        self.message_handler.ouat_temp_msg_history.append(gpt_ready_msg_dict)
        
        printc(f"A story was added to by {ctx.message.author.name} ({ctx.message.author.id}): '{prompt_text}'", bcolors.WARNING)
        self.logger.info(f"A story was added to by {ctx.message.author.name} ({ctx.message.author.id}): '{prompt_text}'")

    @twitch_commands.command(name='extendstory')
    async def extend_story(self, ctx, *args) -> None:
        self.ouat_counter = 2
        self.logger.debug(f"Story extension requested, self.ouat_counter has been set to {self.ouat_counter}")

    @twitch_commands.command(name='stopstory')
    async def stop_story(self, ctx):
        await self.channel.send("--ToBeCoNtInUeD--")
        await self.stop_loop()

    @twitch_commands.command(name='endstory')
    async def endstory(self, ctx):
        self.ouat_counter = self.ouat_story_max_counter
        self.logger.debug(f"Story is being forced to end, counter is at {self.ouat_counter}")

    async def stop_loop(self) -> None:
        self.is_ouat_loop_active = False
        
        write_msg_history_to_file(
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

    async def event_message(self, message):
        #This is the control flow function for creating message histories
        self.message_handler.add_to_appropriate_message_history(message)
        
        # self.handle_commands directs the twitch bot when to take action on bot specific commands (say !startstory)
        if message.author is not None:
            await self.handle_commands(message)

    async def ouat_storyteller(self):
        self.load_configuration()
    
        #load article links (prepping for reading random article)
        if self.args_include_ouat == 'yes' and self.args_ouat_prompt_name.startswith('newsarticle'):
            self.article_generator = ArticleGeneratorClass.ArticleGenerator(rss_link=self.newsarticle_rss_feed)
            self.article_generator.fetch_articles()

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
                    #self.logger.debug(f'OUAT gpt_prompt_final: {gpt_prompt_final}')   
                
                else: self.logger.error("Neither automsg or ouat enabled with app startup argument")

                self.logger.info(f"The self.ouat_counter is currently at {self.ouat_counter}")
                messages_dict_gpt = combine_msghistory_and_prompttext(prompt_text=gpt_prompt_final,
                                                                      role='system',
                                                                      msg_history_list_dict=self.message_handler.ouat_temp_msg_history,
                                                                      combine_messages=True)
                self.logger.debug("This is the messages_dict_gpt:")
                self.logger.debug(messages_dict_gpt)

                ##################################################################################
                generated_message = openai_gpt_chatcompletion(messages_dict_gpt=messages_dict_gpt, 
                                                                OPENAI_API_KEY=self.OPENAI_API_KEY,
                                                                max_attempts=3)
                generated_message = re.sub(r'<<<.*?>>>\s*:', '', generated_message)
                
                if self.args_include_sound == 'yes':
                    v2s_message_object = generate_t2s_object(
                        ELEVENLABS_XI_API_KEY = self.ELEVENLABS_XI_API_KEY,
                        voice_id = self.ELEVENLABS_XI_VOICE,
                        text_to_say=generated_message, 
                        is_testing = False)
                    play_t2s_object(v2s_message_object)

                if self.ouat_counter == self.ouat_story_max_counter:
                    print("self.ouat_counter == self.ouat_story_max_counter:  That was the last message")
                    self.logger.info(f"That was the final message (self.ouat_counter == {self.ouat_story_max_counter})")  

                self.logger.info(f"FINAL generated_message (type: {type(generated_message)}): \n{generated_message}")  
                await self.channel.send(generated_message)
                self.ouat_counter += 1   

            await asyncio.sleep(int(self.ouat_message_recurrence_seconds))

    @twitch_commands.command(name='chatforme')
    async def chatforme(self, ctx):
        """
        A Twitch bot command that interacts with OpenAI's GPT API.
        It takes in chat messages from the Twitch channel and forms a GPT prompt for a chat completion API call.
        """
        self.load_configuration()
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
                                                                role='system',
                                                                msg_history_list_dict=self.message_handler.chatforme_temp_msg_history,
                                                                combine_messages=False)
        
        # Execute the GPT API call to get the chatbot response
        gpt_response = openai_gpt_chatcompletion(messages_dict_gpt=messages_dict_gpt, 
                                                 OPENAI_API_KEY=self.OPENAI_API_KEY)
        gpt_response_formatted = re.sub(r'<<<.*?>>>\s*:', '', gpt_response)

        await ctx.send(gpt_response_formatted)      
        return print(f"Sent gpt_response to chat: {gpt_response_formatted}")

    @twitch_commands.command(name='botthot')
    async def botthot(self, ctx):
        """
        A Twitch bot command that interacts with OpenAI's GPT API.
        It takes in chat messages from the Twitch channel and forms a GPT prompt for a chat completion API call.
        """
        self.load_configuration()
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
                                                              role='system',
                                                              name='unknown',
                                                              msg_history_list_dict=self.message_handler.chatforme_temp_msg_history,
                                                              combine_messages=False)
        
        # Execute the GPT API call to get the chatbot response
        gpt_response = openai_gpt_chatcompletion(messages_dict_gpt=messages_dict_gpt, OPENAI_API_KEY=self.OPENAI_API_KEY)
        gpt_response_formatted = re.sub(r'<<<.*?>>>\s*:', '', gpt_response)

        await ctx.send(gpt_response_formatted)
        return print(f"Sent gpt_response to chat: {gpt_response_formatted}")


################################
#TODO: Separate flask app class?

#TWITCH_BOT_REDIRECT_PATH = os.getenv('TWITCH_BOT_REDIRECT_PATH')
yaml_data = load_yaml(yaml_dirname='config', yaml_filename='config.yaml')
load_env(env_dirname=yaml_data['env_dirname'], env_filename=yaml_data['env_filename'])

twitch_bot_redirect_path = yaml_data['twitch-app']['twitch_bot_redirect_path']
TWITCH_BOT_CLIENT_ID = os.getenv('TWITCH_BOT_CLIENT_ID')
TWITCH_BOT_CLIENT_SECRET = os.getenv('TWITCH_BOT_CLIENT_SECRET')
TWITCH_BOT_SCOPE = os.getenv('TWITCH_BOT_SCOPE')

#App route home
@app.route('/')
def hello_world():
    return "Hello, you're probably looking for the /auth page!"

#app route auth
@app.route('/auth')
def auth():
    base_url_auth = 'https://id.twitch.tv/oauth2/authorize'
    input_port_number = str(args.input_port_number)
    redirect_uri = f'http://localhost:{input_port_number}/{twitch_bot_redirect_path}'
    params_auth = f'?response_type=code&client_id={TWITCH_BOT_CLIENT_ID}&redirect_uri={redirect_uri}&scope={TWITCH_BOT_SCOPE}&state={uuid.uuid4().hex}'
    url = base_url_auth+params_auth
    print(f"Generated redirect_uri: {redirect_uri}")
    return f'<a href="{url}">Connect with Twitch</a>'

#app route auth callback
@app.route('/callback')
def callback():
    global TWITCH_CHATFORME_BOT_THREAD  # declare the variable as global inside the function
    input_port_number = str(args.input_port_number)
    redirect_uri = f'http://localhost:{input_port_number}/{twitch_bot_redirect_path}'
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    # output = {}
    
    if error:
        return f"Error: {error}"
    
    data = {
        'client_id': TWITCH_BOT_CLIENT_ID,
        'client_secret': TWITCH_BOT_CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': redirect_uri
    }
    
    response = requests.post('https://id.twitch.tv/oauth2/token', data=data)
    
    if response.status_code == 200:
        #capture tokens
        TWITCH_BOT_ACCESS_TOKEN = response.json()['access_token']
        TWITCH_BOT_REFRESH_TOKEN = response.json()['refresh_token']

        #add the access/refresh token to the environments
        os.environ["TWITCH_BOT_ACCESS_TOKEN"] = TWITCH_BOT_ACCESS_TOKEN        
        os.environ["TWITCH_BOT_REFRESH_TOKEN"] = TWITCH_BOT_REFRESH_TOKEN

        # Only start bot thread if it's not already running
        if TWITCH_CHATFORME_BOT_THREAD is None or not TWITCH_CHATFORME_BOT_THREAD.is_alive():
            TWITCH_CHATFORME_BOT_THREAD = Thread(target=run_bot, args=(TWITCH_BOT_ACCESS_TOKEN,))
            TWITCH_CHATFORME_BOT_THREAD.start()
            twitch_bot_status = 'Twitch bot was not active or did not exist and thread was started.'
        else: 
            twitch_bot_status = 'Twitch bot was active so the existing bot thread was left active.'

        return f'<a>{twitch_bot_status} Access Token and Refresh Token have been captured and set in the current environment</a>'

    else:
        # output = {}
        # output['response.text'] = response.json()
        return '<a>There was an issue retrieving and setting the access token.  If you would like to include more detail in this message, return "template.html" or equivalent using the render_template() method from flask and add it to this response...'

#This is run immediately after the authentication process.
def run_bot(TWITCH_BOT_ACCESS_TOKEN):

    #load yaml_data for init'ing Bot class
    yaml_data = load_yaml(yaml_filename='config.yaml', yaml_dirname='config')
    
    #TODO This could be moved to a ConfigManager() class as it only needs a handful
    # of configuration parameters
    load_env(env_filename=yaml_data['env_filename'], env_dirname=yaml_data['env_dirname'])
    env_vars = {
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'ELEVENLABS_XI_API_KEY': os.getenv('ELEVENLABS_XI_API_KEY'),
        'ELEVENLABS_XI_VOICE': os.getenv('ELEVENLABS_XI_VOICE'),
        'ELEVENLABS_XI_VOICE_BUSINESS': os.getenv('ELEVENLABS_XI_VOICE_BUSINESS')
    }

    #asyncio event loop
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    
    #instantiate the class
    bot = Bot(TWITCH_BOT_ACCESS_TOKEN, yaml_data, env_vars)
    bot.run()

#TODO/NOTE: Everytime /callback is hit, a new bot instance is being started.  This 
# could cause problems
if __name__ == "__main__":

    # Can't get the defaults  in arg parser to work as I planned (aka leaving the command prompt entry 
    # empty.)  Defaults in arg parser could thus be confusing as they are useless!
    parser = argparse.ArgumentParser(description="Select your runtime arguments")

    #OnceUponATime:
    parser.add_argument("--include_ouat", default="yes", dest="include_ouat")
    parser.add_argument("--ouat_prompt_name", default="newsarticle_og2",dest="ouat_prompt_name", help="The name of the prompt list of dictionaries in the YAML file (default: standard):")

    #automsg
    parser.add_argument("--include_automsg", default="no", dest="include_automsg")
    parser.add_argument("--automated_msg_prompt_name", default="standard",dest="automated_msg_prompt_name", help="The name of the prompt list of dictionaries in the YAML file (default: standard):")
    parser.add_argument("--include_sound", default="no", dest="include_sound", help="Should the bot run with sound? (yes/no)")

    #chatforme
    parser.add_argument("--chatforme_prompt_name", default="standard", dest="chatforme_prompt_name", help="The name of the prompt in the YAML file.")
    
    #app port
    parser.add_argument("--input_port_number", default=3000, dest="input_port_number", help="The port you would like to use:")

    #run app
    args = parser.parse_args()
    app.run(port=args.input_port_number, debug=True, use_reloader=use_reloader_bool)