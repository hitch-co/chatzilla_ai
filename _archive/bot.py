#NOTE
#2023-05-27 -- GPT response states 'not enough context' (see commit.)  Have tested the output from
# console directly in gpt 3.5 and it works fine.  Next steps:
# - Check API limit/$ceiling?
# - Try to confirm the format of the list of dictionaries [{'system':'content'},{userN:'content'}]
# - 2023-07-19: Try gpt4!
# Move keys to config file/.env file

#imports
import os
from dotenv import load_dotenv

#imports built for bot
from _old.config import load_parameters

#imports used in bot
import discord #not sure of whether the below is redundant, include import into
    # any scripts where discord API is requested
from discord.ext import commands #move to chatforme/get_user_list and anywhere 
    # where the discord api is requested 


#TODO: Feels like the below is where the client shoudl be instantiated but looks like
#   it should be done MULTIPLE TIMES, once within each command (chatforme_help, e.g.
#   chatforme_main, get_channel_idin 
#create the client -- sometimes tutorials use intents "all" instead of "default"
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())


# #import commands
# async def load_commands() -> None:
#     "The code in this function is executed whenever the bot will start."
#     for file in os.listdir(f"{os.path.realpath(os.path.dirname(__name__))}/modules/commands"):
#         if file.endswith(".py"):
#             #extension = file[:-3]
#             try:
#                 await bot.load_extension(f"modules.commands") #removed{extension}
#                 bot.logger.info(f"Loaded extension") #removed - '{extension}'")
#                 print(f"Loaded Extension {__name__}")
#             except Exception as e:
#                 exception = f"{type(e).__name__}: {e}"
#                 bot.logger.error(f"Failed to load extension\n{exception}\n") #removed  {extension}\n{exception}")

#asyncio.run(load_commands())
#load_commands()

#NOTE: wants me to opotentially create a class full of commands to gbe loaded via: 
# https://stackoverflow.com/questions/62351392/load-extension-in-python-discordpy
bot.load_extension("modules.commands.chatforme_main")

#run the client
bot.run(os.getenv("DISCORD_BOT_KEY"))