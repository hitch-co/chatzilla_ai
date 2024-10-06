import asyncio
import random

from my_modules.my_logging import create_logger
from classes.ConfigManagerClass import ConfigManager

from models.task import CreateExecuteThreadTask

runtime_logger_level = 'INFO'
class ExplanationService:
    def __init__(self, config, gpt_thread_mgr, message_handler):
        self.config = config
        self.gpt_thread_mgr = gpt_thread_mgr
        self.message_handler = message_handler

        self.logger = create_logger(
            debug_level=runtime_logger_level,
            logger_name='logger_ExplanationService',
            mode='w',
            stream_logs=True
            )
        self.yaml_data = ConfigManager.get_instance()

        self.loop_sleep_time = 5
        self.is_explanation_loop_active = False
        self.explanation_counter = 0
        self.explanation_max_counter = self.config.explanation_max_counter_default

    async def explanation_start(self, message, *args):
        self.logger.info(f"Starting explanation, self.explanation_counter is at {self.explanation_counter} (of {self.explanation_max_counter})")

        # Log message details
        self.logger.info(f"...args: {args}")
        self.logger.debug("...Logging message object (ctx) details:")
        self.logger.debug(f"...message.author.name: {message.author.name}")
        self.logger.debug(f"...message.content: {message.message.content}")
        self.logger.debug(f"...Joined args: {' '.join(args)}")
        self.logger.debug(f"...self.is_explanation_loop_active: {self.is_explanation_loop_active}")
        
        # Ensure that args has at least one element
        if len(args) > 0:
            first_arg = args[0].strip()

            # Check if the first argument is numeric
            if first_arg.isnumeric():
                self.explanation_max_counter = int(first_arg)
                self.logger.info(f"...Setting newly requested explanation_max_counter to {self.explanation_max_counter}")
                user_requested_explanation = ' '.join(args[1:])
            else:
                self.logger.warning(f"...First argument is not numeric: {first_arg}")

                #Check to make sure not empty string or empty inputs
                if args == [''] or args == [' ']:
                    user_requested_explanation = None
                else:
                    user_requested_explanation = ' '.join(args)
        else:
            user_requested_explanation = None

        if self.explanation_counter == 0:
            self.explanation_counter += 1

            # Extract the user requested explanation and if '' or ' ', etc. then set to None
            if user_requested_explanation in ['', ' ', None]:
                user_requested_explanation = None

            # Set the thread name and assistant name
            thread_name = 'ouatmsgs'
            assistant_name = 'storyteller' #NOTE: maybe should be a new explaination assistant instead of storyteller

            # Randomly select voice/tone/style/theme from list, set replacements dictionary
            self.current_story_voice = self.config.tts_voice_story

            # Log the story details
            self.logger.info(f"...A explanation was started by {message.author.name} ({message.author.id})")
            self.logger.info(f"...thread_name and assistant_name: {thread_name}, {assistant_name}")
            self.logger.info(f"...user_requested_explanation: {user_requested_explanation}")
            self.logger.info(f"...current_story_voice: {self.current_story_voice}")

            if user_requested_explanation is not None:   
                self.logger.info(f"...This is the requested explanation: {user_requested_explanation}")

            gpt_prompt_text = self.config.explanation_user_opening_summary_prompt + " " + self.config.explanation_suffix    
            replacements_dict = {
                "wordcount_short":self.config.wordcount_short,
                "wordcount_medium":self.config.wordcount_medium,
                "wordcount_long":self.config.wordcount_long,
                "explanation_counter":self.explanation_counter,
                "explanation_max_counter":self.explanation_max_counter,
                "user_requested_explanation":user_requested_explanation,
                }

            # Add executeTask to the queue
            task = CreateExecuteThreadTask(
                thread_name=thread_name,
                assistant_name=assistant_name,
                thread_instructions=gpt_prompt_text,
                replacements_dict=replacements_dict,
                tts_voice=self.current_story_voice
                ).to_dict()
            self.logger.debug(f"Task to add to queue: {task}")

            # Add the bullet list to the 'ouatmsgs' thread via queue
            await self.gpt_thread_mgr.add_task_to_queue(thread_name, task)
            self.is_explanation_loop_active = True

    async def explanation_task(self):
        
        #This is the while loop that generates the occurring GPT response
        while True:
            if self.is_explanation_loop_active is False:
                self.logger.debug(f"OUAT details: Explanation loop is not active, waiting longer...")
                await asyncio.sleep(self.loop_sleep_time)
                continue

            else:
                self.explanation_counter += 1
                self.logger.info(f"OUAT details: Starting cycle #{self.explanation_counter} of the OUAT Storyteller") 

                #storystarter
                if self.explanation_counter <=2:
                    gpt_prompt_detail = self.config.explanation_starter

                #storyprogressor
                elif self.explanation_counter <= self.config.explanation_progression_number:
                    gpt_prompt_detail = self.config.explanation_progressor

                #storyender
                elif self.explanation_counter >= self.explanation_max_counter:
                    gpt_prompt_detail = self.config.explanation_ender

                # Combine prefix and final article content
                gpt_prompt_final = gpt_prompt_detail + " " + self.config.explanation_suffix
                assistant_name = 'storyteller'
                thread_name = 'ouatmsgs'
                tts_voice = self.current_story_voice

                self.logger.info(f"The self.explanation_counter is currently at {self.explanation_counter} (explanation_max_counter={self.explanation_max_counter})")
                self.logger.info(f"Explanation Service gpt_prompt_final: '{gpt_prompt_final}'")

                replacements_dict = {
                    "wordcount_short":self.config.wordcount_short,
                    "wordcount_long":self.config.wordcount_long,
                    'twitch_bot_display_name':self.config.twitch_bot_display_name,
                    'num_bot_responses':self.config.num_bot_responses,
                    "explanation_counter":self.explanation_counter,
                    "explanation_max_counter":self.explanation_max_counter,
                    'param_in_text':'variable_from_scope'
                    }

                # Add a executeTask to the queue
                task = CreateExecuteThreadTask(
                    thread_name=thread_name,
                    assistant_name=assistant_name,
                    thread_instructions=gpt_prompt_final,
                    replacements_dict=replacements_dict,
                    tts_voice=tts_voice
                ).to_dict()
                self.logger.debug(f"Task to add to queue: {task}")

                await self.gpt_thread_mgr.add_task_to_queue(thread_name, task)

            if self.explanation_counter >= self.explanation_max_counter:
                await self.stop_explanation_loop()
            else:
                await asyncio.sleep(int(self.config.explanation_message_recurrence_seconds))

    async def stop_explanation(self, ctx):
        # await self._send_channel_message_wrapper("That's it for now...")
        self.logger.info(f"Stopping the explanation at cycle {self.explanation_counter}.  Note that messages are not sent to twitch because of _send_channel_message_wrapper() being commented out.")
        await self.stop_explanation_loop()

    async def stop_explanation_loop(self) -> None:
        self.is_explanation_loop_active = False
        self.explanation_counter = 0
        self.logger.info(f"Explanation service loop has been stopped, self.ouat_counter has been reset to {self.explanation_counter}")