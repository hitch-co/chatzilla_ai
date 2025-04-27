
import logging
import asyncio

from my_modules import utils
from my_modules.my_logging import create_logger

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
        self.handle_tasks_logger = logging.getLogger("my_app.task_handler")
        self.runtime_logger = logging.getLogger('my_app.runtime')
        
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
        """
        Set the callable that sends a channel message. This is a wrapper around the
        actual method that sends the message, allowing the TaskHandler to control
        the flow of messages and optionally include TTS.
        """
        self._send_channel_message_wrapper = wrapper_callable

    async def _add_thread_instructions_final(self, task: object) -> dict:
        try:
            task.task_dict["thread_instructions_final"] = utils.populate_placeholders(
                logger=None,
                prompt_template=task.task_dict.get("thread_instructions", "") + self.config.llm_assistants_suffix,
                replacements=task.task_dict.get("replacements_dict", {})
            )
            return task
        except Exception as e:
            self.runtime_logger.error(f"Exception in '_add_thread_instructions_final': {e}", exc_info=True)
            task.future.set_exception(e)
            return
    
    async def handle_tasks(self, task: object):
        """
        Entry point for handling all tasks. Acquires a lock on the thread and dispatches
        to the appropriate handler based on task_type.
        """
        try:
            # Log the entire task dict as extra info
            log_extra = dict(task.task_dict or {})
            self.handle_tasks_logger.info("handle_tasks: Received task", extra=log_extra)

            # Grab the thread_name from the task dict (already in log_extra, but also needed locally)
            thread_name = task.task_dict.get("thread_name")
            lock = self.task_manager.thread_locks[thread_name]

            async with lock:
                self.runtime_logger.debug("Lock acquired, dispatching handler", extra=log_extra)
                try:
                    task_type = task.task_dict.get("type")
                    handler = self.dispatch_table.get(task_type)
                    if not handler:
                        error_msg = f"Unsupported task type: {task_type}"
                        # Log again with the same extra fields
                        self.runtime_logger.error(error_msg, extra=log_extra)
                        task.future.set_exception(Exception(error_msg))
                        return

                    # Call the handler
                    await handler(task)

                except Exception as exc:
                    self.runtime_logger.exception("Exception in handle_tasks", extra=log_extra)
                    task.future.set_exception(exc)

        except Exception as e:
            self.runtime_logger.error(f"Exception in 'handle_tasks': {e}", exc_info=True)
            task.future.set_exception(e)
            return

    async def _wait_for_no_active_run(self, thread_name: str, poll_interval: float = 1.0, timeout: float = 10.0):
        """
        Polls OpenAI to check if the thread still has active runs.
        """
        import time

        start_time = time.time()
        thread_id = self.gpt_response_manager.gpt_thread_manager.get_thread_id_by_name(thread_name)

        while True:
            # List all runs for this thread
            runs = self.gpt_response_manager.gpt_client.beta.threads.runs.list(thread_id=thread_id)

            # Check if any run is still queued or in_progress
            active_runs = [r for r in runs.data if r.status in ['queued', 'in_progress']]
            
            if not active_runs:
                # No active runs — thread is free
                return
            
            elif time.time() - start_time > timeout:
                raise Exception(f"Timeout: OpenAI thread '{thread_name}' still has active runs after {timeout} seconds.")

            await asyncio.sleep(poll_interval)
            
    async def handle_add_message(self, task: object):
        """
        Add a message to the thread's message queue.
        """
        log_extra = dict(task.task_dict or {})
        try:
            thread_name = task.task_dict.get("thread_name")
            message_role = task.task_dict.get("message_role")
            message_content = task.task_dict.get("message_content")
            message_name = task.task_dict.get('message_name')
            message_timestamp = task.task_dict.get('message_timestamp')
            model_vendor_config = task.task_dict.get("model_vendor_config", {})
            model_vendor_name = model_vendor_config.get("vendor", None)

            # Check if thread has an active run
            if model_vendor_name == "openai":
                self.runtime_logger.info(f"Checking if OpenAI thread '{thread_name}' has an active run...", extra=log_extra)
                await self._wait_for_no_active_run(thread_name)

        except Exception as e:
            self.runtime_logger.warning("Failed to initialize task_dict attribute", exc_info=True)
            task.future.set_exception(e)

        try:
            await self.gpt_response_manager.add_message_to_openai_thread(
                message_content=f"{message_name}: {message_content}",
                thread_name=thread_name,
                role=message_role
            )
        except Exception as e:
            self.runtime_logger.warning(f"gpt_response_manager.add_message_to_openai_thread() failed.  Make sure GPT threads are created")
            task.future.set_exception(e)

        try:
            await self.message_handler.add_to_appropriate_message_history(
                role=message_role,
                name=message_name,
                content=message_content,
                timestamp=message_timestamp
            )
        except Exception as e:
            self.runtime_logger.warning(f"message_handler.add_to_appropriate_message_history() failed.  This should not happen.")
            task.future.set_exception(e)

        message = f"TaskHandler.handle_add_message: Task complete for thread='{thread_name}'"
        self.handle_tasks_logger.info(message, extra=log_extra)
        task.future.set_result(message)

    async def handle_generate_text(self, task: object):
        gpt_response = None
        task = await self._add_thread_instructions_final(task)
        thread_name = task.task_dict.get("thread_name")
        model_vendor_name = task.task_dict.get("model_vendor_config", {}).get("vendor")
        log_extra = dict(task.task_dict or {})

        try:
            if model_vendor_name == "openai":
                gpt_response = await self._handle_generate_openai(task)
            elif model_vendor_name == "deepseek":
                gpt_response = await self._handle_generate_deepseek(task)
            else:
                error_msg = f"Unsupported model vendor: {model_vendor_name}"
                self.handle_tasks_logger.error(error_msg, extra=log_extra)
                task.future.set_exception(Exception(error_msg))
                return

            if gpt_response is not None and task.task_dict.get("send_channel_message"):
                gpt_response = GPTResponseCleaner.perform_all_gpt_response_cleanups(gpt_response)

                await self._handle_send_channel_message_and_voice(
                    gpt_response,
                    tts_voice=task.task_dict.get("tts_voice"),
                    log_extra=log_extra
                )
                message = f"handle_generate_text: Completed for thread='{thread_name}' (channel msg sent)."

            elif gpt_response is None:
                error_msg = f"GPT response is None in generate_text (thread='{thread_name}')"
                self.runtime_logger.error(error_msg, extra=log_extra)
                task.future.set_exception(Exception(error_msg))
                return
            else:
                message = f"handle_generate_text: Completed for thread='{thread_name}' (no channel msg)."

            self.handle_tasks_logger.info(message, extra=log_extra)
            self.runtime_logger.debug("GPT response complete", extra=log_extra)
            task.future.set_result(message)

        except Exception as e:
            self.runtime_logger.error("Error in handle_generate_text", extra=log_extra, exc_info=True)
            task.future.set_exception(e)

    async def handle_execute_thread(self, task: object):        
        gpt_response = None
        task = await self._add_thread_instructions_final(task)
        thread_name = task.task_dict.get("thread_name")
        model_vendor_name = task.task_dict.get("model_vendor_config", {}).get("vendor")
        log_extra = dict(task.task_dict or {})
        try:
            if model_vendor_name == "openai":
                gpt_response = await self._handle_execute_openai(task)
            elif model_vendor_name == "deepseek":
                gpt_response = await self._handle_execute_deepseek(task)
            else:
                error_msg = f"Unsupported model vendor: {model_vendor_name}"
                self.runtime_logger.error(error_msg, extra=log_extra)
                task.future.set_exception(Exception(error_msg))
                return
            
            self.runtime_logger.debug(f"{model_vendor_name} GPT response complete (execute_thread)", extra=log_extra)

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
                self.runtime_logger.error(error_msg, extra=log_extra)
                task.future.set_exception(Exception(error_msg))
                return
            else:
                message = f"handle_execute_thread: Completed for thread='{thread_name}' (no channel msg)."

            self.handle_tasks_logger.info(message, extra=log_extra)
            task.future.set_result(message)

        except Exception as e:
            self.runtime_logger.error("Error in handle_execute_thread", extra=log_extra, exc_info=True)
            task.future.set_exception(e)

    async def handle_send_channel_message(self, task: object):
        log_extra = dict(task.task_dict or {})
        thread_name = task.task_dict.get("thread_name")

        try:
            # Add message to specified thread
            content = task.task_dict.get("content")
            message_role = task.task_dict.get("message_role")


            await self.gpt_response_manager.add_message_to_openai_thread(
                message_content=content,
                thread_name=thread_name,
                role=message_role
            )

            # Now send output (with optional TTS)
            await self._handle_send_channel_message_and_voice(
                content,
                tts_voice=task.task_dict.get("tts_voice"),
                log_extra=log_extra
            )
            message = f"handle_send_channel_message: Completed for thread='{thread_name}'"
            self.handle_tasks_logger.info(message, extra=log_extra)
            task.future.set_result(message)

        except Exception as e:
            self.runtime_logger.error("Error in handle_send_channel_message", extra=log_extra, exc_info=True)
            task.future.set_exception(e)

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
                thread_instructions=task.task_dict.get("thread_instructions_final"),
                replacements_dict=task.task_dict.get("replacements_dict")
            )
            return gpt_response

        except Exception as e:
            self.runtime_logger.error("Error in _handle_generate_openai", extra=log_extra, exc_info=True)
            raise

    async def _handle_generate_deepseek(self, task):
        """
        For handle_generate_text: deepseek scenario
        """
        log_extra = dict(task.task_dict or {})
        try:
            model_vendor_config = task.task_dict.get("model_vendor_config", {})
            model_name = model_vendor_config.get("model")
            
            gpt_response = await self.deepseek_client.get_deepseek_response_generate(
                model=model_name,
                prompt=task.task_dict.get("thread_instructions_final")
            )
            return gpt_response

        except Exception as e:
            self.runtime_logger.error("Error in _handle_generate_deepseek", extra=log_extra, exc_info=True)
            raise

    async def _handle_execute_openai(self, task):
        """
        For handle_execute_thread: openai scenario
        """
        thread_name=task.task_dict.get("thread_name")
        assistant_name=task.task_dict.get("assistant_name")
        thread_instructions=task.task_dict.get("thread_instructions_final")
        replacements_dict=task.task_dict.get("replacements_dict")

        try:
            gpt_response = await self.gpt_response_manager.execute_thread(
                thread_name=thread_name,
                assistant_name=assistant_name,
                thread_instructions=thread_instructions,
                replacements_dict=replacements_dict
            )
            return gpt_response

        except Exception as e:
            self.runtime_logger.error("Error in _handle_execute_openai", exc_info=True)
            raise

    async def _handle_execute_deepseek(self, task):
        """
        For handle_execute_thread: deepseek scenario
        """
        try:
            gpt_response = await self.deepseek_client.get_deepseek_response_chat(
                model=task.task_dict.get("model_vendor_config", {}).get("model"),
                prompt=task.task_dict.get("thread_instructions_final"),
                messages=self.message_handler.all_msg_history_gptdict
            )
            return gpt_response

        except Exception as e:
            self.runtime_logger.error("Error in _handle_execute_deepseek", exc_info=True)
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
        self.runtime_logger.debug("Sent channel message and/or voice", extra=log_extra)
