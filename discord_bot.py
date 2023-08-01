#discord_bot.py
from modules import load_yaml, load_env, openai_gpt_chatcompletion, get_models
from discord.ext import commands
import discord
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO)

#Load yaml file
yaml_data = load_yaml(yaml_filename='config.yaml', yaml_dirname="c:\\Users\\erich\\OneDrive\\Desktop\\_work\\__repos\\discord-chatforme\\config")

# Store the bot API key and the OpenAI ChatGPT API key
load_env(env_filename=yaml_data['env_filename'], env_dirname=yaml_data['env_dirname'])
DISCORD_BOT_KEY = os.getenv('DISCORD_BOT_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize the bot client 'client' with the given API key (sometimes tutorials use intents "all" instead of "default")
bot = commands.Bot(command_prefix='!', 
                   intents=discord.Intents.all())

# Define the event for when the bot has connected to the Discord server
@bot.event
async def on_ready():
    print('discord-chatforme is now running')
    message = '@silent chatforme bot is now connected on discord!'
    print(message)
    #await ctx.send(message)

#Primary command/function that calls discord API to gather message history and 
# openai API to submit the message history for an automated response.
#  -reads yaml/config for api key
@bot.command()
async def chatforme(
    ctx, 
    skip_response = False, 
    msg_history_limit = yaml_data['msg_history_limit'], 
    num_bot_responses = yaml_data['num_bot_responses'], 
    chatgpt_prompt_prefix = '',
    chatgpt_prompt_suffix = ''#to be implemented
    ): 
    
    #add base parameters, create placeholder lists/etc.
    msg_history_limit = int(msg_history_limit)
    num_bot_responses=int(num_bot_responses)
    messages_dict_gpt = []
    users_in_messages_list = []

    #Grab the async generator object channel.history from discord
    messages = ctx.channel.history(limit=msg_history_limit)
    print('"messages" object is of type:',type(messages))

    #Build the keyvalue pairs to be added to a dictionary and then added to the list messages_dict_gpt
    async for message in messages:        
        message_dict = {}

        #Used in GPT get request
        #filters messages to exclude bot/system and user command() related messages from the 
        # GPT response 
        if message.author.bot == True or message.content.startswith('!'):
            continue
        else: 
            if message.author.system == False or not message.content.startswith('!'):
                # Build messages_dict_gpt dictionary 
                message_author_name_gpt = message.author.name #replace w dict
                message_author_role_gpt = 'user'
                message_author_content_gpt = message.content #replace w dict
                message_dictitem_gpt = {"role": message_author_role_gpt, "name": message_author_name_gpt, "content": message_author_name_gpt+": "+message_author_content_gpt} #replace w dict
                messages_dict_gpt.append(message_dictitem_gpt)
                
                # Add author name to the list if it's unique.  
                if message.author.name not in users_in_messages_list:
                    users_in_messages_list.append(message.author.name)  
                else: continue            
            else:
                print('this was either a system/bot generated response or was a command issued to a bot by a user')

    #BUild out GPT 'prompt'. Make sure this is the first entry in 'list of dictionaries'
    request_user_name = ctx.author.name
    users_in_messages_list_text = {', '.join(users_in_messages_list)}
    
    chatgpt_prompt_meat = f'You are an assistant designed to predict the next {num_bot_responses} response(s) \
        that can come from any of the "usernames" in the conversation history.  The very first message \
        provided should come from {request_user_name} and {num_bot_responses} responses that follow \
        should: \
            1. come from one of the users that have already participated, \
            2. be 1 sentence at least, two if necessary, \
            3. not be repetitive of text spoken in the  \
            4. only be conversation between those that have already participated, in this case: {*users_in_messages_list,} \
            5. Include "name" followed by a colon and then the content of the message for each user in your \
                {num_bot_responses} generated response(s). \
            6. begin with "<<<" followed by the username and then a colon. \
            7. The only usernames that can be in your response are {users_in_messages_list_text}'
    chatgpt_prompt_final = chatgpt_prompt_prefix+". "+chatgpt_prompt_meat+". "+chatgpt_prompt_suffix
    chatgpt_prompt_dict = {'role': 'system','content':chatgpt_prompt_final}
    messages_dict_gpt.append(chatgpt_prompt_dict)

    #View what is submitted to chatgpt and then send the request to GPT
    print('usernames to be used in GPT response:') 
    print(users_in_messages_list)
    print('final message history dictionary used for GPT response:') 
    print(messages_dict_gpt)

    #Final execution of chatgpt api call
    if skip_response == False:
        gpt_response = openai_gpt_chatcompletion(messages_dict_gpt=messages_dict_gpt,
                                                 OPENAI_API_KEY=OPENAI_API_KEY)
        await ctx.send(gpt_response)
    else:
        #TODO: print prettier!  pp = pprint.PrettyPrinter(indent=4) pp.newline = '\n\n' pp.pprint(mylistofdictionaries)
        help_message = "This is what will be received by GPT, including the prompt and the chat history\nNote:\
            If you can see this, the bot is currently not retrieving responses from GPT\nNote: The\
            structure is a list of dictionaries and includes the following:\n1. Dictionary\
            including the prompt to be received by GPT\n2. n Dictionaries, one for each of the\
            messages used by GPT to generate a response"
        await ctx.send(help_message)
        await ctx.send(messages_dict_gpt)

#placeholder command
@bot.command()
async def bye(self, ctx):
    await ctx.send('Goodbye!')

#run the bot
bot.run(DISCORD_BOT_KEY)