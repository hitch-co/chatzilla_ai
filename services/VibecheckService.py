import asyncio
import random 

from classes.ConfigManagerClass import ConfigManager

from my_modules.my_logging import create_logger
from models.task import AddMessageTask, ExecuteThreadTask
from models.task import ExecuteThreadTask

runtime_logger_level = 'DEBUG'

class VibeCheckService:
    def __init__(
            self,
            message_handler,
            gpt_assistant_mgr,
            gpt_thread_mgr,
            gpt_response_mgr,
            chatforme_service,
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
        self.gpt_thread_mgr = gpt_thread_mgr
        self.gpt_response_mgr = gpt_response_mgr

        #ChatForMeService
        self.chatforme_service = chatforme_service
        
        #constants
        self.is_vibecheck_loop_active = False
        self.vibechecker_interactions_counter = 0
        self.vibechecker_players = vibechecker_players
        self.vibecheckee_username = vibechecker_players['vibecheckee_username']
        self.vibechecker_username = vibechecker_players['vibechecker_username']
        self.vibecheckbot_username = vibechecker_players['vibecheckbot_username']
        self.vibecheck_message_wordcount = self.config.vibechecker_message_wordcount
        self.vibechecker_max_interaction_count = self.config.vibechecker_max_interaction_count
        self.vibechecker_question_session_sleep_time = self.config.vibechecker_question_session_sleep_time
        self.vibechecker_listener_sleep_time = self.config.vibechecker_listener_sleep_time

    def start_vibecheck_session(self):
        self.is_vibecheck_loop_active = True

        # Start the vibe check logic (e.g., initiating a task or loop)
        self.loop = asyncio.get_event_loop()
        self.vibechecker_task = self.loop.create_task(self._vibechecker_question_session())

    async def process_vibecheck_message(self, message_username, message_content):
        if self.is_vibecheck_loop_active and message_username == self.vibecheckee_username: 
            # Set the event if the criteria is met

            # Add the bullet list to the 'ouatmsgs' thread via queue
            thread_name = 'vibecheckmsgs'
            task = AddMessageTask(thread_name, message_content).to_dict()
            await self.gpt_thread_mgr.add_task_to_queue(thread_name, task)

            self.vibecheck_ready_event.set()
            pass

    async def stop_vibecheck_session(self):
        self.vibechecker_task.cancel()
        try:
            await self.vibechecker_task  # Await the task to ensure it's fully cleaned up
        except asyncio.CancelledError:
            self.logger.debug("Cancellation requested for vibechecker task.")

        self.vibecheckee_username = None
        self.is_vibecheck_loop_active = False

        self.logger.debug("General cleanup of vibecheckee_username/loop status and vibecheck service completed")

    async def _vibechecker_question_session(self):
        self.logger.info("-----------------------------------------------------------------------------")
        self.logger.info(f"------------ Vibe-check Quetsion/Answer Session static variables ------------")
        self.logger.info(f"vibecheckee_username: {self.vibechecker_players}")
        self.logger.debug(f"Initial self.message_handler.all_msg_history_gptdict: {self.message_handler.all_msg_history_gptdict}")
        
        try:
            while True:
                if self.is_vibecheck_loop_active is False:
                    await asyncio.sleep(self.vibechecker_listener_sleep_time)
                    continue

                else:
                    self.vibechecker_interactions_counter += 1
                    self.logger.info(f"------------ Starting cycle #{self.vibechecker_interactions_counter} of the Vibechecker ------------")

                    # Filter the list for items containing the name pattern of any important player
                    self.message_handler.all_msg_history_gptdict = [
                        item for item in self.message_handler.all_msg_history_gptdict 
                        if any(f'<<<{player_name}>>>' in item['content'] for player_name in self.vibechecker_players.values())
                    ]

                    if self.vibechecker_interactions_counter > self.vibechecker_max_interaction_count:
                        await self.stop_vibecheck_session()
                        break
                    
                    elif self.vibechecker_interactions_counter == 1:
                        vibechecker_prompt = self.config.formatted_gpt_vibecheck_alert

                    elif self.vibechecker_interactions_counter < self.vibechecker_max_interaction_count:
                        vibechecker_prompt = self.config.formatted_gpt_vibecheck_prompt

                    elif self.vibechecker_interactions_counter == self.vibechecker_max_interaction_count:                    
                        vibechecker_prompt = self.config.formatted_gpt_viberesult_prompt 

                    assistant_name = 'vibechecker'
                    thread_name = 'vibecheckmsgs'
                    tts_voice = self.config.tts_voice_vibecheck

                    #Prompt text replacement
                    self.logger.debug(f"This is the vibechecker_prompt: {vibechecker_prompt}")
                    replacements_dict = {
                            "vibecheckee_username":self.vibecheckee_username,
                            "vibechecker_username":self.vibechecker_username,
                            "vibecheck_message_wordcount":self.vibecheck_message_wordcount
                        }

                    # Add a executeTask to the queue
                    task = ExecuteThreadTask(
                        thread_name=thread_name,
                        assistant_name=assistant_name,
                        thread_instructions=vibechecker_prompt,
                        replacements_dict=replacements_dict,
                        tts_voice=tts_voice
                    ).to_dict()
                    await self.gpt_thread_mgr.add_task_to_queue(thread_name, task)

                    # Wait for either the event to be set or the timer to run out
                    try:
                        await asyncio.wait_for(self.vibecheck_ready_event.wait(), self.vibechecker_question_session_sleep_time)
                    except asyncio.TimeoutError:
                        pass  # Timeout occurred, continue as normal

                    if self.vibecheck_ready_event.is_set():
                        self.vibecheck_ready_event.clear()

        except asyncio.CancelledError:
            # Handle cancellation here
            self.logger.debug("(message from vibechecker_question_session()) -- Task was cancelled and cleanup is complete")
            return
