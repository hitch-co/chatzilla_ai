#twitch_bot.py
#usage: python "C:\_repos\chatforme_bots\twitch_bot.py" --automated_msg_prompt_name standard


#imports
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

#Start the app
app = Flask(__name__)

###############
#Load yaml file & Load and Store keys/tokens from env
yaml_data = load_yaml(yaml_filename='config.yaml', yaml_dirname="C:\\_repos\\chatforme_bots\\config")
load_env(env_filename=yaml_data['env_filename'], env_dirname=yaml_data['env_dirname'])

##########
#YAML FILE
msg_history_limit = yaml_data['msg_history_limit']
num_bot_responses = yaml_data['num_bot_responses']
automated_message_seconds = yaml_data['automated_message_seconds']
automated_message_wordcount = str(yaml_data['automated_message_wordcount'])
formatted_gpt_automsg_prompt_prefix = str(yaml_data['formatted_gpt_automsg_prompt_prefix'])
formatted_gpt_automsg_prompt_suffix = str(yaml_data['formatted_gpt_automsg_prompt_suffix'])
formatted_gpt_chatforme_prompt_prefix = str(yaml_data['formatted_gpt_chatforme_prompt_prefix'])
formatted_gpt_chatforme_prompt_suffix = str(yaml_data['formatted_gpt_chatforme_prompt_suffix'])

#nested automsg gpt prompts
chatgpt_automated_msg_prompts = yaml_data['chatgpt_automated_msg_prompts']
chatgpt_chatforme_prompts = yaml_data['chatgpt_chatforme_prompts']

############
#ENVIRONMENT

#Open AI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

#Twitch
TWITCH_BOT_CLIENT_ID = os.getenv('TWITCH_BOT_CLIENT_ID')
TWITCH_BOT_CLIENT_SECRET = os.getenv('TWITCH_BOT_CLIENT_SECRET')
TWITCH_BOT_SCOPE = 'chat:read+chat:edit'
TWITCH_BOT_REDIRECT_BASE = os.getenv('TWITCH_BOT_REDIRECT_BASE')
TWITCH_BOT_REDIRECT_AUTH = os.getenv('TWITCH_BOT_REDIRECT_AUTH')
TWITCH_BOT_USERNAME = os.getenv('TWITCH_BOT_USERNAME')
TWITCH_BOT_CHANNEL_NAME = os.getenv('TWITCH_BOT_CHANNEL_NAME')

#Eleven Labs
ELEVENLABS_XI_API_KEY = os.getenv('ELEVENLABS_XI_API_KEY')
ELEVENLABS_XI_VOICE_PERSONAL = os.getenv('ELEVENLABS_XI_VOICE_PERSONAL')
ELEVENLABS_XI_VOICE_BUSINESS = os.getenv('ELEVENLABS_XI_VOICE_BUSINESS')

#Placeholder/junk
TWITCH_CHATFORME_BOT_THREAD = None 


###############################
class Bot(twitch_commands.Bot):

    def __init__(self, TWITCH_BOT_ACCESS_TOKEN):
        super().__init__(
            token=TWITCH_BOT_ACCESS_TOKEN, #chagned from irc_token
            name=TWITCH_BOT_USERNAME,
            prefix='!',
            initial_channels=[TWITCH_BOT_CHANNEL_NAME],
            nick = 'chatforme_bot'
            #NOTE/QUESTION:what other variables could be set here?
        )
        self.messages = []

        #NOTE/QUESTION: Should all of my twitch bot related variables be delcared
        # here rather than above/outside/before the class?
        #i.e. yaml here....
        #i.e. env here


    #Set the listener(?) to start once the bot is ready
    async def event_ready(self):
        print(f'Ready | {self.nick}')
        
        #starts the loop for sending a periodic message 
        self.loop.create_task(self.send_periodic_message())
        
        #sets the channel name in prep for sending a hello message
        #TODO: Add a forloop to cycle through twitch channels in yaml  
        channel = self.get_channel(TWITCH_BOT_CHANNEL_NAME)
        await channel.send("Hello there!")


    # # Inside the Bot class
    # async def is_stream_live(self):
    #     response = requests.get(f"https://api.twitch.tv/helix/streams?user_login={TWITCH_BOT_CHANNEL_NAME}",
    #                             headers={"Client-ID": TWITCH_BOT_CLIENT_ID, "Authorization": f"Bearer {self.token}"})
    #     data = response.json()
    #     
    #     # Do something if the stream is live
    #     something = print('did something')    
    #     
    #     #return "data" in data
    #     return something
    #
    # 


    #automated message every N seconds
    async def send_periodic_message(self):

        #Import voice options
        from my_modules.text_to_speech import generate_t2s_object
        from elevenlabs import play

        while True:

            # #TODO: Checks to see whether the stream is live before executing any auto
            # # messaging services.  Comment out and update indent to make live
            # stream_live = await self.is_stream_live()
            # if stream_live:    

            #Argument from runnign twitch_bot.py.  This will determine which respective set of propmts is randomly 
            # cycled through.
            chatgpt_automated_msg_prompts_list = yaml_data['chatgpt_automated_msg_prompts'][args.automated_msg_prompt_name]
            include_sound = args.include_sound

            #Grab a random prompt based on % chance from the config.yaml
            formatted_gpt_auto_msg_prompt = rand_prompt(chatgpt_automated_msg_prompts_list=chatgpt_automated_msg_prompts_list)

            #get the channel and populate the prompt
            channel = self.get_channel(TWITCH_BOT_CHANNEL_NAME)
            if channel:

                #Build the prompt
                gpt_auto_msg_prompt = formatted_gpt_automsg_prompt_prefix+" [everything that follows is your prompt as the aforementioned chat bot]:"+formatted_gpt_auto_msg_prompt+formatted_gpt_chatforme_prompt_suffix
                messages_dict_gpt = [{'role': 'system', 'content': gpt_auto_msg_prompt}]
                
                #Generate the prompt response
                generated_message = openai_gpt_chatcompletion(messages_dict_gpt=messages_dict_gpt, OPENAI_API_KEY=OPENAI_API_KEY)

                #Print
                print("-----------------------------------------------")
                print("----- THIS IS THE GPT AUTO MESSAGE PROMPT -----")
                print(gpt_auto_msg_prompt)
                print("-----------------------------------------------")

                print("-----------------------------------------------")
                print("------THIS IS THE GENERATED MESSAGE -----------")
                print(generated_message)
                print("-----------------------------------------------")

                #Send the message to twitch             
                await channel.send(generated_message)

                #Play the message generated/sent to TWITCH
                v2s_message_object = generate_t2s_object(ELEVENLABS_XI_API_KEY = ELEVENLABS_XI_API_KEY,
                                                           voice_id = ELEVENLABS_XI_VOICE_PERSONAL,
                                                           text_to_say=generated_message, 
                                                           is_testing = False)
                
                #if the prompt entered on startup is True, play the sound after the message is sent
                if include_sound == True:
                    play(v2s_message_object)

            await asyncio.sleep(int(automated_message_seconds))



    #Collects historic messages for use in chatforme
    async def event_message(self, message):
        print('--------------------------------')
        print('starting message content capture')
        print(message.content)

        #Error checking; Address message nuances 
        try:
            if message.author is not None:
                self.messages.append({'role': 'user', 'name': message.author.name, 'content': message.content})
                if len(self.messages) > msg_history_limit:
                    self.messages.pop(0)
        except AttributeError:
            self.messages.append({'role': 'user', 'name': 'bot', 'content': message.content})            
        if message.author is not None:
            await self.handle_commands(message)


    #Twitch command
    @twitch_commands.command(name='chatforme')
    async def chatforme(self, ctx):
        try:
            request_user_name = ctx.author.name
        except AttributeError:
            request_user_name = 'bot?'

        # Build out GPT 'prompt'
        users_in_messages_list = list(set([message['name'] for message in self.messages]))
        users_in_messages_list_text = ', '.join(users_in_messages_list)


        # Get the formatted twitch prompts from yaml
        formatted_gpt_chatforme_prompts = {
            key: value.format(
                num_bot_responses=num_bot_responses,
                request_user_name=request_user_name,
                users_in_messages_list_text=users_in_messages_list_text,
                automated_message_wordcount=automated_message_wordcount
            ) for key, value in chatgpt_chatforme_prompts.items() if isinstance(value, str)
        }
        formatted_gpt_chatforme_prompt = formatted_gpt_chatforme_prompts[args.chatforme_prompt_name]

        discord_chatgpt_chatforme_prompt = formatted_gpt_chatforme_prompt_prefix+formatted_gpt_chatforme_prompt+formatted_gpt_chatforme_prompt_suffix
        chatgpt_prompt_dict = {'role': 'system', 'content': discord_chatgpt_chatforme_prompt}

        messages_dict_gpt = self.messages + [chatgpt_prompt_dict]

        # Final execution of chatgpt api call
        gpt_response = openai_gpt_chatcompletion(messages_dict_gpt=messages_dict_gpt, OPENAI_API_KEY=OPENAI_API_KEY)
        await ctx.send(gpt_response)


################################
#TODO: Separate flask app class?

#App route home
@app.route('/')
def hello_world():
    return "Hello, you're probably looking for the /auth page!"


#app route auth
@app.route('/auth')
def auth():
    base_url_auth = 'https://id.twitch.tv/oauth2/authorize'
    params_auth = f'?response_type=code&client_id={TWITCH_BOT_CLIENT_ID}&redirect_uri={TWITCH_BOT_REDIRECT_BASE}&scope={TWITCH_BOT_SCOPE}&state={uuid.uuid4().hex}'
    url = base_url_auth+params_auth
    print(f"Generated redirect_uri: {TWITCH_BOT_REDIRECT_BASE}")
    return f'<a href="{url}">Connect with Twitch</a>'


#app route auth callback
@app.route('/callback')
def callback():
    global TWITCH_CHATFORME_BOT_THREAD  # declare the variable as global inside the function
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
        'redirect_uri': TWITCH_BOT_REDIRECT_BASE
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
        return '<a>There was an issue retrieving and setting the access token.  If you would like to include more detail, return "template.html" or equivalent using the render_template() method from flask and add it to this response...'

def run_bot(TWITCH_BOT_ACCESS_TOKEN):
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    bot = Bot(TWITCH_BOT_ACCESS_TOKEN)
    bot.run()

#NOTE: Everytime /callback is hit, a new bot instance is being started.  This 
# could cause problems

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Select prompt_name for gpt_auto_msg_prompt.")

    #automsg
    parser.add_argument("--automated_msg_prompt_name", default="standard",dest="automated_msg_prompt_name", help="The name of the prompt list of dictionaries in the YAML file.")
    parser.add_argument("--include_sound", default=False, dest="include_sound", help="Should the bot run with sound?")

    #chatforme
    parser.add_argument("--chatforme_prompt_name", default="standard", dest="chatforme_prompt_name", help="The name of the prompt in the YAML file.")
    
    #run app
    args = parser.parse_args()
    app.run(port=3000, debug=True)



