import asyncio

from my_modules.gpt import openai_gpt_chatcompletion, prompt_text_replacement, combine_msghistory_and_prompttext
from my_modules.my_logging import create_logger

runtime_logger_level = 'DEBUG'

class VibeCheckService:
    def __init__(
            self, 
            yaml_config, 
            message_handler, 
            botclass, 
            vibechecker_players
            ):

        self.logger = create_logger(
            dirname='log', 
            logger_name='logger_VibecheckService', 
            debug_level=runtime_logger_level,
            mode='w',
            stream_logs=True,
            encoding='UTF-8'
            )

        #create vc event
        self.vibecheck_ready_event = asyncio.Event()
        
        #Bot
        self.botclass = botclass

        #message handler
        self.message_handler = message_handler
        
        #constants
        self.is_vibecheck_loop_active = False
        self.vibechecker_interactions_counter = 0
        self.vibechecker_players = vibechecker_players
        self.vibecheckee_username = vibechecker_players['vibecheckee_username']
        self.vibechecker_username = vibechecker_players['vibechecker_username']
        self.vibecheckbot_username = vibechecker_players['vibecheckbot_username']
        self.vibecheck_message_wordcount = yaml_config.vibechecker_message_wordcount
        self.vibechecker_max_interaction_count = yaml_config.vibechecker_max_interaction_count
        self.vibechecker_question_session_sleep_time = yaml_config.vibechecker_question_session_sleep_time
        self.vibechecker_listener_sleep_time = yaml_config.vibechecker_listener_sleep_time

        #prompts
        self.formatted_gpt_vibecheck_prompt = yaml_config.formatted_gpt_vibecheck_prompt
        self.formatted_gpt_viberesult_prompt =  yaml_config.formatted_gpt_viberesult_prompt
        self.formatted_gpt_vibecheck_alert = yaml_config.formatted_gpt_vibecheck_alert

    def start_vibecheck_session(self):
        self.is_vibecheck_loop_active = True

        # Start the vibe check logic (e.g., initiating a task or loop)
        self.loop = asyncio.get_event_loop()
        self.vibechecker_task = self.loop.create_task(self._vibechecker_question_session())

    def process_vibecheck_message(self, message_username):
        if self.is_vibecheck_loop_active and message_username == self.vibecheckee_username:
            # 1. Set the event if the criteria is met
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
        if hasattr(self.botclass, 'vibecheck_service'):
            self.botclass.vibecheck_service = None
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
                        vibechecker_prompt = self.formatted_gpt_vibecheck_alert

                    elif self.vibechecker_interactions_counter < self.vibechecker_max_interaction_count:
                        vibechecker_prompt = self.formatted_gpt_vibecheck_prompt

                    elif self.vibechecker_interactions_counter == self.vibechecker_max_interaction_count:                    
                        vibechecker_prompt = self.formatted_gpt_viberesult_prompt 

                    #Prompt text replacement
                    replacements_dict = {
                            "vibecheckee_username":self.vibecheckee_username,
                            "vibechecker_username":self.vibechecker_username,
                            "vibecheck_message_wordcount":self.vibecheck_message_wordcount
                        }
                    vibechecker_prompt = prompt_text_replacement(
                        gpt_prompt_text=vibechecker_prompt,
                        replacements_dict = replacements_dict
                        )  
                    self.logger.info(f"vibechecker_prompt: {vibechecker_prompt}")

                    # TODO: This comes from my_modules.gpt -- Should change this
                    #  to come from ChatForMeService.combine_msghistory_and_prompttext
                    #  instead.
                    #Create message_dict from prompt and add the prompt to the message history
                    vibecheckee_message_dict = combine_msghistory_and_prompttext(
                        prompt_text=vibechecker_prompt,
                        prompt_text_role='user',
                        prompt_text_name='',
                        msg_history_list_dict=self.message_handler.all_msg_history_gptdict,
                        output_new_list=True
                        )
                    
                    self.logger.debug(f"vibecheckee_message_dict (TEMPORARY):")
                    self.logger.debug(vibecheckee_message_dict)

                    gpt_response = openai_gpt_chatcompletion(
                        messages_dict_gpt=vibecheckee_message_dict
                        )  
                    gpt_response_dict = self.message_handler._create_gpt_message_dict_from_strings(
                        content = gpt_response,
                        role = 'system',
                        name = self.vibecheckbot_username
                        )
                    self.logger.debug(f"THIS IS THE gpt_response: {gpt_response}")
                    self.logger.debug("THIS IS THE gpt_response_dict")
                    self.logger.debug(gpt_response_dict)

                    self.message_handler.all_msg_history_gptdict.append(gpt_response_dict)

                    #Send the nth response to vibechecker_question_session
                    await self.botclass.channel.send(gpt_response)
                    
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
