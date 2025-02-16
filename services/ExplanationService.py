import asyncio
import random

from my_modules.my_logging import create_logger
from classes.ConfigManagerClass import ConfigManager
from classes.TaskManagerClass import TaskManager

from models.task import CreateExecuteThreadTask

runtime_logger_level = 'INFO'
class ExplanationService:
    def __init__(self, config, task_manager, message_handler):
        self.config = config
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

        self.thread_name = 'explanationmsgs'
        self.assistant_name = 'explainer'

        # NOTE: Why is this instantiated twice?
        #initialize the task manager
        self.task_manager = task_manager
        self.logger.info(f"Initialized ExplanationService with explanation_max_counter: {self.explanation_max_counter}")

    async def explanation_start(self, message, *args):
        self.logger.info(f"Starting explanation, self.explanation_counter is at {self.explanation_counter} (of {self.explanation_max_counter})")

        # Log message details
        self.logger.info(f"...args: {args}")
        self.logger.debug("...logging message object (ctx) details:")
        self.logger.debug(f"...message.author.name: {message.author.name}")
        self.logger.debug(f"...message.content: {message.message.content}")
        self.logger.debug(f"...joined args: {' '.join(args)}")
        self.logger.debug(f"...self.is_explanation_loop_active: {self.is_explanation_loop_active}")
        
        # Ensure that args has at least one element
        if len(args) > 0:
            first_arg = args[0].strip()

            # Check if the first argument is numeric
            if first_arg.isnumeric():
                self.explanation_max_counter = int(first_arg)
                self.logger.info(f"...setting newly requested explanation_max_counter to {self.explanation_max_counter}")
                user_requested_explanation = ' '.join(args[1:])
            else:
                self.logger.debug(f"...first argument is not numeric: {first_arg}")

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
            thread_name = self.thread_name
            assistant_name = self.assistant_name #NOTE: maybe should be a new explaination assistant instead of storyteller

            # Randomly select voice/tone/style/theme from list, set replacements dictionary
            self.current_story_voice = self.config.tts_voice_story

            # Log the story details
            self.logger.info(f"...an explanation was started by {message.author.name} ({message.author.id})")
            self.logger.info(f"...thread_name and assistant_name: {thread_name}, {assistant_name}")
            self.logger.info(f"...user_requested_explanation: {user_requested_explanation}")
            self.logger.info(f"...current_story_voice: {self.current_story_voice}")

            if user_requested_explanation is not None:   
                self.logger.info(f"...this is the requested explanation: {user_requested_explanation}")

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
                tts_voice=self.current_story_voice,
                model_vendor_config={"vendor": self.config.twitch_bot_explanation_service_model_provider, "model": self.config.deepseek_model}
                )
            self.logger.debug(f"...task to add to queue: {task.task_dict}")
            await self.task_manager.add_task_to_queue_and_execute(thread_name, task, description="ExecuteThreadTask 'explanation_start'")
            self.is_explanation_loop_active = True

    async def explanation_task(self):
        
        #This is the while loop that generates the occurring GPT response
        while True:
            if not self.is_explanation_loop_active:
                await asyncio.sleep(self.loop_sleep_time)
                continue

            else:
                self.explanation_counter += 1
                self.logger.info(f"...starting cycle #{self.explanation_counter} of the Explanation Service loop") 

                #explanation_starter, explanation_progressor, explanation_ender
                if self.explanation_counter <=2:
                    gpt_prompt_detail = self.config.explanation_starter
                elif self.explanation_counter <= self.config.explanation_progression_number:
                    gpt_prompt_detail = self.config.explanation_progressor
                elif self.explanation_counter >= self.explanation_max_counter:
                    gpt_prompt_detail = self.config.explanation_ender

                # Combine prefix and final article content
                gpt_prompt_final = gpt_prompt_detail + " " + self.config.explanation_suffix
                assistant_name = self.assistant_name
                thread_name = self.thread_name
                tts_voice = self.current_story_voice

                self.logger.info(f"...the self.explanation_counter is currently at {self.explanation_counter} (explanation_max_counter={self.explanation_max_counter})")
                self.logger.info(f"...explanation Service gpt_prompt_final: '{gpt_prompt_final}'")

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
                    tts_voice=tts_voice,
                    model_vendor_config={"vendor": self.config.twitch_bot_explanation_service_model_provider, "model": self.config.deepseek_model}
                    )
                await self.task_manager.add_task_to_queue_and_execute(thread_name, task, description="ExecuteThreadTask 'explanation_task'")

            # Check if the explanation loop should be stopped
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