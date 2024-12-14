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

    async def add_task_to_queue(self, thread_name, task):
        """Adds a task to the queue with logging."""
        self.logger.debug(f"Task to add to queue: {task.task_dict}")
        async with self.task_queue_lock:
            await self.task_queues[thread_name].put(task)
            self.logger.debug(f"Queue size for thread '{thread_name}': {self.task_queues[thread_name].qsize()}")

    async def add_task_to_queue_and_execute(self, thread_name, task, description=""):
        """Adds a task to the queue and waits for its completion."""
        await self.add_task_to_queue(thread_name, task)
        await self._wait_for_task_completion(task, description)