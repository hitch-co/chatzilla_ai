class TaskManager:
    def __init__(self, gpt_thread_mgr, logger):
        self.gpt_thread_mgr = gpt_thread_mgr
        self.logger = logger

    async def _wait_for_task_completion(self, task, description=""):
        """Waits for a task's completion with logging."""
        if description:
            self.logger.info(f"...waiting for {description} task to complete...")
        await task.future
        if description:
            self.logger.info(f"...{description} task completed.")

    async def _add_task_to_queue(self, thread_name, task):
        """Adds a task to the queue with logging."""
        self.logger.debug(f"Task to add to queue: {task.task_dict}")
        await self.gpt_thread_mgr.add_task_to_queue(thread_name, task)

    async def add_task_to_queue_and_execute(self, thread_name, task, description=""):
        """Adds a task to the queue and waits for its completion."""
        await self._add_task_to_queue(thread_name, task)
        await self._wait_for_task_completion(task, description)

    # async def execute_add_message_task(self, thread_name, content, message_role="user"):
    #     """Creates, queues, and waits for an AddMessageTask to complete."""
    #     task = AddMessageTask(thread_name, content, message_role)
    #     await self.add_task_to_queue_and_execute(thread_name, task, description="AddMessageTask")

    # async def execute_thread_task(self, thread_name, assistant_name, instructions, replacements, voice, description="ExecuteThreadTask"):
    #     """Creates, queues, and waits for an ExecuteThreadTask to complete."""
    #     task = CreateExecuteThreadTask(
    #         thread_name=thread_name,
    #         assistant_name=assistant_name,
    #         thread_instructions=instructions,
    #         replacements_dict=replacements,
    #         tts_voice=voice
    #     )
    #     await self.add_task_to_queue_and_execute(thread_name, task, description)
