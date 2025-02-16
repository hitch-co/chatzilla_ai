import asyncio
import random 

from classes.ConfigManagerClass import ConfigManager

from my_modules.my_logging import create_logger
from models.task import AddMessageTask, CreateExecuteThreadTask

runtime_logger_level = 'DEBUG'

class VibeCheckService:
    def __init__(
            self,
            message_handler,
            gpt_assistant_mgr,
            task_manager,
            gpt_response_mgr,
            vibechecker_players,
            send_channel_message
            ):

        self.logger = create_logger(
            dirname='log', 
            logger_name='logger_VibecheckService', 
            debug_level=runtime_logger_level,
            mode='w',
            stream_logs=True,
            encoding='UTF-8'
            )

        # Config
        self.config = ConfigManager.get_instance()

        #create vc event
        self.vibecheck_ready_event = asyncio.Event()
        
        #Bot (send channel function)
        self.send_channel_message = send_channel_message

        #message handler
        self.message_handler = message_handler

        #gpt manager
        self.gpt_assistant_mgr = gpt_assistant_mgr
        self.gpt_response_mgr = gpt_response_mgr

        #task manager
        self.task_manager = task_manager
        
        #constants
        self.is_vibecheck_loop_active = False
        self.vibechecker_interactions_counter = 0
        self.vibecheck_message_wordcount = self.config.vibechecker_message_wordcount
        self.vibechecker_max_interaction_count = self.config.vibechecker_max_interaction_count
        self.vibechecker_question_session_sleep_time = self.config.vibechecker_question_session_sleep_time
        self.vibechecker_listener_sleep_time = self.config.vibechecker_listener_sleep_time

        self.vibechecker_players = vibechecker_players
        self.vibecheckee_username = self.vibechecker_players['vibecheckee_username']
        self.vibechecker_username = self.vibechecker_players['vibechecker_username']
        self.vibecheckbot_username = self.vibechecker_players['vibecheckbot_username']

        self.logger.info(f"Initialized VibecheckService with vibechecker_username: {self.vibechecker_username}")

    async def start_vibecheck_session(self):
        # Start the vibe check logic (e.g., initiating a task or loop)
        self.is_vibecheck_loop_active = True
        self.loop = asyncio.get_event_loop()
        self.vibechecker_task = self.loop.create_task(self._vibechecker_question_session())
        self.logger.info("Vibecheck session has started...")

    async def process_vibecheck_message(self, message_username, message_content):
        if self.is_vibecheck_loop_active and message_username == self.vibecheckee_username: 
            # Set the event if the criteria is met
            self.logger.info(f"...vibecheck message received from {message_username} with content: {message_content}")

            # Add the message to the 'vibecheckmsgs' thread via queue
            task = AddMessageTask(self.vibecheck_thread_name, message_content)
            await self.task_manager.add_task_to_queue(self.vibecheck_thread_name, task)

            self.vibecheck_ready_event.set()
            pass
        else:
            self.logger.info(f"...vibecheck message received from user who is not the vibecheckee ({self.vibecheckee_username})")

    async def stop_vibecheck_session(self):
        if self.vibechecker_task:
            await self._vibecheck_cleanup()
            self.vibechecker_task.cancel()
            try:
                await self.vibechecker_task
                self.logger.debug("...vibecheck session stopped successfully")
            except asyncio.CancelledError:
                self.logger.debug("...vibecheck session stop ran into an error")

    async def _vibecheck_cleanup(self):
        self.is_vibecheck_loop_active = False
        self.vibechecker_interactions_counter = 0
        self.vibechecker_players = {}
        self.vibecheckee_username = None
        self.vibechecker_username = None
        self.vibecheck_ready_event.clear()
        self.logger.info("...vibecheck cleanup is complete")

        await asyncio.sleep(1)
        self.is_cleanup_in_progress = False
        
    async def _vibechecker_question_session(self):
        self.logger.info(f"...vibechecker_players: {self.vibechecker_players}")
        self.logger.debug(f"...self.message_handler.all_msg_history_gptdict contains {len(self.message_handler.all_msg_history_gptdict)} items") 
        self.logger.debug(f"...self.message_handler.all_msg_history_gptdict: {self.message_handler.all_msg_history_gptdict}")
        
        try:
            while self.is_vibecheck_loop_active:
                self.vibechecker_interactions_counter += 1
                self.logger.info(f"...starting cycle #{self.vibechecker_interactions_counter} of the Vibechecker")

                if self.vibechecker_interactions_counter > self.vibechecker_max_interaction_count:
                    self.logger.debug("...max interaction count reached, stopping vibe check session.")
                    await self._vibecheck_cleanup()
                    break
                
                elif self.vibechecker_interactions_counter == 1:
                    vibechecker_prompt = self.config.formatted_gpt_vibecheck_alert

                elif self.vibechecker_interactions_counter < self.vibechecker_max_interaction_count:
                    vibechecker_prompt = self.config.formatted_gpt_vibecheck_prompt

                elif self.vibechecker_interactions_counter == self.vibechecker_max_interaction_count:                    
                    vibechecker_prompt = self.config.formatted_gpt_viberesult_prompt 

                assistant_name = 'vibechecker'
                self.vibecheck_thread_name = 'vibecheckmsgs'
                tts_voice = self.config.tts_voice_vibecheck

                #Prompt text replacement
                self.logger.info(f"...this is the vibechecker_prompt: {vibechecker_prompt}")
                replacements_dict = {
                        "vibecheckee_username":self.vibecheckee_username,
                        "vibechecker_username":self.vibechecker_username,
                        "vibecheck_message_wordcount":self.vibecheck_message_wordcount
                    }

                # Add a executeTask to the queue
                task = CreateExecuteThreadTask(
                    thread_name=self.vibecheck_thread_name,
                    assistant_name=assistant_name,
                    thread_instructions=vibechecker_prompt,
                    replacements_dict=replacements_dict,
                    tts_voice=tts_voice,
                    model_vendor_config={"vendor": self.config.twitch_bot_vibecheck_service_model_provider, "model": self.config.deepseek_model}
                )
                await self.task_manager.add_task_to_queue(self.vibecheck_thread_name, task)

                # Wait for either the event to be set or the timer to run out
                try:
                    await asyncio.wait_for(
                        self.vibecheck_ready_event.wait(), 
                        self.vibechecker_question_session_sleep_time
                    )
                except asyncio.TimeoutError:
                    pass  # Timeout occurred, continue as normal

                if self.vibecheck_ready_event.is_set():
                    self.vibecheck_ready_event.clear()

        except asyncio.CancelledError:
            self.logger.debug("...vibecheck ran into an error")

        finally:
            await self._vibecheck_cleanup()
