#main.py

# Define the Discord bot function
#def discord_bot_function(bot_api_key, chatgpt_api_key):
import dotenv
import os
import discord
from discord.ext import commands
import openai

# Store the bot API key and the OpenAI ChatGPT API key
#  - Alternative: openai.api_key = os.getenv("OPENAI_API_KEY")
load_env(env_filename='config.env', env_dirname='config') 
DISCORD_BOT_KEY = os.getenv('DISCORD_BOT_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

#Load yaml file
yaml_data = load_yaml(yaml_filename='config.yaml', yaml_dirname='')

# Initialize the bot client 'client' with the given API key (sometimes tutorials use intents "all" instead of "default")
bot = commands.Bot(command_prefix='!', 
                   intents=discord.Intents.all())

# Define the event for when the bot has connected to the Discord server
@bot.event
async def on_ready(ctx):
    message = '@silent chatforme bot is now connected on discord!'
    print(message)
    await ctx.send(message)

## Define the event for when a message is received
# Command to extract channel conversations.  Note: it appears as thouh ctx is automatically input as
#  a parameter when called
@bot.command()
async def chatforme(
    ctx, 
    skip_response = False, 
    msg_history_limit = '15', 
    num_bot_responses = '1', 
    chatgpt_prompt_prefix = '',
    chatgpt_prompt_suffix = '' #to be implemented
    ): 

    """
    #TODO Add an if/else statement that checks to see whether default values are
    # used and if they are, the config.yaml file is used to populate the func
    # parameters
    # Check if skip_response is using the default value
    if skip_response is chatforme.__defaults__[0]:
        print("skip_response is using the default value")
    else:
        print("skip_response has a user-defined value")

    # Check if msg_history_limit is using the default value
    if msg_history_limit is chatforme.__defaults__[1]:
        print("msg_history_limit is using the default value")
    else:
        print("msg_history_limit has a user-defined value")

    # Check if num_bot_responses is using the default value
    if num_bot_responses is chatforme.__defaults__[2]:
        print("num_bot_responses is using the default value")
    else:
        print("num_bot_responses has a user-defined value")

    # Check if chatgpt_prompt_prefix is using the default value
    if chatgpt_prompt_prefix is chatforme.__defaults__[3]:
        print("chatgpt_prompt_prefix is using the default value")
    else:
        print("chatgpt_prompt_prefix has a user-defined value")

    # Check if chatgpt_prompt_suffix is using the default value
    if chatgpt_prompt_suffix is chatforme.__defaults__[4]:
        print("chatgpt_prompt_suffix is using the default value")
    else:
        print("chatgpt_prompt_suffix has a user-defined value")
    """
    
    #housekeeping: add base parameters, create placeholder lists/etc.
    msg_history_limit = int(msg_history_limit)
    num_bot_responses=int(num_bot_responses)
    messages_processed = []
    users_in_messages_list = []

    #grab the async generator object channel.history from discord
    messages = ctx.channel.history(limit=msg_history_limit)
    print('---------------------------------------')
    print('------- messages object details -------')
    print('---------------------------------------')
    print('"messages" object is of type:',type(messages))

    async for message in messages:
        # Add author name to the list if it's unique.  Used in GPT get request
        #TODO : NOTE, there is a similar loop happening below
        if message.author.bot != False and message.author.system == False or not message.content.startswith('!'):
            if message.author.name not in users_in_messages_list:
                users_in_messages_list.append(message.author.name)
        print(f'users in messages list: {", ".join(users_in_messages_list)}') #TODO list should not include bot

    #TODO 2023-07-19: This section should probaby be moved to bottom ()
    #Add system 'prompt' to GPT as first entry in list of dictionaries
    # TODO: Add any additional wrappers to the GPT prompt here for:
    #  1. use prefix/suffix user input in the command called by the user
    #  2. include ONLY the list of names from the chat history in the previous n messages
    #       - use {*users_in_messages_list,} to unpack the list
    chatgpt_prompt_meat = f'You are an assistant designed to predict the next {num_bot_responses} response(s) \
        that can come from any of the "usernames" in the conversation history.  Each response should \
            1. come from one of the users that have already participated, \
            2. be roughly 1-2 sentences and ~5 words each maximum, \
            3. not be repetitive of already spoken text \
            4. only be conversation between those that have already participated, in this case: {*users_in_messages_list,} \
            5. Include "name" followed by a colon and then the content of the message for each user in your \
                {num_bot_responses} generated response(s). \
            6. begin with "<<<" followed by the username and then a colon'
    chatgpt_prompt_final = chatgpt_prompt_prefix+". "+chatgpt_prompt_meat+". "+chatgpt_prompt_suffix
    chatgpt_prompt_dict = {'role': 'system','content':chatgpt_prompt_final}
    messages_processed.append(chatgpt_prompt_dict)





    #build the keyvalue pairs to be added to a dictionary and then added to the list messages_processed
    print('-------------------------------------')
    print('------- Loop through messages -------')
    print('-------------------------------------')
    async for message in messages:
    #TODO: Figure out how to get an index retrievable when referencing a <async_generator> object
    #async for index, message in enumerate(messages):
        #print(f'>>> message {index} details:')
        print("is bot message:",message.author.bot)
        print("is system message:", message.author.system)
        print("message content:", message.content)

        #filters messages to exclude bot/system and user command() related messages from the GPT response
        #TODO: Find a way to identify a bot gneerated GPT response and then chagne the structure so that:
        # 1. the gpt response (which should be prefixed with "username:" is reformatted to be input 
        #    in the GPT messages list of dictionaried messages)
        # 2. lorem ips
        if message.author.bot == False and message.author.system == False or not message.content.startswith('!'):
            authorname = message.author.name
            authorrole = 'user'
            messagecontent = message.content
            message_as_dictionary = {"role": authorrole, "name": authorname, "content": authorname+": "+messagecontent}
            messages_processed.append(message_as_dictionary)

        else:
            print('this was either a system/bot generated response or was a command issued to a bot\
                  by a user')
            #next







    #
    print('-----------------------------------------------------------------')
    print('------- Execute API call and send response to discord bot -------')
    print('-----------------------------------------------------------------')

    #View what is submitted to chatgpt and then send the request to GPT
    print('usernames to be used in GPT response:') 
    print(users_in_messages_list)
    print('final message history dictionary used for GPT response:') 
    print(messages_processed)

    if skip_response == False:
        #attach openai api key
        openai.api_key = OPENAI_API_KEY

        #request to openai
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages_processed
        )
        
        #review what's been provided by GPT
        gpt_response = completion.choices[0].message['content']
        print("completion object is of type:",type(completion))
        print("Completion message:")
        print(completion.choices[0].message)

        #send the gpt response as discord bot message
        await ctx.send(gpt_response)
    else:
        #TODO: print prettier!  pp = pprint.PrettyPrinter(indent=4) pp.newline = '\n\n' pp.pprint(mylistofdictionaries)
        help_message = "This is what will be received by GPT, including the prompt and the chat history\nNote:\
            If you can see this, the bot is currently not retrieving responses from GPT\nNote: The\
            structure is a list of dictionaries and includes the following:\n1. Dictionary\
            including the prompt to be received by GPT\n2. n Dictionaries, one for each of the\
            messages used by GPT to generate a response"
        await ctx.send(help_message)
        await ctx.send(messages_processed)



















        # Ignore the message if it's from the bot itself
        # ...

        # Process the received message
        # ...

            # If necessary, preprocess the message (e.g., remove bot mentions, trim excess whitespace)
            # ...

            # Send the message to the OpenAI ChatGPT API
            # ...

                # Handle the API request, including setting the appropriate headers and body
                # ...

                # Make the API request and handle any potential errors
                # ...

            # Parse the response from the OpenAI ChatGPT API
            # ...

                # Extract the generated message from the response
                # ...

            # Post the generated message to the Discord server
            # ...

#run the bot
bot.run(DISCORD_BOT_KEY)

# Call the function with the necessary API keys
# ...