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

        self.dependencies = DependencyInjector(config=self.config)
        self.dependencies.create_dependencies()

    def start_bot(self, twitch_auth):
        if self.bot_thread is None or not self.bot_thread.is_alive():
            self.bot_thread = Thread(target=self._run_bot, args=(twitch_auth,))
            self.bot_thread.start()
            self.logger.info("Twitch bot thread started.")
        else:
            self.logger.info("Twitch bot thread is already running.")

    def _run_bot(self, twitch_auth):
        # Set up a new asyncio event loop for the thread
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)

        # Instantiate and start the bot
        Bot(
            config=self.config,
            gpt_client=self.dependencies.gpt_client,
            bq_uploader=self.dependencies.bq_uploader,
            tts_client=self.dependencies.tts_client,
            gpt_thread_mgr=self.dependencies.gpt_thread_mgr,
            gpt_assistant_mgr=self.dependencies.gpt_assistant_mgr,
            gpt_response_mgr=self.dependencies.gpt_response_mgr,
            gpt_function_call_mgr=self.dependencies.gpt_function_call_mgr,
            message_handler=self.dependencies.message_handler,
            twitch_auth=twitch_auth
        ).run()