from threading import Thread
import asyncio
import os

from config.DependencyInjector import DependencyInjector
from classes.TwitchBotClass import Bot

class TwitchBotManager:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.bot_thread = None

    def start_bot_thread(self):
        if self.bot_thread is None or not self.bot_thread.is_alive():
            self.bot_thread = Thread(target=self.run_bot)
            self.bot_thread.start()
            self.logger.info("Twitch bot thread started.")
        else:
            self.logger.info("Twitch bot thread is already running.")

    def run_bot(self):
        # Set up a new asyncio event loop for the thread
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)

        # Set up dependencies
        dependencies = DependencyInjector(config=self.config)
        dependencies.create_dependencies()

        # Instantiate and start the bot
        bot = Bot(
            TWITCH_BOT_ACCESS_TOKEN=os.environ["TWITCH_BOT_ACCESS_TOKEN"],
            config=self.config,
            gpt_client=dependencies.gpt_client,
            bq_uploader=dependencies.bq_uploader,
            tts_client=dependencies.tts_client,
            message_handler=dependencies.message_handler
        ).run()