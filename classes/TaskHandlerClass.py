
import logging
from my_modules import utils

from classes.GPTResponseCleanerClass import GPTResponseCleaner

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
        self.logger = logging.getLogger("my_app.task_handler")
        self.task_manager = task_manager
        self.config = config
        self.gpt_response_manager = gpt_response_manager
        self.deepseek_client = deepseek_client
        self.tts_client = tts_client
        self.message_handler = message_handler
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
        """
        Entry point for handling all tasks. Acquires a lock on the thread and dispatches
        to the appropriate handler based on task_type.
        """
        try:
            # 1) Log the entire task dict as extra info
            log_extra = dict(task.task_dict or {})
            self.logger.info("handle_tasks: Received task", extra=log_extra)

        except Exception as e:
            # If we fail to parse or log, ensure the future gets the exception
            self.logger.error(f"Error occurred in 'handle_tasks': {e}", exc_info=True)
            task.future.set_exception(e)
            return

        # Grab the thread_name from the task dict (already in log_extra, but also needed locally)
        thread_name = task.task_dict.get("thread_name")
        lock = self.task_manager.thread_locks[thread_name]

        async with lock:
            try:
                task_type = task.task_dict.get("type")
                handler = self.dispatch_table.get(task_type)
                if not handler:
                    error_msg = f"Unsupported task type: {task_type}"
                    # Log again with the same extra fields
                    self.logger.error(error_msg, extra=log_extra)
                    task.future.set_exception(Exception(error_msg))
                    return

                # 2) We have the lock, log that fact
                self.logger.debug("Lock acquired, dispatching handler", extra=log_extra)

                # 3) Call the handler
                await handler(task)

            except Exception as exc:
                self.logger.exception("Exception in handle_tasks", extra=log_extra)
                task.future.set_exception(exc)

    async def handle_add_message(self, task: object):
        """
        Add a message to the thread's message queue.
        """
        log_extra = dict(task.task_dict or {})
        try:
            # Add message
            thread_name = task.task_dict.get("thread_name")
            message_role = task.task_dict.get("message_role")
            content = task.task_dict.get("content")

            await self._add_message_to_specified_thread(
                message_content=content, 
                role=message_role,
                thread_name=thread_name
            )
            message = f"TaskHandler.handle_add_message: Task complete for thread='{thread_name}'"
            self.logger.info(message, extra=log_extra)
            task.future.set_result(message)

        except Exception as e:
            self.logger.error("Error in handle_add_message", extra=log_extra, exc_info=True)
            task.future.set_exception(e)

    async def handle_generate_text(self, task: object):
        log_extra = dict(task.task_dict or {})
        thread_name = task.task_dict.get("thread_name")
        model_vendor_config = task.task_dict.get("model_vendor_config", {})
        model_vendor_name = model_vendor_config.get("vendor")
        gpt_response = None

        try:
            if model_vendor_name == "openai":
                self.logger.warning(
                    "OpenAI vendor not fully QA'd for generate_text",
                    extra=log_extra
                )
                gpt_response = await self._handle_generate_openai(task)

            elif model_vendor_name == "deepseek":
                gpt_response = await self._handle_generate_deepseek(task)
            else:
                error_msg = f"Unsupported model vendor: {model_vendor_name}"
                self.logger.error(error_msg, extra=log_extra)
                task.future.set_exception(Exception(error_msg))
                return

            if gpt_response is not None and task.task_dict.get("send_channel_message"):
                # Clean up text if needed
                gpt_response = GPTResponseCleaner.perform_all_gpt_response_cleanups(gpt_response)

                await self._handle_send_channel_message_and_voice(
                    gpt_response,
                    tts_voice=task.task_dict.get("tts_voice"),
                    log_extra=log_extra
                )
                message = f"handle_generate_text: Completed for thread='{thread_name}' (channel msg sent)."

            elif gpt_response is None:
                error_msg = f"GPT response is None in generate_text (thread='{thread_name}')"
                self.logger.error(error_msg, extra=log_extra)
                task.future.set_exception(Exception(error_msg))
                return
            else:
                message = f"handle_generate_text: Completed for thread='{thread_name}' (no channel msg)."

            self.logger.info(message, extra=log_extra)
            task.future.set_result(message)

        except Exception as e:
            self.logger.error("Error in handle_generate_text", extra=log_extra, exc_info=True)
            task.future.set_exception(e)

    async def handle_execute_thread(self, task: object):
        log_extra = dict(task.task_dict or {})
        thread_name = task.task_dict.get("thread_name")
        model_vendor_config = task.task_dict.get("model_vendor_config", {})
        model_vendor_name = model_vendor_config.get("vendor")
        gpt_response = None

        try:
            if model_vendor_name == "openai":
                gpt_response = await self._handle_execute_openai(task)
            elif model_vendor_name == "deepseek":
                gpt_response = await self._handle_execute_deepseek(task)
            else:
                error_msg = f"Unsupported model vendor: {model_vendor_name}"
                self.logger.error(error_msg, extra=log_extra)
                task.future.set_exception(Exception(error_msg))
                return

            if gpt_response is not None and task.task_dict.get("send_channel_message"):
                # Clean the text
                gpt_response = GPTResponseCleaner.perform_all_gpt_response_cleanups(gpt_response)
                await self._handle_send_channel_message_and_voice(
                    gpt_response,
                    tts_voice=task.task_dict.get("tts_voice"),
                    log_extra=log_extra
                )
                message = f"handle_execute_thread: Completed for thread='{thread_name}' (channel msg sent)."
            elif gpt_response is None:
                error_msg = f"GPT response is None in execute_thread (thread='{thread_name}')"
                self.logger.error(error_msg, extra=log_extra)
                task.future.set_exception(Exception(error_msg))
                return
            else:
                message = f"handle_execute_thread: Completed for thread='{thread_name}' (no channel msg)."

            self.logger.info(message, extra=log_extra)
            task.future.set_result(message)

        except Exception as e:
            self.logger.error("Error in handle_execute_thread", extra=log_extra, exc_info=True)
            task.future.set_exception(e)

    async def handle_send_channel_message(self, task: object):
        log_extra = dict(task.task_dict or {})
        thread_name = task.task_dict.get("thread_name")

        try:
            # Add message to specified thread
            content = task.task_dict.get("content")
            message_role = task.task_dict.get("message_role")

            await self._add_message_to_specified_thread(
                message_content=content, 
                role=message_role, 
                thread_name=thread_name
            )
            self.logger.info("Added 'send_channel_message' to thread", extra=log_extra)

            # Now send output (with optional TTS)
            await self._handle_send_channel_message_and_voice(
                content,
                tts_voice=task.task_dict.get("tts_voice"),
                log_extra=log_extra
            )
            message = f"handle_send_channel_message: Completed for thread='{thread_name}'"
            self.logger.info(message, extra=log_extra)
            task.future.set_result(message)

        except Exception as e:
            self.logger.error("Error in handle_send_channel_message", extra=log_extra, exc_info=True)
            task.future.set_exception(e)

    async def _add_message_to_specified_thread(self, message_content: str, role: str, thread_name: str) -> None:
        """
        Internal helper to place message into GPT thread memory or queue.
        """
        if thread_name in self.config.gpt_thread_names:
            try:
                await self.gpt_response_manager.add_message_to_thread(
                    message_content=message_content,
                    thread_name=thread_name,
                    role=role
                )
            except Exception as e:
                self.logger.error(
                    f"Error in '_add_message_to_specified_thread': {e}",
                    exc_info=True
                )
        else:
            snippet = (message_content[:25] + "...") if message_content else ""
            self.logger.error(
                f"Thread '{thread_name}' not in gpt_thread_names. Content snippet: {snippet}"
            )

    async def send_output_message_and_voice(
            self,
            text,
            incl_voice,
            voice_name,
            send_channel_message_wrapper: callable
            ):
        """
        Asynchronously sends a text message and optionally plays a voice message.
        """
        datetime_string = utils.get_current_datetime_formatted()['filename_format']
        if incl_voice:
            output_filename = "chatforme_" + "_" + datetime_string + "_" + self.tts_client.tts_file_name
            self.tts_client.workflow_t2s(
                text_input=text,
                voice_name=voice_name,
                output_dirpath=self.tts_client.tts_data_folder,
                output_filename=output_filename
            )

        if not send_channel_message_wrapper:
            raise Exception("send_channel_message_wrapper has not been set in TaskHandler!")
        await send_channel_message_wrapper(text)

        if incl_voice:
            self.tts_client.play_local_mp3(
                dirpath=self.tts_client.tts_data_folder, 
                filename=output_filename
            )

    # --------------------------------------------------------------------
    # Below are small helper methods to handle the openai/deepseek logic
    # so you don't crowd your main methods.
    # --------------------------------------------------------------------
    async def _handle_generate_openai(self, task):
        """
        For handle_generate_text: openai scenario
        """
        log_extra = dict(task.task_dict or {})
        try:
            gpt_response = await self.gpt_response_manager.execute_thread(
                thread_name=task.task_dict.get("thread_name"),
                assistant_name=task.task_dict.get("assistant_name"),
                thread_instructions=task.task_dict.get("prompt"),
                replacements_dict=task.task_dict.get("replacements_dict")
            )
            self.logger.debug("OpenAI GPT response complete", extra=log_extra)
            return gpt_response

        except Exception as e:
            self.logger.error("Error in _handle_generate_openai", extra=log_extra, exc_info=True)
            raise

    async def _handle_generate_deepseek(self, task):
        """
        For handle_generate_text: deepseek scenario
        """
        log_extra = dict(task.task_dict or {})
        try:
            prompt = task.task_dict.get("prompt", "")
            replacements_dict = task.task_dict.get("replacements_dict", {})
            final_prompt = utils.populate_placeholders(
                logger=self.logger,
                prompt_template=prompt + self.config.llm_assistants_suffix,
                replacements=replacements_dict
            )
            model_vendor_config = task.task_dict.get("model_vendor_config", {})
            model_name = model_vendor_config.get("model")
            
            gpt_response = await self.deepseek_client.get_deepseek_response_generate(
                model=model_name,
                prompt=final_prompt
            )
            self.logger.debug("DeepSeek GPT response complete", extra=log_extra)
            return gpt_response

        except Exception as e:
            self.logger.error("Error in _handle_generate_deepseek", extra=log_extra, exc_info=True)
            raise

    async def _handle_execute_openai(self, task):
        """
        For handle_execute_thread: openai scenario
        """
        log_extra = dict(task.task_dict or {})
        try:
            gpt_response = await self.gpt_response_manager.execute_thread(
                thread_name=task.task_dict.get("thread_name"),
                assistant_name=task.task_dict.get("assistant_name"),
                thread_instructions=task.task_dict.get("thread_instructions"),
                replacements_dict=task.task_dict.get("replacements_dict")
            )
            self.logger.debug("OpenAI GPT response complete (execute_thread)", extra=log_extra)
            return gpt_response

        except Exception as e:
            self.logger.error("Error in _handle_execute_openai", extra=log_extra, exc_info=True)
            raise

    async def _handle_execute_deepseek(self, task):
        """
        For handle_execute_thread: deepseek scenario
        """
        log_extra = dict(task.task_dict or {})
        try:
            thread_instructions = task.task_dict.get("thread_instructions", "")
            replacements_dict = task.task_dict.get("replacements_dict", {})
            final_instructions = utils.populate_placeholders(
                logger=self.logger,
                prompt_template=thread_instructions + self.config.llm_assistants_suffix,
                replacements=replacements_dict
            )
            model_vendor_config = task.task_dict.get("model_vendor_config", {})
            model_name = model_vendor_config.get("model")

            gpt_response = await self.deepseek_client.get_deepseek_response_chat(
                model=model_name,
                prompt=final_instructions,
                messages=self.message_handler.all_msg_history_gptdict
            )
            self.logger.debug("DeepSeek GPT response complete (execute_thread)", extra=log_extra)
            return gpt_response

        except Exception as e:
            self.logger.error("Error in _handle_execute_deepseek", extra=log_extra, exc_info=True)
            raise

    async def _handle_send_channel_message_and_voice(self, text, tts_voice, log_extra):
        """
        Small helper that calls send_output_message_and_voice with the known wrapper.
        """
        if not self._send_channel_message_wrapper:
            raise Exception("send_channel_message_wrapper has not been set!")
        # Reuse your existing method but supply the arguments
        await self.send_output_message_and_voice(
            text=text,
            incl_voice=self.config.tts_include_voice,
            voice_name=tts_voice,
            send_channel_message_wrapper=self._send_channel_message_wrapper
        )
        self.logger.debug("Sent channel message and/or voice", extra=log_extra)
