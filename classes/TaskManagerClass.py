from typing import Dict, List, Callable
import asyncio
from collections import defaultdict 

from my_modules import my_logging

runtime_logger_level = 'INFO'
class TaskManager:
    def __init__(self):

        # Create a logger
        self.logger = my_logging.create_logger(
            dirname='log', 
            logger_name='TaskManagerClass',
            debug_level=runtime_logger_level,
            mode='w',
            stream_logs=True
            )

        # Task queues
        self.task_queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue) # Thread name to task queue mapping
        self.task_queue_lock = asyncio.Lock()
        self.on_task_ready: Callable[[Dict], None] = None

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

    async def task_scheduler(self, sleep_time=3):
        """
        Continuously checks task queues and processes tasks in a FIFO order.
        Marks tasks as done after processing to keep the queue state consistent.
        """
        while True:
            self.logger.info("Checking task queues...")

            async with self.task_queue_lock:
                task_queues_snapshot = list(self.task_queues.items())

            task_processed = False

            self.logger.info("Task Queue Status:")
            for thread_name, queue in task_queues_snapshot:
                self.logger.info(f"Thread: {thread_name}, Queue Size: {queue.qsize()}, Pending Tasks: {queue._unfinished_tasks}")

            for thread_name, queue in task_queues_snapshot:
                if not queue.empty():
                    try:
                        task = await queue.get()
                        self.logger.info(f"...task found in queue '{thread_name}' (type: {task.task_dict.get('type')})...")
                        
                        await self._process_task(task)
                        task_processed = True
                    
                    except Exception as e:
                        self.logger.error(f"Error processing task (type: {task.task_dict.get('type')}): {e}", exc_info=True)
                    
                    finally:
                        queue.task_done()

            if not task_processed:
                self.logger.info("No tasks found in queues. Waiting for new tasks...")
                await asyncio.sleep(sleep_time)

    async def _process_task(self, task: object):
        """
        Process the task before executing. This method includes logging, validation,
        and any other pre-processing steps needed before the task is handled.
        """
        self.logger.info(f"...processing task type '{task.task_dict.get('type')}' with thread_name: '{task.task_dict.get('thread_name')}'")
        self.logger.debug(f"Task details: {task.task_dict}")

        # Basic validation to ensure necessary fields are present
        if not task.task_dict.get('type') or not task.task_dict.get('thread_name'):
            self.logger.error("...Task missing required fields. Task will be skipped.")
            self.logger.error(f"...Invalid task: {task.task_dict}")
            raise ValueError("Task missing required fields. Task will be skipped.")

        # Check if the on_task_ready callback is set (probably handle_tasks()) and invoke it to handle the task execution
        if self.on_task_ready:
            self.logger.debug(f"...Invoking task handler for task associated with thread name, execution: {task.task_dict.get('thread_name')}, {task.task_dict.get('type')}")
            await self.on_task_ready(task)
        else:
            self.logger.error("...No task handler has been set. Unable to execute task.")
            raise ValueError("No task handler has been set. Unable to execute task.")

if __name__ == '__main__':
    task_manager = TaskManager()
    print("loaded TaskManager.py")

