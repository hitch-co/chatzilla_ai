import asyncio

from my_modules.gpt import openai_gpt_chatcompletion, prompt_text_replacement, combine_msghistory_and_prompttext
from my_modules.my_logging import create_logger

runtime_logger_level = 'DEBUG'

class VibeCheckService:
    def __init__(self, yaml_config, message_handler, botclass, vibechecker_players):

        self.logger = create_logger(
            dirname='log', 
            logger_name='logger_VibecheckService', 
            debug_level=runtime_logger_level,
            mode='w',
            stream_logs=True,
            encoding='UTF-8'
            )

        #Bot
        self.botclass = botclass

        #message handler
        self.message_handler = message_handler
        
        #constants
        self.is_vibecheck_loop_active = False
        self.vibechecker_players = vibechecker_players
        self.vibecheckee_username = vibechecker_players['vibecheckee_username']
        self.vibechecker_username = vibechecker_players['vibechecker_username']
        self.vibecheckbot_username = vibechecker_players['vibecheckbot_username']
        self.vibecheck_message_wordcount = yaml_config['vibechecker_max_wordcount']
        self.vibechecker_max_interaction_count = yaml_config['vibechecker_max_interaction_count']
        self.vibechecker_interactions_counter = 0
        self.vibechecker_question_session_sleep_time = yaml_config['vibechecker_question_session_sleep_time']

        #prompts
        self.formatted_gpt_vibecheck_prompt = yaml_config['formatted_gpt_vibecheck_prompt']
        self.formatted_gpt_viberesult_prompt =  yaml_config['formatted_gpt_viberesult_prompt']

    def start_vibecheck_session(self):
        self.is_vibecheck_loop_active = True

        # Start the vibe check logic (e.g., initiating a task or loop)
        self.loop = asyncio.get_event_loop()
        self.vibechecker_task = self.loop.create_task(self._vibechecker_question_session())

    # def process_message(self, message_username):
    #     if self.is_vibecheck_loop_active and message_username == self.vibecheckee_username:
    #         # Process the message for vibe check
    #         pass  # Implement your message processing logic here

    async def stop_vibecheck_session(self):
        self.vibecheckee_username = None
        self.is_vibecheck_loop_active = False

        # Implement any cleanup or state resetting logic here
        self.vibechecker_task.cancel()
        try:
            await self.vibechecker_task  # Await the task to ensure it's fully cleaned up
        except asyncio.CancelledError:
            self.logger.debug("(message from stop_vibechecker_loop()) -- Task was cancelled and cleanup is complete")

    async def _vibechecker_question_session(self):
        self.logger.info("-----------------------------------------------------------------------------")
        self.logger.info(f"------------ Vibe-check Quetsion/Answer Session static variables ------------")
        self.logger.info(f"vibecheckee_username: {self.vibechecker_players}")
        self.logger.debug(f"Initial self.message_handler.vc_msg_history: {self.message_handler.vc_msg_history}")
        
        try:
            while True:
                if self.is_vibecheck_loop_active is False:
                    await asyncio.sleep(self.vibechecker_question_session_sleep_time)
                    continue

                else:
                    self.vibechecker_interactions_counter += 1
                    self.logger.warning(f"------------ Starting cycle #{self.vibechecker_interactions_counter} of the Vibechecker ------------")

                    # Filter the list for items containing the name pattern of any important player
                    self.message_handler.vc_msg_history = [
                        item for item in self.message_handler.vc_msg_history 
                        if any(f'<<<{player_name}>>>' in item['content'] for player_name in self.vibechecker_players.values())
                    ]
                    self.logger.debug(f"THIS IS THE vc_msg_history at the start of cycle {self.vibechecker_interactions_counter}: {self.message_handler.vc_msg_history}")

                    if self.vibechecker_interactions_counter > self.vibechecker_max_interaction_count:
                        await self.stop_vibecheck_session
                        break

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
                    self.logger.warning("THIS IS THE vc_msg_history BEFORE combining the prompt and the message history into a TEMPORARY scoped var")
                    self.logger.warning(self.message_handler.vc_msg_history)

                    #Create message_dict from prompt and add the prompt to the message history
                    vibecheckee_message_dict = combine_msghistory_and_prompttext(
                        prompt_text=vibechecker_prompt,
                        prompt_text_role='user',
                        prompt_text_name='',
                        msg_history_list_dict=self.message_handler.vc_msg_history,
                        output_new_list=True
                        )
                    
                    self.logger.warning(f"vibecheckee_message_dict (TEMPORARY):")
                    self.logger.warning(vibecheckee_message_dict)

                    self.logger.warning("THIS IS THE vc_msg_history AFTER combining the prompt and the message history into a TEMPORARY scoped var called vibecheckee_message_dict")
                    self.logger.warning(self.message_handler.vc_msg_history)

                    gpt_response = openai_gpt_chatcompletion(
                        messages_dict_gpt=vibecheckee_message_dict
                        )  

                    self.logger.warning("THIS IS THE vc_msg_history BEFORE creating the gpt response dictionary")
                    self.logger.warning(self.message_handler.vc_msg_history)

                    gpt_response_dict = self.message_handler._create_gpt_message_dict_from_strings(
                        content = gpt_response,
                        role = 'system',
                        name = self.vibecheckbot_username
                        )
                    self.logger.warning(f"THIS IS THE gpt_response: {gpt_response}")
                    self.logger.warning("THIS IS THE gpt_response_dict")
                    self.logger.warning(gpt_response_dict)

                    self.logger.warning("THIS IS THE vc_msg_history BEFORE appending the gpt response dictionary")
                    self.logger.warning(self.message_handler.vc_msg_history)

                    self.message_handler.vc_msg_history.append(gpt_response_dict)
                    
                    self.logger.warning("THIS IS THE vc_msg_history AFTER appending the gpt response dictionary")
                    self.logger.warning(self.message_handler.vc_msg_history)

                    await self.botclass.channel.send(gpt_response)
                    await asyncio.sleep(self.vibechecker_question_session_sleep_time)

        except asyncio.CancelledError:
            # Handle cancellation here
            self.logger.debug("(message from vibechecker_question_session()) -- Task was cancelled and cleanup is complete")
            return
