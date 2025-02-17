from my_modules import utils
import dotenv
import os

from classes.GPTResponseCleanerClass import GPTResponseCleaner
from classes.ConfigManagerClass import ConfigManager
from classes.GPTAssistantManagerClass import GPTBaseClass, GPTThreadManager, GPTResponseManager, GPTAssistantManager

class TaskHandler:
    def __init__(
            self, 
            config,
            task_manager,
            gpt_response_manager,
            deepseek_client,
            tts_client,
            message_handler
        ):
        self.logger = task_manager.logger
        self.task_manager = task_manager
        self.config = config
        self.gpt_response_manager = gpt_response_manager
        self.deepseek_client = deepseek_client
        self.tts_client = tts_client
        self.message_handler = message_handler

        # Set the send_channel_message_wrapper to None and then set it to the actual method in the constructor.
        self._send_channel_message_wrapper = None
        
        # Set up the dispatch table mapping task types to handler methods.
        self.dispatch_table = {
            "add_message": self.handle_add_message,
            "generate_text": self.handle_generate_text,
            "execute_thread": self.handle_execute_thread,
            "send_channel_message": self.handle_send_channel_message
        }

    def set_send_channel_message_wrapper(self, wrapper_callable):
        self._send_channel_message_wrapper = wrapper_callable

    async def handle_tasks(self, task: object):
        try:
            task_type = task.task_dict.get("type")
            thread_name = task.task_dict.get("thread_name")
            self.logger.info(f"Handling task type '{task_type}' for thread: {thread_name}")
        except Exception as e:
            self.logger.error(f"Error occurred in 'handle_tasks': {e}")
            task.future.set_exception(e)
            return

        # Get the lock for the thread.
        lock = self.task_manager.thread_locks[thread_name]
        async with lock:
            handler = self.dispatch_table.get(task_type)
            if not handler:
                error_msg = f"Unsupported task type: {task_type}"
                self.logger.error(error_msg)
                task.future.set_exception(Exception(error_msg))
                return

            # Invoke the dedicated handler.
            await handler(task)

    async def handle_add_message(self, task: object):
        """
        Add a message to the thread's message queue.
        """
        thread_name = task.task_dict.get("thread_name")
        message_role = task.task_dict.get("message_role")
        content = task.task_dict.get("content")

        try:
            await self._add_message_to_specified_thread(
                message_content=content, 
                role=message_role,
                thread_name=thread_name
            )
            message = f"...'add_message' task handled for thread: {thread_name}"
            self.logger.info(message)
        except Exception as e:
            self.logger.error(f"Error in handle_add_message: {e}", exc_info=True)
            task.future.set_exception(e)
            return

        task.future.set_result(message)

    async def handle_generate_text(self, task: object):
        thread_name = task.task_dict.get("thread_name")
        assistant_name = task.task_dict.get("assistant_name")
        prompt = task.task_dict.get("prompt")
        replacements_dict = task.task_dict.get("replacements_dict")
        tts_voice = task.task_dict.get("tts_voice")
        send_channel_message = task.task_dict.get("send_channel_message")
        model_vendor_config = task.task_dict.get("model_vendor_config")
        model_vendor_name = model_vendor_config.get("vendor")
        model_name = model_vendor_config.get("model")
        gpt_response = None

        if model_vendor_name == "openai":
            self.logger.warning("OpenAI vendor not fully QA'd for generate_text")
            try:
                gpt_response = await self.gpt_response_manager.execute_thread(
                    thread_name=thread_name,
                    assistant_name=assistant_name,
                    thread_instructions=prompt,
                    replacements_dict=replacements_dict
                )
                self.logger.info(f"GPT response generated for thread: {thread_name}")
            except Exception as e:
                self.logger.error(f"Error in generate_text (openai): {e}")
                task.future.set_exception(e)
                return
            
        elif model_vendor_name == "deepseek":
            try:
                final_prompt = utils.populate_placeholders(
                    logger=self.logger,
                    prompt_template=prompt + self.config.llm_assistants_suffix,
                    replacements=replacements_dict
                )
                gpt_response = await self.deepseek_client.get_deepseek_response_generate(
                    model=model_name,
                    prompt=final_prompt
                )
                self.logger.info(f"DeepSeek generate_text completed for thread: {thread_name}")
            except Exception as e:
                self.logger.error(f"Error in generate_text (deepseek): {e}")
                task.future.set_exception(e)
                return
            
        else:
            error_msg = f"Unsupported model vendor: {model_vendor_name}"
            self.logger.error(error_msg)
            task.future.set_exception(Exception(error_msg))
            return

        # If we need to send a channel message.
        if gpt_response is not None and send_channel_message:
            gpt_response = GPTResponseCleaner.perform_all_gpt_response_cleanups(gpt_response)
            try:
                await self.send_output_message_and_voice(
                    text=gpt_response,
                    incl_voice=self.config.tts_include_voice,
                    voice_name=tts_voice,
                    send_channel_message_wrapper=self._send_channel_message_wrapper
                )
                message = f"...'generate_text' task handled for thread: {thread_name} and channel message sent."
            except Exception as e:
                self.logger.error(f"Error in send_output_message_and_voice: {e}")
                task.future.set_exception(e)
                return
        elif gpt_response is None:
            error_msg = f"GPT response is None in generate_text task for thread: {thread_name}"
            self.logger.error(error_msg)
            task.future.set_exception(Exception(error_msg))
            return
        else:
            message = f"...'generate_text' task handled for thread: {thread_name}. No channel message sent."

        task.future.set_result(message)

    async def handle_execute_thread(self, task: object):
        thread_name = task.task_dict.get("thread_name")
        assistant_name = task.task_dict.get("assistant_name")
        thread_instructions = task.task_dict.get("thread_instructions")
        replacements_dict = task.task_dict.get("replacements_dict")
        tts_voice = task.task_dict.get("tts_voice")
        send_channel_message = task.task_dict.get("send_channel_message")
        model_vendor_config = task.task_dict.get("model_vendor_config")
        model_vendor_name = model_vendor_config.get("vendor")
        model_name = model_vendor_config.get("model")
        gpt_response = None
        
        if model_vendor_name == "openai":
            try:
                gpt_response = await self.gpt_response_manager.execute_thread(
                    thread_name=thread_name,
                    assistant_name=assistant_name,
                    thread_instructions=thread_instructions,
                    replacements_dict=replacements_dict
                )
                self.logger.info(f"GPT response generated for thread: {thread_name}")
            except Exception as e:
                self.logger.error(f"Error in execute_thread (openai): {e}")
                task.future.set_exception(e)
                return
        elif model_vendor_name == "deepseek":
            try:
                final_instructions = utils.populate_placeholders(
                    logger=self.logger,
                    prompt_template=thread_instructions + self.config.llm_assistants_suffix,
                    replacements=replacements_dict
                )
                gpt_response = await self.deepseek_client.get_deepseek_response_chat(
                    model=model_name,
                    prompt=final_instructions,
                    messages=self.message_handler.all_msg_history_gptdict
                )
                self.logger.info(f"DeepSeek execute_thread completed for thread: {thread_name}")
            except Exception as e:
                self.logger.error(f"Error in execute_thread (deepseek): {e}")
                task.future.set_exception(e)
                return
        else:
            error_msg = f"Unsupported model vendor: {model_vendor_name}"
            self.logger.error(error_msg)
            task.future.set_exception(Exception(error_msg))
            return

        if gpt_response is not None and send_channel_message:
            gpt_response = GPTResponseCleaner.perform_all_gpt_response_cleanups(gpt_response)
            try:
                await self.send_output_message_and_voice(
                    text=gpt_response,
                    incl_voice=self.config.tts_include_voice,
                    voice_name=tts_voice,
                    send_channel_message_wrapper=self._send_channel_message_wrapper
                )
                message = f"...'execute_thread' task handled for thread: {thread_name} and channel message sent."
            except Exception as e:
                self.logger.error(f"Error in send_output_message_and_voice: {e}")
                task.future.set_exception(e)
                return
        elif gpt_response is None:
            error_msg = f"GPT response is None in execute_thread task for thread: {thread_name}"
            self.logger.error(error_msg)
            task.future.set_exception(Exception(error_msg))
            return
        else:
            message = f"...'execute_thread' task handled for thread: {thread_name}. No channel message sent."

        task.future.set_result(message)

    async def handle_send_channel_message(self, task: object):
        thread_name = task.task_dict.get("thread_name")
        content = task.task_dict.get("content")
        tts_voice = task.task_dict.get("tts_voice")
        message_role = task.task_dict.get("message_role")
        
        try:
            await self._add_message_to_specified_thread(
                message_content=content, 
                role=message_role, 
                thread_name=thread_name
            )
            self.logger.info(f"'send_channel_message' task added message for thread: {thread_name}")
        except Exception as e:
            self.logger.error(f"Error in adding message: {e}")
            task.future.set_exception(e)
            return
        
        try:
            await self.send_output_message_and_voice(
                text=content,
                incl_voice=self.config.tts_include_voice,
                voice_name=tts_voice,
                send_channel_message_wrapper=self._send_channel_message_wrapper
            )
            message = f"...'send_channel_message' task handled for thread: {thread_name}"
        except Exception as e:
            self.logger.error(f"Error in sending channel message: {e}")
            task.future.set_exception(e)
            return
        
        task.future.set_result(message)

    async def _add_message_to_specified_thread(self, message_content: str, role: str, thread_name: str) -> None:
        if thread_name in self.config.gpt_thread_names:
            try:
                message_object = await self.gpt_response_manager.add_message_to_thread(
                    message_content=message_content,
                    thread_name=thread_name,
                    role=role
                )
                self.logger.debug(f"Message object: {message_object}")
            except Exception as e:
                self.logger.error(f"Error occurred in 'add_message_to_thread': {e}", exc_info=True)
        else:
            self.logger.error(f"Thread name '{thread_name}' is not in the list of thread names. Message content: {message_content[0:25]+'...'}")

    async def send_output_message_and_voice(
            self,
            text,
            incl_voice,
            voice_name,
            send_channel_message_wrapper: callable
            ):
        """
        Asynchronously sends a text message and optionally plays a voice message.

        This internal method sends a text message to the specified channel and, if requested, generates and plays a voice message using the text-to-speech service.

        Parameters:
        - text (str): The text message to be sent.
        - incl_voice (str): Specifies whether to include voice output (True or False).
        - voice_name (str): The name of the voice to be used in the text-to-speech service.
        """
        datetime_string = utils.get_current_datetime_formatted()['filename_format']
        if incl_voice == True:
            # Generate speech object and generate speech object/mp3
            output_filename = "chatforme_"+"_"+datetime_string+"_"+self.tts_client.tts_file_name
            self.tts_client.workflow_t2s(
                text_input=text,
                voice_name=voice_name,
                output_dirpath=self.tts_client.tts_data_folder,
                output_filename=output_filename
                )

        # TODO: Does this class need botclass injected simply to send messages? 
        if not self._send_channel_message_wrapper:
            raise Exception("send_channel_message_wrapper has not been set in TaskHandler!")
        await self._send_channel_message_wrapper(text)

        if incl_voice == True:
            self.tts_client.play_local_mp3(
                dirpath=self.tts_client.tts_data_folder, 
                filename=output_filename
                )