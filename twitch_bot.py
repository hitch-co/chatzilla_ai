#imports
from ConsoleColoursClass import bcolors, printc

from modules import load_yaml, load_env, openai_gpt_chatcompletion, get_models, rand_prompt
import asyncio #(new_event_loop, set_event_loop)
from twitchio.ext import commands as twitch_commands
from threading import Thread
from flask import Flask, request, url_for
import uuid
import requests
import os
import argparse
import json
import random
import openai

#separate modules file
#TODO: modules should be reorganized
from my_modules import text_to_speech

#Voice imports
from my_modules.text_to_speech import generate_t2s_object
from elevenlabs import play

#Automsg
from my_modules.utils import format_previous_messages_to_string

#load yaml/env
yaml_data = load_yaml(yaml_filename='config.yaml', yaml_dirname="config")
load_env(env_filename=yaml_data['env_filename'], env_dirname=yaml_data['env_dirname'])

#Start the app
app = Flask(__name__)

###############
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
            name=env_vars['TWITCH_BOT_USERNAME'],
            prefix='!',
            initial_channels=[env_vars['TWITCH_BOT_CHANNEL_NAME']],
            nick = 'chatforme_bot'
            #NOTE/QUESTION:what other variables could be set here?
        )

        #TODO: Need to work out loadiong env/yaml into the class.  See CrubeYawnes PR
        #i.e. load_env() here
        #i.e. load_env() here

        #load yaml/env
        self.yaml_data = load_yaml(yaml_filename='config.yaml', yaml_dirname="config")
        load_env(env_filename=self.yaml_data['env_filename'], env_dirname=self.yaml_data['env_dirname'])

        #capture yaml/env data from instantiated class
        self.env_vars = env_vars
        self.TWITCH_BOT_CHANNEL_NAME = env_vars['TWITCH_BOT_CHANNEL_NAME']
        self.OPENAI_API_KEY = env_vars['OPENAI_API_KEY']
        self.TWITCH_BOT_USERNAME = env_vars['TWITCH_BOT_USERNAME']

        #runtime arguments
        self.args_include_sound = str.lower(args.include_sound)

        self.args_include_automsg = str.lower(args.include_automsg)
        self.args_automated_msg_prompt_name = str.lower(args.automated_msg_prompt_name)

        #TODO self.args_include_chatforme = str.lower(args.include_chatforme)
        self.args_chatforme_prompt_name = str.lower(args.chatforme_prompt_name)

        self.args_include_ouat = str.lower(args.include_ouat)        
        self.args_ouat_prompt_name = str.lower(args.ouat_prompt_name)

        #placeholder list
        self.chatforme_temp_msg_history = []
        self.automsg_temp_msg_history = []
        self.bot_temp_msg_history = []
        self.nonbot_temp_msg_history = []
        self.ouat_temp_msg_history = []

    #Set the listener(?) to start once the bot is ready
    async def event_ready(self):
        print(f'Ready | {self.nick}')
        
        #starts the loop for sending a periodic message 
        self.loop.create_task(self.send_periodic_message())
        
        #sets the channel name in prep for sending a hello message
        #TODO: Add a forloop to cycle through twitch channels in yaml  
        channel = self.get_channel(self.TWITCH_BOT_CHANNEL_NAME)
        #await channel.send("Hello there!")


    #TODO: Collects historic messages for use in chatforme
    async def event_message(self, message):
        printc("-----------------------------------------------",bcolors.WARNING)
        printc("BEGINNING MESSAGE CAPTGURE",bcolors.WARNING)
        printc("-----------------------------------------------",bcolors.WARNING)

        #Reload the yaml for every event messsage in case things have changed
        self.yaml_data = load_yaml(yaml_filename='config.yaml', yaml_dirname="config")

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

        # try:
        if message.author is not None:
            # for attr in dir(message):
            #     if not attr.startswith('__'):
            #         print(f"{attr}: {getattr(message, attr)}")
            printc("message.author is not None", bcolors.WARNING)  
            printc(f"MESSAGE AUTHOR: {message.author.name}", bcolors.OKBLUE)
            printc(f'MESSAGE CONTENT: {message.content}\n', bcolors.OKBLUE)

            # Collect all metadata
            message_metadata = {
                'badges': message.author.badges,
                'name': message.author.name,
                'user_id': message.author.id,
                'display_name': message.author.display_name,
                'channel': message.channel.name,
                'timestamp': message.timestamp,
                'tags': message.tags,
                'content': f'<<<{message.author.name}>>>: {message.content}'
            }

            #Add bot role
            message_metadata['role'] = 'user'
            
            # Filter to gpt columns, update the 'content' key to include {name}: {content}
            gptchatcompletion_keys = {'role', 'content'}
            filtered_message_dict = {key: message_metadata[key] for key in gptchatcompletion_keys}
            printc("filtered_message_dict:", bcolors.WARNING)
            print(filtered_message_dict)
            print("\n")

            # Check if the message is triggering a command
            if message.content.startswith('!'):
                # TODO: Add your code here
                printc("MESSAGE CONTENT STARTS WITH = ! NO ACTION TAKEN\n", bcolors.WARNING)  

            else:
                # Check if message from automsg or chatforme bot
                if message.author.name in bots_automsg or message.author.name in bots_chatforme:
                    printc('message.author.name in bots_automsg or message.author.name in bots_chatforme',bcolors.WARNING)
                    # Add GPT related fields to automsg and chatforme variables 
                    printc(f"MESSAGE AUTHOR = AUTOMSG BOT ({message.author.name})",bcolors.OKBLUE)   
                    self.automsg_temp_msg_history.append(filtered_message_dict)
                    printc(f"MESSAGE AUTHOR = CHATFORME BOT ({message.author.name})",bcolors.OKBLUE)   
                    self.chatforme_temp_msg_history.append(filtered_message_dict)
                else: printc("MESSAGE AUTHOR NOT A AUTOMSG BOT or CHATFORME BOT", bcolors.WARNING)

                if message.author.name in bots_ouat:
                    printc('message.author.name in bots_ouat',bcolors.WARNING)
                    # Add GPT related fields to ouat variable 
                    printc(f"MESSAGE AUTHOR = OUAT BOT ({message.author.name})", bcolors.OKBLUE)   
                    self.ouat_temp_msg_history.append(filtered_message_dict)
                else: printc("MESSAGE AUTHOR NOT A OUAT BOT", bcolors.FAIL)

                #All other messagers hould be from users, capture them here
                if message_metadata['role'] not in known_bots:
                    printc(f"message_metadata['role'] not in known_bots",bcolors.WARNING) 
                    # Add GPT related fields to nonbot and chatforme variables
                    printc(f"MESSAGE AUTHOR = USER ({message.author.name})",bcolors.OKBLUE) 
                    self.nonbot_temp_msg_history.append(message_metadata)
                    print(f"MESSAGE AUTHOR = CHATFORME BOT ({message.author.name})")   
                    self.chatforme_temp_msg_history.append(filtered_message_dict)
                else: printc("MESSAGE AUTHOR NOT A AUTOMSG BOT", bcolors.WARNING)
                print("\n")

        # Check for bot or system messages
        elif message.author is None:
            printc("message.author is None", bcolors.WARNING)  
            # #printout attributes associated with event_message()
            # for attr in dir(message):
            #     if not attr.startswith('__'):
            #         print(f"{attr}: {getattr(message, attr)}")
            printc("MESSAGE AUTHER = NONE",bcolors.FAIL)
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
        # print('----------------------')
        # print('chatforme_temp_msg_history:')
        # print(self.chatforme_temp_msg_history)
        # print('----------------------')
        # print('automsg_temp_msg_history:')
        # print(self.automsg_temp_msg_history)
        # print('----------------------')
        # print('nonbot_temp_msg_history:')
        # print(self.nonbot_temp_msg_history)
        # print('----------------------')

        # TODO: ADD TO DATABASE
        #
        #
        #
        #
        
        if message.author is not None:
            await self.handle_commands(message)


    #Create a GPT response based on config.yaml
    async def send_periodic_message(self):
        
        #ensure at least one bot was set to activate
        if self.args_include_automsg != 'yes' and self.args_include_ouat != 'yes':
            return printc('Neither AUTOMSG or OUAT were set to YES at app launch', bcolors.FAIL)
        
        #Eleven Labs
        ELEVENLABS_XI_API_KEY = self.env_vars['ELEVENLABS_XI_API_KEY']
        ELEVENLABS_XI_VOICE = self.env_vars['ELEVENLABS_XI_VOICE']
        ELEVENLABS_XI_VOICE_BUSINESS = self.env_vars['ELEVENLABS_XI_VOICE_BUSINESS']
        #ELEVENLABS_XI_VOICE_NEW = self.env_vars['ELEVENLABS_XI_VOICE_NEW']

        #load yaml in case it has changed
        self.yaml_data = load_yaml(yaml_filename='config.yaml', yaml_dirname="config")

        #general config
        num_bot_responses = self.yaml_data['num_bot_responses']

        #ouat prompts
        ouat_wordcount = self.yaml_data['ouat_wordcount']
        ouat_prompts = self.yaml_data['ouat_prompts']

        #automsg prompts
        automated_message_seconds = self.yaml_data['automated_message_seconds']
        automsg_prompt_prefix = self.yaml_data['automsg_prompt_prefix']
        chatgpt_automated_msg_prompts = self.yaml_data['chatgpt_automated_msg_prompts']

        #Import voice options
        from my_modules.text_to_speech import generate_t2s_object
        from elevenlabs import play

        # #TODO: Checks to see whether the stream is live before executing any auto
        # # messaging services.  Comment out and update indent to make live
        # stream_live = await self.is_stream_live()
        # if stream_live()   
        printc("These are the runtime params for this bot:", bcolors.WARNING)
        printc(f"self.args_include_automsg:{self.args_include_automsg}", bcolors.OKBLUE) 
        printc(f"self.args_automated_msg_prompt_name:{self.args_automated_msg_prompt_name}", bcolors.OKBLUE)
        printc(f"self.args_include_ouat:{self.args_include_ouat}", bcolors.OKBLUE) 
        printc(f"self.args_ouat_prompt_name:{self.args_ouat_prompt_name}", bcolors.OKBLUE) 
        printc(f"self.args_chatforme_prompt_name:{self.args_chatforme_prompt_name}", bcolors.OKBLUE) 
        printc(f"self.args_include_sound:{self.args_include_sound}", bcolors.OKBLUE) 


        #Set channel
        channel = self.get_channel(self.TWITCH_BOT_CHANNEL_NAME)


        #TODO Need to introduce this control flow a bit different.  DOesn't work well with current
        # bot launch app selections for params

        #if include_automsg == 'yes'
        if self.args_include_automsg == 'yes': 

            #Argument from runnign twitch_bot.py.  This will determine which respective set of propmts is randomly 
            # cycled through.
            selected_prompts_list = chatgpt_automated_msg_prompts[self.args_automated_msg_prompt_name]
            printc("AUTMSG: These are the variables for AUTOMSG", bcolors.WARNING)
            printc(f"AUTOMSG selected_prompts_list:{selected_prompts_list}", bcolors.OKBLUE)   
            printc(f"AUTOMSG self.args_automated_msg_prompt_name:{self.args_automated_msg_prompt_name}", bcolors.OKBLUE) 
            
            #Grab a random prompt based on % chance from the config.yaml
            automsg_prompt = rand_prompt(prompts_list=selected_prompts_list)   
            printc(f"OUAT automsg_prompt:{automsg_prompt}", bcolors.OKBLUE)  
   
            #Build the prompt
            gpt_prompt = automsg_prompt_prefix + " [everything that follows is your prompt as the aforementioned chat bot]:" + automsg_prompt
            printc(f"AUTOMSG gpt_prompt:{gpt_prompt}", bcolors.OKBLUE)   
            print("\n")
        else: printc("AUTOMSG is not set to yes\n", bcolors.WARNING)


        if self.args_include_ouat == 'yes':

            await channel.send("---NEW STORY---")

            #Argument from runnign twitch_bot.py.  This will determine which respective set of propmts is randomly 
            # cycled through.
            # NOTE: Doesn't use the random prompt generator because there is only one prompt
            ouat_prompt = ouat_prompts[self.args_ouat_prompt_name]
            printc("OUAT: These are the variables for OUAT", bcolors.WARNING)
            printc(f"OUAT args_ouat_prompt_name:{self.args_ouat_prompt_name}", bcolors.OKBLUE) 

            gpt_prompt = ouat_prompt
            printc(f"OUAT gpt_prompt:{gpt_prompt}\n", bcolors.OKBLUE) 

        else: printc("OUAT is not set to yes\n", bcolors.WARNING)

        while True:

            #Get list of already said things
            msg_list_historic = self.automsg_temp_msg_history
            printc(f'FINAL self.automsg_temp_msg_history type:{type(self.automsg_temp_msg_history)}',bcolors.WARNING)
            printc(f'{self.automsg_temp_msg_history}', bcolors.OKBLUE)
            print("\n")

            if channel: 
                
                #insert variables
                params = {"ouat_wordcount":ouat_wordcount, 
                          'twitch_bot_username':self.TWITCH_BOT_USERNAME,
                          'num_bot_responses':num_bot_responses}
                gpt_prompt_final = gpt_prompt.format(**params)
                printc(f"FINAL gpt_prompt:",bcolors.WARNING)
                printc(gpt_prompt, bcolors.OKBLUE) 
                print("\n")
                printc(f"FINAL gpt_prompt_final:", bcolors.WARNING)
                printc(gpt_prompt_final, bcolors.OKBLUE) 
                print("\n")

                #Final prompt dict submitted to GPT
                gpt_prompt_dict = [{'role': 'system', 'content': gpt_prompt_final}]

                #Final combined prompt dictionary (historic + prompt)
                messages_dict_gpt = msg_list_historic + gpt_prompt_dict

                # Combine the chat history with the new system prompt to form a list of messages for GPT.
                printc(f"FINAL msg_list_historic type: {type(msg_list_historic)}", bcolors.WARNING)
                print(msg_list_historic)
                print("\n") 
                printc(f"FINAL gpt_prompt_dict type: {type(gpt_prompt_dict)}", bcolors.WARNING)
                print(gpt_prompt_dict)
                print("\n") 
                printc(f"FINAL messages_dict_gpt type: {type(messages_dict_gpt)}", bcolors.WARNING)
                print(messages_dict_gpt)
                print("\n") 

                #Generate the prompt response
                generated_message = openai_gpt_chatcompletion(messages_dict_gpt=messages_dict_gpt, OPENAI_API_KEY=self.OPENAI_API_KEY)
                printc(f"FINAL generated_message:", bcolors.FAIL)  
                printc(generated_message, bcolors.WARNING)  
                print("\n")

                #Send the message to twitch             
                await channel.send(generated_message)

                #if the prompt entered on startup is True, play the sound after the message is sent
                if self.args_include_sound == 'yes':
                    #Play the message generated/sent to TWITCH
                    v2s_message_object = generate_t2s_object(ELEVENLABS_XI_API_KEY = ELEVENLABS_XI_API_KEY,
                                                            voice_id = ELEVENLABS_XI_VOICE,
                                                            text_to_say=generated_message, 
                                                            is_testing = False)

                    play(v2s_message_object)
                    
            await asyncio.sleep(int(automated_message_seconds))


    # Import the Twitch command decorator
    @twitch_commands.command(name='chatforme')
    async def chatforme(self, ctx):
        """
        A Twitch bot command that interacts with OpenAI's GPT API.
        It takes in chat messages from the Twitch channel and forms a GPT prompt for a chat completion API call.
        """
        print('---------------------------------')
        print('---------------------------------')
        print("---STARTING CHATFORME COMMAND----")
        print('---------------------------------')
        print('---------------------------------')
        print('LOG:LOAD PARAMS FROM ENV/YAML')
        # Load settings and configurations from a YAML file
        num_bot_responses = self.yaml_data['num_bot_responses']
        chatforme_message_wordcount = str(self.yaml_data['chatforme_message_wordcount'])
        formatted_gpt_chatforme_prompt_prefix = str(self.yaml_data['formatted_gpt_chatforme_prompt_prefix'])
        formatted_gpt_chatforme_prompt_suffix = str(self.yaml_data['formatted_gpt_chatforme_prompt_suffix'])
        formatted_gpt_chatforme_prompts = self.yaml_data['formatted_gpt_chatforme_prompts']

        print(f"num_bot_responses: {num_bot_responses}")
        print(f"chatforme_message_wordcount: {chatforme_message_wordcount}")
        print(f"formatted_gpt_chatforme_prompt_prefix: {formatted_gpt_chatforme_prompt_prefix}")
        print(f"formatted_gpt_chatforme_prompt_suffix: {formatted_gpt_chatforme_prompt_suffix}")
        print(f'formatted_gpt_chatforme_prompts: {formatted_gpt_chatforme_prompts}')

        #TODO right now 'bot' is being sent when 'bot1' or 'cire5955_dev' should be sent (The bot username)
        # Get chat history for this session, grab the list of prompts from the yaml. 
        message_list = self.chatforme_temp_msg_history

        # Extract usernames from previous chat messages stored in chatforme_temp_msg_history.
        users_in_messages_list = list(set([message['role'] for message in message_list]))
        users_in_messages_list_text = ', '.join(users_in_messages_list)
        request_user_name = ctx.message.author.name

        # Format the GPT prompts using 
        # placeholders and data from the YAML file and chat history.
        formatted_gpt_chatforme_prompts_formatted = {
            key: value.format(
                twitch_bot_username=self.TWITCH_BOT_USERNAME,
                num_bot_responses=num_bot_responses,
                request_user_name=request_user_name,
                users_in_messages_list_text=users_in_messages_list_text,
                chatforme_message_wordcount=chatforme_message_wordcount

            ) for key, value in formatted_gpt_chatforme_prompts.items() if isinstance(value, str)
        }
        #Select the prompt based on the argument on app startup
        formatted_gpt_chatforme_prompt = formatted_gpt_chatforme_prompts_formatted[self.args_chatforme_prompt_name]

        #Build the chatgpt_chatforme_prompt to be added as role: system to the 
        # chatcompletions endpoint
        chatgpt_chatforme_prompt = formatted_gpt_chatforme_prompt_prefix + formatted_gpt_chatforme_prompt + formatted_gpt_chatforme_prompt_suffix
        print('---------------------------------')
        print('---------------------------------')
        print('LOG: This is the prompt prefix that was selected (formatted_gpt_chatforme_prompt_prefix)')
        print(formatted_gpt_chatforme_prompt_prefix)
        print('---------------------------------')
        print('---------------------------------')
        print('LOG: This is the prompt that was selected (formatted_gpt_chatforme_prompt)')
        print(formatted_gpt_chatforme_prompt)
        print('---------------------------------')
        print('---------------------------------')
        print("LOG: This is the prompt (formatted_gpt_chatforme_prompt_suffix)")
        print(formatted_gpt_chatforme_prompt_suffix)

        # Create a dictionary entry for the chat prompt
        chatgpt_prompt_dict = {'role': 'system', 'content': chatgpt_chatforme_prompt}

        # Combine the chat history with the new system prompt to form a list of messages for GPT.
        messages_dict_gpt = message_list + [chatgpt_prompt_dict]

        # Execute the GPT API call to get the chatbot response
        gpt_response = openai_gpt_chatcompletion(messages_dict_gpt=messages_dict_gpt, OPENAI_API_KEY=self.OPENAI_API_KEY)

        print('---------------------------------')
        print('---------------------------------')
        print("REACHED #5: gpt_response")
        #TODO is currently a dictionary of prompts
        print(gpt_response)

        # Send the GPT-generated response back to the Twitch chat.
        await ctx.send(gpt_response)



################################
#TODO: Separate flask app class?

TWITCH_BOT_REDIRECT_PATH = os.getenv('TWITCH_BOT_REDIRECT_PATH')
TWITCH_BOT_CLIENT_ID = os.getenv('TWITCH_BOT_CLIENT_ID')
TWITCH_BOT_CLIENT_SECRET = os.getenv('TWITCH_BOT_CLIENT_SECRET')
#TWITCH_BOT_REDIRECT_AUTH = os.getenv('TWITCH_BOT_REDIRECT_AUTH')
TWITCH_BOT_SCOPE = 'chat:read+chat:edit'

#App route home
@app.route('/')
def hello_world():
    return "Hello, you're probably looking for the /auth page!"


#app route auth
@app.route('/auth')
def auth():
    base_url_auth = 'https://id.twitch.tv/oauth2/authorize'
    input_port_number = str(args.input_port_number)
    redirect_uri = f'http://localhost:{input_port_number}/{TWITCH_BOT_REDIRECT_PATH}'
    params_auth = f'?response_type=code&client_id={TWITCH_BOT_CLIENT_ID}&redirect_uri={redirect_uri}&scope={TWITCH_BOT_SCOPE}&state={uuid.uuid4().hex}'
    url = base_url_auth+params_auth
    print(f"Generated redirect_uri: {redirect_uri}")
    return f'<a href="{url}">Connect with Twitch</a>'


#app route auth callback
@app.route('/callback')
def callback():
    global TWITCH_CHATFORME_BOT_THREAD  # declare the variable as global inside the function
    input_port_number = str(args.input_port_number)
    redirect_uri = f'http://localhost:{input_port_number}/{TWITCH_BOT_REDIRECT_PATH}'
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
    
    from modules import load_yaml, load_env

    #load yaml_data for init'ing Bot class
    yaml_data = load_yaml(yaml_filename='config.yaml', yaml_dirname='config')
    
    #load env vars and then set dict object for init'ing Bot class
    load_env(env_filename=yaml_data['env_filename'], env_dirname='env_dirname')
    env_vars = {
        'TWITCH_BOT_USERNAME': os.getenv('TWITCH_BOT_USERNAME'),
        'TWITCH_BOT_CHANNEL_NAME': os.getenv('TWITCH_BOT_CHANNEL_NAME'),
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
    parser.add_argument("--include_ouat", default="no", dest="include_ouat")
    parser.add_argument("--ouat_prompt_name", default="onceuponatime",dest="ouat_prompt_name", help="The name of the prompt list of dictionaries in the YAML file (default: standard):")

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
    app.run(port=args.input_port_number, debug=True)