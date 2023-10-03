#Whether or not to refresh flask app live
use_reloader_bool=False
runtime_logger_level = 'DEBUG'

#imports
import asyncio #(new_event_loop, set_event_loop)
from twitchio.ext import commands as twitch_commands
from threading import Thread
from flask import Flask, request
import uuid
import requests
import os
import argparse
import re


from classes.ConsoleColoursClass import bcolors, printc
from classes import ArticleGeneratorClass
from classes.CustomExceptions import BotFeatureNotEnabledException
from my_modules.gpt import get_random_rss_article_summary_prompt, openai_gpt_chatcompletion
from my_modules.gpt import generate_ouat_prompt, generate_automsg_prompt, combine_msghistory_and_prompt
from my_modules.my_logging import my_logger 

from modules import load_yaml, load_env

#separate modules file
#TODO: modules should be reorganized
from my_modules import text_to_speech

#Voice imports
from my_modules.text_to_speech import generate_t2s_object
from elevenlabs import play

#Automsg
from my_modules.utils import format_previous_messages_to_string

# configure the root logger
root_logger = my_logger(dirname='log', logger_name='root_logger', debug_level=runtime_logger_level)
root_logger.info("this is a root log!")

#Start the app
app = Flask(__name__)

#Load yaml file & Load and Store keys/tokens from env
yaml_data = load_yaml(yaml_filename='config.yaml', yaml_dirname="config")
load_env(env_filename=yaml_data['env_filename'], env_dirname=yaml_data['env_dirname'])

#Placeholder/junk
TWITCH_CHATFORME_BOT_THREAD = None

###############################
class Bot(twitch_commands.Bot):

    def __init__(self, TWITCH_BOT_ACCESS_TOKEN, yaml_data, env_vars):
        super().__init__(
            token=TWITCH_BOT_ACCESS_TOKEN, #chagned from irc_token
            name=yaml_data['twitch-app']['twitch_bot_username'], #env_vars['TWITCH_BOT_USERNAME'],
            prefix='!',
            initial_channels=[yaml_data['twitch-app']['twitch_bot_channel_name']],#[env_vars['TWITCH_BOT_CHANNEL_NAME']],
            nick = 'chatforme_bot'
            #NOTE/QUESTION:what other variables should be set here?
        )

        #setup logger
        self.logger = my_logger(dirname='log', logger_name='logger_BotClass', debug_level=runtime_logger_level)

        #May be redundant.  I think I should leave these here but then ened to handle
        # Configuration in the bot(run()) section of the script which is outside both classes
        # and thus might need it's own class
        self.yaml_data = yaml_data
        self.env_vars = env_vars

        #load cofiguration
        self.load_configuration()

        #Taken from app authentication class()
        self.TWITCH_BOT_ACCESS_TOKEN = TWITCH_BOT_ACCESS_TOKEN

        #Set default loop state
        self.is_ouat_loop_active = False  # controls if the loop should runZ

    #Load configurations
    def load_configuration(self):
        #load yaml/env
        self.yaml_data = load_yaml(yaml_filename='config.yaml', yaml_dirname="config")
        load_env(env_filename=self.yaml_data['env_filename'], env_dirname=self.yaml_data['env_dirname'])

        #capture yaml/env data from instantiated class
        self.env_vars = self.env_vars
        self.twitch_bot_channel_name = self.yaml_data['twitch-app']['twitch_bot_channel_name']
        self.OPENAI_API_KEY = self.env_vars['OPENAI_API_KEY']
        self.twitch_bot_username = yaml_data['twitch-app']['twitch_bot_username']

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

        #placeholder list
        self.chatforme_temp_msg_history = []
        self.automsg_temp_msg_history = []
        self.bot_temp_msg_history = []
        self.nonbot_temp_msg_history = []

        #List for OUAT/newsarticle
        self.ouat_message_recurrence_seconds = self.yaml_data['ouat_message_recurrence_seconds']
        self.ouat_temp_msg_history = []
        self.random_article_content = ''
        self.ouat_prompts = self.yaml_data['ouat_prompts']
        self.newsarticle_rss_feed = self.yaml_data['twitch-automsg']['newsarticle_rss_feed']
        self.ouat_news_article_summary_prompt = yaml_data['ouat_news_article_summary_prompt'] 

        self.gpt_ouat_prompt_begin = self.ouat_prompts[self.args_ouat_prompt_name]
        self.ouat_prompt_startstory = self.yaml_data['ouat_prompt_startstory']
        self.ouat_prompt_progression = self.yaml_data['ouat_prompt_progression']
        self.ouat_prompt_endstory = self.yaml_data['ouat_prompt_endstory']

        self.ouat_story_progression_number = yaml_data['ouat_story_progression_number']
        self.ouat_story_max_counter = yaml_data['ouat_story_max_counter']

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

        print("Loaded yaml and env file, configured all variables")     
        return self.logger.info("Loaded configuration function")  


    #Set the listener(?) to start once the bot is ready
    async def event_ready(self):
        print(f'Ready | {self.nick}')
        
        #load configuration
        self.load_configuration()
        
        #starts the loop for sending a periodic message 
        self.loop.create_task(self.send_periodic_message())
        
        #sets the channel name in prep for sending a hello message
        #TODO: Add a forloop to cycle through twitch channels in yaml  
        self.channel = self.get_channel(self.twitch_bot_channel_name)
        #await self.channel.send("I'm the storyteller bot.  You can start a story with [!startstory], [!stopstory] and [!addtostory thing to add].  [!botthot] will provide a gpt response based on the conversation history so feel free to ask a question and then send !botthot with a separate message")

        if self.args_include_ouat == 'yes' and self.args_ouat_prompt_name.startswith('newsarticle'):
            # self.article_generator = ArticleGeneratorClass.ArticleGenerator(rss_link=self.newsarticle_rss_feed)
            # self.articles_content = self.article_generator.fetch_articles_content()
            self.news_article_content_plot_summary = get_random_rss_article_summary_prompt(newsarticle_rss_feed=self.newsarticle_rss_feed,
                                                                                           summary_prompt=self.ouat_news_article_summary_prompt,
                                                                                           OPENAI_API_KEY=self.OPENAI_API_KEY,
                                                                                           )

    #controls send_periodic_message()
    async def start_loop(self):
        self.is_ouat_loop_active = True
        self.load_configuration()
        if not any([self.args_include_automsg == 'yes', self.args_include_ouat == 'yes']):
            self.logger.error("Neither automsg or ouat enabled with app argument")
            raise BotFeatureNotEnabledException("Neither automsg or ouat enabled with app argument")        
        self.logger.debug(f'self.news_article_content_plot_summary: {self.news_article_content_plot_summary}')


    @twitch_commands.command(name='addtostory')
    async def add_to_story_ouat(self, ctx, *args):
        sentence = ' '.join(args)
        sentence_dict = {'role':'user', 'content':sentence}
        self.ouat_temp_msg_history.append(sentence_dict)
        

    #stops and clears the ouat loop/message history
    async def stop_loop(self):
        self.is_ouat_loop_active = False
        self.ouat_temp_msg_history.clear()
        self.ouat_counter = 0


    async def print_send_periodic_message_runtime_params(self):
        args_list = [
            "args_include_automsg",
            "args_automsg_prompt_list_name",
            "args_include_ouat",
            "args_ouat_prompt_name",
            "args_chatforme_prompt_name",
            "args_include_sound"
        ]
        
        printc("These are the runtime params for this bot:", bcolors.WARNING)
        for arg in args_list:
            printc(f"{arg}: {getattr(self, arg)}", bcolors.OKBLUE)


    #TODO: Collects historic messages for use in chatforme
    async def event_message(self, message):
        printc("Message Captured:",bcolors.FAIL)

        #Reload the yaml for every event messsage in case things have changed
        self.load_configuration()

        # Loop through each key in the 'twitch-bots' dictionary
        bots_automsg = self.yaml_data['twitch-bots']['automsg']
        bots_chatforme = self.yaml_data['twitch-bots']['chatforme']
        bots_ouat = self.yaml_data['twitch-bots']['onceuponatime']
        known_bots = []

        # Extend the known_bots list with the list of bots under the current key
        for key in self.yaml_data['twitch-bots']:
            known_bots.extend(self.yaml_data['twitch-bots'][key])

        # If you want to remove duplicates
        known_bots = list(set(known_bots))

        ############################################
        if message.author is not None:
            # for attr in dir(message):
            #     if not attr.startswith('__'):
            #         print(f"{attr}: {getattr(message, attr)}")
            printc("message.author is not None", bcolors.FAIL)  
            printc(f"message.author.name: {message.author.name}", bcolors.OKBLUE)
            printc(f'message.content: {message.content[:25]}...\n', bcolors.OKBLUE)

            # Collect all metadata
            message_metadata = {
                'badges': message.author.badges,
                'name': message.author.name,
                'user_id': message.author.id,
                'display_name': message.author.display_name,
                'channel': message.channel.name,
                'timestamp': message.timestamp,
                'tags': message.tags,
                'content': f'<<<{message.author.name}>>>: {message.content}',
                'role':'user'
            }
            # Filter to gpt columns, update the 'content' key to include {name}: {content}
            gptchatcompletion_keys = {'role', 'content'}
            filtered_message_dict = {key: message_metadata[key] for key in gptchatcompletion_keys}


            ###########################################
            #TODO: Should be a command not a condition 
            # Check if the message is triggering a command
            if message.content.startswith('!'):
                # TODO: Add your code here
                printc("MESSAGE CONTENT STARTS WITH = ! NO ACTION TAKEN\n", bcolors.WARNING)  
                if message.content == "!startstory" and (message.author.name == self.twitch_bot_channel_name or message.author.is_mod):
                    await self.start_loop()
                elif message.content == "!stopstory" and (message.author.name == self.twitch_bot_channel_name or message.author.is_mod):
                    await self.stop_loop()

            else:
                ############################################
                # Check if message from automsg or chatforme bot
                if message.author.name in bots_automsg or message.author.name in bots_chatforme:
                    printc(f'message.author.name:{message.author.name} IS IN bots_automsg or bots_chatforme',bcolors.WARNING)
                    # Add GPT related fields to automsg and chatforme variables 
                    printc(f"{message.author.name}'s message added to automsg_temp_msg_history",bcolors.WARNING) 
                    self.automsg_temp_msg_history.append(filtered_message_dict)
                    printc(f"{message.author.name}'s message added to chatforme_temp_msg_history",bcolors.WARNING)
                    self.chatforme_temp_msg_history.append(filtered_message_dict)
                else: printc(f'message.author.name:{message.author.name} IS NOT IN bots_automsg or bots_chatforme',bcolors.WARNING)

                ############################################
                if message.author.name in bots_ouat:
                    printc(f"{message.author.name}'s message added to ouat_temp_msg_history",bcolors.WARNING)
                    self.ouat_temp_msg_history.append(filtered_message_dict)
                else: printc(f'{message.author.name} IS NOT IN bots_ouat',bcolors.WARNING)

                ############################################
                #All other messagers hould be from users, capture them here
                if message.author.name not in known_bots:
                    printc(f"{message.author.name} is NOT IN known_bots",bcolors.WARNING)
                    # Add GPT related fields to nonbot and chatforme variables
                    printc(f"{message.author.name}'s message added to nonbot_temp_msg_history",bcolors.OKBLUE) 
                    self.nonbot_temp_msg_history.append(message_metadata)
                    printc(f"{message.author.name}'s message added to chatforme_temp_msg_history", bcolors.OKBLUE)   
                    self.chatforme_temp_msg_history.append(filtered_message_dict)

                else: printc(f"message.author.name: {message.author.name} IS IN known_bots",bcolors.WARNING) 
                print("\n")

        ############################################
        # Check for bot or system messages
        elif message.author is None:
            printc("message.author is None", bcolors.FAIL)  
            # #printout attributes associated with event_message()
            # for attr in dir(message):
            #     if not attr.startswith('__'):
            #         print(f"{attr}: {getattr(message, attr)}")
            message_rawdata = message.raw_data
            start_index = message_rawdata.find(":") + 1  # Add 1 to not include the first ':'
            end_index = message_rawdata.find("!")

            # Check if both start_index and end_index are valid
            if start_index == 0 or end_index == -1:
                extracted_name = 'unknown_name - see message.raw_data for details'
            else:
                extracted_name = message_rawdata[start_index:end_index]

            if extracted_name in bots_automsg or extracted_name in bots_chatforme:

                role='user'
                message_metadata = {
                    'role': role,
                    'content': f'<<<{extracted_name}>>>: {message.content}'
                    }

                #add GPT elements to automsg msg list variagble
                printc(f"MESSAGE AUTHOR = AUTOMSG BOT ({extracted_name})",bcolors.OKBLUE)
                self.automsg_temp_msg_history.append(message_metadata)

                #add GPT elements to chatforme msg list variagble
                printc(f"MESSAGE AUTHOR = CHATFORME BOT ({extracted_name})",bcolors.OKBLUE)
                self.chatforme_temp_msg_history.append(message_metadata)
        print('\n')

        # TODO: ADD TO DATABASE
        #
        #
        #
        #
        
        if message.author is not None:
            await self.handle_commands(message)


    #Create a GPT response based on config.yaml
    async def send_periodic_message(self):

        await self.print_send_periodic_message_runtime_params() 
        self.load_configuration()
        self.channel = self.get_channel(self.twitch_bot_channel_name)
        self.ouat_counter = 0
    
        #This is the while loop that generates the occurring GPT response
        while True:
            if self.is_ouat_loop_active == False:
                await asyncio.sleep(4)
                      
            else:
                replacements_dict = {"ouat_wordcount":self.ouat_wordcount,
                                     'twitch_bot_username':self.twitch_bot_username,
                                     'num_bot_responses':self.num_bot_responses,
                                     'rss_feed_article_plot':self.news_article_content_plot_summary,
                                     'param_in_text':'variable_from_scope'}
                self.logger.debug(f'replacements_dict: ')
                self.logger.debug(f'{replacements_dict}')

                #######################################
                self.ouat_counter += 1   
                self.logger.warning(f"ouat_counter is: {self.ouat_counter}")
                if self.args_include_ouat == 'yes':

                    if self.ouat_counter == 1:
                        gpt_prompt_final = generate_ouat_prompt(gpt_ouat_prompt=self.ouat_prompt_startstory,
                                                                replacements_dict=replacements_dict)         
                        self.logger.debug(f'OUAT gpt_prompt_final: {gpt_prompt_final}')

                    if self.ouat_counter < self.ouat_story_progression_number:
                        gpt_prompt_final = generate_ouat_prompt(gpt_ouat_prompt=self.gpt_ouat_prompt_begin,
                                                                replacements_dict=replacements_dict)         
                        self.logger.debug(f'OUAT gpt_prompt_final: {gpt_prompt_final}')

                    elif self.ouat_counter < self.ouat_story_max_counter:
                        gpt_prompt_final = generate_ouat_prompt(gpt_ouat_prompt=self.ouat_prompt_progression,
                                                                replacements_dict=replacements_dict) 
                        
                    elif self.ouat_counter == self.ouat_story_max_counter:
                        gpt_prompt_final = generate_ouat_prompt(gpt_ouat_prompt=self.ouat_prompt_endstory,
                                                                replacements_dict=replacements_dict)                                       

                    elif self.ouat_counter > self.ouat_story_max_counter:
                        message = "---TheEnd---"
                        await self.channel.send(message)
                        await self.stop_loop()
                        continue

                # #######################################
                # elif self.args_include_automsg == 'yes':
                #     gpt_prompt_final = generate_automsg_prompt(automsg_prompts_list=self.automsg_prompt_list,
                #                                                 automsg_prompt_prefix=self.automsg_prompt_prefix,
                #                                                 replacements_dict=replacements_dict)
                #     self.logger.debug(f'AUTOMSG gpt_prompt_final: {gpt_prompt_final}')
                
                #######################################
                else: print("Neither automsg or ouat enabled with argument")

                messages_dict_gpt = combine_msghistory_and_prompt(prompt_text=gpt_prompt_final,
                                                                    msg_history_dict=self.automsg_temp_msg_history)
                
                ##################################################################################
                generated_message = openai_gpt_chatcompletion(messages_dict_gpt=messages_dict_gpt, 
                                                                OPENAI_API_KEY=self.OPENAI_API_KEY,
                                                                max_attempts=3)
                generated_message = re.sub(r'<<<.*?>>>', '', generated_message)

                self.logger.info(f"\nFINAL self.automsg_temp_msg_history type: {type(self.automsg_temp_msg_history)}")
                self.logger.info(f"\nFINAL gpt_prompt_final:{gpt_prompt_final}") 
                self.logger.info(f"\nFINAL generated_message: {generated_message}")  

                if self.args_include_sound == 'yes':
                    v2s_message_object = generate_t2s_object(ELEVENLABS_XI_API_KEY = self.ELEVENLABS_XI_API_KEY,
                                                            voice_id = self.ELEVENLABS_XI_VOICE,
                                                            text_to_say=generated_message, 
                                                            is_testing = False)
                    play(v2s_message_object)

                await self.channel.send(generated_message)
                self.logger.debug(f'self.is_ouat_loop_active: {self.is_ouat_loop_active}')
            
            await asyncio.sleep(int(self.ouat_message_recurrence_seconds))


    # Import the Twitch command decorator
    @twitch_commands.command(name='chatforme')
    async def chatforme2(self, ctx):
        """
        A Twitch bot command that interacts with OpenAI's GPT API.
        It takes in chat messages from the Twitch channel and forms a GPT prompt for a chat completion API call.
        """
        self.load_configuration()
        request_user_name = ctx.message.author.name

        # #TODO: add a print_chatforme2_runtime_params function
        # printc('CHATFORME command issued', bcolors.WARNING)
        # printc(f"Request Username:{request_user_name}", bcolors.OKBLUE)
        # printc(f"num_bot_responses: {self.num_bot_responses}", bcolors.OKBLUE)
        # printc(f"chatforme_message_wordcount: {chatforme_message_wordcount}", bcolors.OKBLUE)
        # printc(f"formatted_gpt_chatforme_prompt_prefix: {formatted_gpt_chatforme_prompt_prefix}", bcolors.OKBLUE)
        # printc(f"formatted_gpt_chatforme_prompt_suffix: {formatted_gpt_chatforme_prompt_suffix}", bcolors.OKBLUE)
        # printc(f'formatted_gpt_chatforme_prompts: {formatted_gpt_chatforme_prompts}', bcolors.OKBLUE)

        # Extract usernames from previous chat messages stored in chatforme_temp_msg_history.
        users_in_messages_list = list(set([message['role'] for message in self.chatforme_temp_msg_history]))
        users_in_messages_list_text = ', '.join(users_in_messages_list)

        # Format the GPT prompts using 
        # placeholders and data from the YAML file and chat history.
        # TODO: Redo using format_prompt() function
        formatted_gpt_chatforme_prompts_formatted = {
            key: value.format(
                twitch_bot_username=self.twitch_bot_username,
                num_bot_responses=self.num_bot_responses,
                request_user_name=request_user_name,
                users_in_messages_list_text=users_in_messages_list_text,
                chatforme_message_wordcount=self.chatforme_message_wordcount
            ) for key, value in self.formatted_gpt_chatforme_prompts.items() if isinstance(value, str)
        }

        #TODO: Can be replaced by a function
        #Select the prompt based on the argument on app startup
        formatted_gpt_chatforme_prompt = formatted_gpt_chatforme_prompts_formatted[self.args_chatforme_prompt_name]

        #Build the chatgpt_chatforme_prompt to be added as role: system to the 
        # chatcompletions endpoint
        chatgpt_chatforme_prompt = self.formatted_gpt_chatforme_prompt_prefix + formatted_gpt_chatforme_prompt + self.formatted_gpt_chatforme_prompt_suffix

        # Create a dictionary entry for the chat prompt
        chatgpt_prompt_dict = [{'role': 'system', 'content': chatgpt_chatforme_prompt}]

        # Combine the chat history with the new system prompt to form a list of messages for GPT.
        messages_dict_gpt = self.chatforme_temp_msg_history + chatgpt_prompt_dict

        # Execute the GPT API call to get the chatbot response
        gpt_response = openai_gpt_chatcompletion(messages_dict_gpt=messages_dict_gpt, OPENAI_API_KEY=self.OPENAI_API_KEY)

        # #TODO:: Could be replaced by a function
        # #Print out Final prompt
        # printc('\nLOG: This is the prompt prefix that was selected (formatted_gpt_chatforme_prompt_prefix)', bcolors.WARNING)
        # print(self.formatted_gpt_chatforme_prompt_prefix)
        # printc('\nLOG: This is the prompt that was selected (formatted_gpt_chatforme_prompt)', bcolors.WARNING)
        # print(formatted_gpt_chatforme_prompt)
        # printc("\nLOG: This is the prompt (formatted_gpt_chatforme_prompt_suffix)", bcolors.WARNING)
        # print(self.formatted_gpt_chatforme_prompt_suffix)
        # printc("\nFINAL gpt_response:", bcolors.WARNING)
        # print(gpt_response)

        # Send the GPT-generated response back to the Twitch chat.
        await ctx.send(gpt_response)
        
        return print(f"Sent gpt_response to chat: {gpt_response}")


    # Import the Twitch command decorator
    @twitch_commands.command(name='botthot')
    async def chatforme(self, ctx):
        """
        A Twitch bot command that interacts with OpenAI's GPT API.
        It takes in chat messages from the Twitch channel and forms a GPT prompt for a chat completion API call.
        """
        self.load_configuration()
        request_user_name = ctx.message.author.name

        # printc('CHATFORME command issued', bcolors.WARNING)
        # printc(f"Request Username:{request_user_name}", bcolors.OKBLUE)
        # printc(f"num_bot_responses: {self.num_bot_responses}", bcolors.OKBLUE)
        # printc(f"chatforme_message_wordcount: {self.chatforme_message_wordcount}", bcolors.OKBLUE)
        # printc(f"formatted_gpt_chatforme_prompt_prefix: {self.formatted_gpt_chatforme_prompt_prefix}", bcolors.OKBLUE)
        # printc(f"formatted_gpt_chatforme_prompt_suffix: {self.formatted_gpt_chatforme_prompt_suffix}", bcolors.OKBLUE)
        # printc(f'formatted_gpt_chatforme_prompts: {self.formatted_gpt_chatforme_prompts}', bcolors.OKBLUE)

        #TODO right now 'bot' is being sent when 'bot1' or 'cire5955_dev' should be sent (The bot username)
        # Get chat history for this session, grab the list of prompts from the yaml. 
        message_list = self.chatforme_temp_msg_history

        # Extract usernames from previous chat messages stored in chatforme_temp_msg_history.
        users_in_messages_list = list(set([message['role'] for message in message_list]))
        users_in_messages_list_text = ', '.join(users_in_messages_list)

        # Format the GPT prompts using placeholders and data from the YAML file and chat history.
        formatted_gpt_chatforme_prompts_formatted = {
            key: value.format(
                twitch_bot_username=self.twitch_bot_username,
                num_bot_responses=self.num_bot_responses,
                request_user_name=request_user_name,
                users_in_messages_list_text=users_in_messages_list_text,
                chatforme_message_wordcount=self.chatforme_message_wordcount
            ) for key, value in self.formatted_gpt_chatforme_prompts.items() if isinstance(value, str)
        }
        #Select the prompt based on the argument on app startup
        formatted_gpt_chatforme_prompt = formatted_gpt_chatforme_prompts_formatted[self.args_botthot_prompt_name]

        #Build the chatgpt_chatforme_prompt to be added as role: system to the 
        # chatcompletions endpoint
        chatgpt_chatforme_prompt = self.formatted_gpt_chatforme_prompt_prefix + formatted_gpt_chatforme_prompt + self.formatted_gpt_chatforme_prompt_suffix

        # Create a dictionary entry for the chat prompt
        chatgpt_prompt_dict = [{'role': 'system', 'content': chatgpt_chatforme_prompt}]

        # Combine the chat history with the new system prompt to form a list of messages for GPT.
        messages_dict_gpt = message_list + chatgpt_prompt_dict

        # Execute the GPT API call to get the chatbot response
        gpt_response = openai_gpt_chatcompletion(messages_dict_gpt=messages_dict_gpt, OPENAI_API_KEY=self.OPENAI_API_KEY)

        # #Print out Final prompt
        # printc('\nLOG: This is the prompt prefix that was selected (formatted_gpt_chatforme_prompt_prefix)', bcolors.WARNING)
        # print(self.formatted_gpt_chatforme_prompt_prefix)
        # printc('\nLOG: This is the prompt that was selected (formatted_gpt_chatforme_prompt)', bcolors.WARNING)
        # print(formatted_gpt_chatforme_prompt)
        # printc("\nLOG: This is the prompt (formatted_gpt_chatforme_prompt_suffix)", bcolors.WARNING)
        # print(self.formatted_gpt_chatforme_prompt_suffix)
        # printc("\nFINAL gpt_response:", bcolors.WARNING)
        # print(gpt_response)

        # Send the GPT-generated response back to the Twitch chat.
        await ctx.send(gpt_response)



################################
#TODO: Separate flask app class?

#TWITCH_BOT_REDIRECT_PATH = os.getenv('TWITCH_BOT_REDIRECT_PATH')
twitch_bot_redirect_path = yaml_data['twitch-app']['twitch_bot_redirect_path']
TWITCH_BOT_CLIENT_ID = os.getenv('TWITCH_BOT_CLIENT_ID')
TWITCH_BOT_CLIENT_SECRET = os.getenv('TWITCH_BOT_CLIENT_SECRET')
twitch_bot_scope = 'chat:read+chat:edit'

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
    params_auth = f'?response_type=code&client_id={TWITCH_BOT_CLIENT_ID}&redirect_uri={redirect_uri}&scope={twitch_bot_scope}&state={uuid.uuid4().hex}'
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
    output = {}
    
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
            TWITCH_CHATFORME_BOT_THREAD = Thread(target=run_bot, args=(os.getenv('TWITCH_BOT_ACCESS_TOKEN'),))
            TWITCH_CHATFORME_BOT_THREAD.start()
            twitch_bot_status = 'Twitch bot was not active or did not exist and thread was started'
        else: 
            twitch_bot_status = 'Twitch bot was active so the existing bot thread was left active(???)'

        print( f'<a>{twitch_bot_status}\nAccess token:{TWITCH_BOT_ACCESS_TOKEN}, Refresh Token: {TWITCH_BOT_REFRESH_TOKEN}</a>')
        return f'<a>{twitch_bot_status}\nAccess Token and Refresh Token have been captured and set in the current environment</a>'

    else:
        output = {}
        output['response.text'] = response.json()
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

    #TODO: asyncio event loop
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

