import asyncio
from my_modules.my_logging import create_logger

runtime_logger_level = 'INFO'
logger = create_logger(
    dirname='log', 
    logger_name='modules-adjustable_sleep_task', 
    debug_level=runtime_logger_level,
    mode='w',
    stream_logs=True,
    encoding='UTF-8'
    )

async def adjustable_sleep_task(config, attribute_name):
    total_sleep_time = getattr(config, attribute_name)
    sleep_interval = 1  # Check every second

    elapsed_time = 0
    while elapsed_time < total_sleep_time:
        logger.debug(f"Elapsed time: {elapsed_time} (of {total_sleep_time})")
        await asyncio.sleep(sleep_interval)
        elapsed_time += sleep_interval

        # Check if the sleep time needs to be adjusted
        new_sleep_time = getattr(config, attribute_name)
        logger.debug(f"new_sleep_time: {new_sleep_time}")
        if new_sleep_time != total_sleep_time:
            logger.info(f"Sleep time was adjusted: {total_sleep_time} -> {new_sleep_time}")
            total_sleep_time = new_sleep_time
    logger.debug("Completed adjustable sleep.")

# # Ceate an example usage of the adjustable_sleep_task function
# import asyncio
# from utils import adjustable_sleep_task  # Import the utility function

# class Config:
#     def __init__(self):
#         self.randomfact_sleep_time = 10

# class Bot:
#     def __init__(self):
#         self.config = Config()

#     async def example_task(self):
#         print("Performing the example task...")

#     async def run(self):
#         await adjustable_sleep_task(self.example_task, self.config, 'randomfact_sleep_time')

# # Create and run the bot
# bot = Bot()
# asyncio.run(bot.run())