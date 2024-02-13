from threading import Thread
import asyncio
import os

from config.DependencyInjector import DependencyInjector
from classes.TwitchBotClass import Bot

# Global variable to track the bot thread
TWITCH_CHATFORME_BOT_THREAD = None

def start_bot_thread(config, logger):
    global TWITCH_CHATFORME_BOT_THREAD

    if TWITCH_CHATFORME_BOT_THREAD is None or not TWITCH_CHATFORME_BOT_THREAD.is_alive():
        TWITCH_CHATFORME_BOT_THREAD = Thread(target=run_bot, args=(config,))
        TWITCH_CHATFORME_BOT_THREAD.start()
        logger.info("Twitch bot thread started.")
    else:
        logger.info("Twitch bot thread is already running.")

def run_bot(config):

    #asyncio event loop
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    
    #dependency injector
    dependencies = DependencyInjector(config = config)
    dependencies.create_dependencies()

    #instantiate the class
    bot = Bot(
        TWITCH_BOT_ACCESS_TOKEN = os.environ["TWITCH_BOT_ACCESS_TOKEN"], 
        config=config,
        gpt_client=dependencies.gpt_client,
        bq_uploader=dependencies.bq_uploader,
        tts_client=dependencies.tts_client,
        message_handler=dependencies.message_handler
        )
    bot.run()

