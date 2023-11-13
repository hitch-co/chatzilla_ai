import openai
import os 
import asyncio

from my_modules import config
from my_modules.my_logging import create_logger
from my_modules.config import run_config

root_logger = create_logger(
    dirname='log', 
    debug_level='INFO',
    logger_name='root_GPTAssistantManager2',
    stream_logs=True
    )

def get_thread_ids(assistant_name, client_manager):
    assistant_id = client_manager.assistants.get(assistant_name, {}).get('id')
    if assistant_id is None:
        raise ValueError(f"No ID found for assistant '{assistant_name}'")
        
def get_thread_and_assistant_ids(thread_name, thread_manager, client_manager):
    # This function takes a thread_name and the manager instances
    # Returns the thread_id and assistant_id

    assistant_name = thread_manager._get_thread_assistant(thread_name)
    if assistant_name is None:
        raise ValueError(f"No assistant found for thread '{thread_name}'")

    assistant_id = client_manager.assistants.get(assistant_name, {}).get('id')
    if assistant_id is None:
        raise ValueError(f"No ID found for assistant '{assistant_name}'")

    thread_id = thread_manager.beta.threads.get(thread_name, {}).get('id')
    if thread_id is None:
        raise ValueError(f"No ID found for thread '{thread_name}'")

    root_logger.info("thread_id and assistant_id:")
    root_logger.info(f"assistant_id:{assistant_id}, thread_id:{thread_id}")
    return thread_id, assistant_id

def get_thread_id(thread_name, gpt_client):
    thread_id = gpt_client.beta.threads.get(thread_name, {}).get('id')
    if thread_id is None:
        raise ValueError(f"No ID found for thread '{thread_name}'")
    return thread_id

class GPTClientAssistantManager:
    def __init__(self, config_data, gpt_client):
        self.logger = create_logger(
            dirname='log', 
            debug_level='INFO',
            logger_name='root_GPTClientAssistantManager',
            stream_logs=True
            )
        self.config_data = config_data
        self.gpt_client = gpt_client
        self.assistants = {}

    def create_assistant(
            self, 
            assistant_name='default', 
            assistant_instructions="you're a question answering machine", 
            assistant_type=None, 
            assistant_model=None
            ):
        assistant_type = assistant_type or self.config_data['openai-api']['assistant_type']
        assistant_model = assistant_model or self.config_data['openai-api']['assistant_model']

        assistant = self.gpt_client.beta.assistants.create(
            name=assistant_name,
            instructions=assistant_instructions,
            tools=[{"type": assistant_type}],
            model=assistant_model
        )
        self.assistants[assistant_name] = {'object':assistant, 'id':assistant.id}

        self.logger.debug(f"This is the assistant:")
        self.logger.debug(assistant)
        return assistant
    

class GPTThreadManager:
    def __init__(self, gpt_client):
        self.logger = create_logger(
            dirname='log', 
            debug_level='INFO',
            logger_name='root_GPTThreadManager',
            stream_logs=True
            )
        self.gpt_client = gpt_client
        self.threads = {}
        self.thread_to_assistant = {}

    def create_thread(self, thread_name):     
        thread = self.gpt_client.beta.threads.create()
        
        #store and link the thread
        self.threads[thread_name] = {'object':thread, 'id':thread.id}

        self.logger.debug(f"This is the thread id/object:")
        self.logger.debug(thread.id)
        self.logger.debug(thread)
        return thread

    def _get_thread_assistant(self, thread_name):
        # Returns the assistant associated with the given thread
        return self.thread_to_assistant.get(thread_name, None)
    
    def add_message_to_thread(self, thread_id:str, role:str='user', message_content:str="Let the user know they should set the message_content variable"):
    
        message_object = self.gpt_client.beta.threads.messages.create(
            thread_id=thread_id,
            role=role,
            content=message_content
            )
        self.logger.debug(f"message_object (type: {type(message_object)})")
        self.logger.debug(message_object)
        return message_object


class GPTAssistantResponseManager:
    def __init__(self, gpt_client):
        self.logger = create_logger(
            dirname='log', 
            debug_level='INFO',
            logger_name='root_GPTAssistantResponseManager',
            stream_logs=True
            )
        self.gpt_client = gpt_client

    async def _get_response(self, thread_id, run_id, polling_seconds=1):
        while True:
            response = self.gpt_client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )
            if response.status == 'completed':
                return response
            await asyncio.sleep(polling_seconds)

    async def _get_assistant_response_thread_messages(
            self, 
            thread_id, 
            assistant_id, 
            thread_instructions='Answer the question using clear and concise language'
            ):
        run = self.gpt_client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
            instructions=thread_instructions
        )
        await self._get_response(thread_id, run.id)
        messages = self.gpt_client.beta.threads.messages.list(thread_id=thread_id)
        self.logger.debug("This is the 'messages' object:")
        self.logger.debug(messages)
        return messages
    
    def _extract_latest_response_from_thread_messages(self, response_thread_messages):
        # Sort the messages by 'created_at' in descending order
        sorted_response_thread_messages = sorted(response_thread_messages.data, key=lambda msg: msg.created_at, reverse=True)

        # Find the most recent message with role 'assistant'
        for message in sorted_response_thread_messages:
            if message.role == 'assistant':
                for content in message.content:
                    if content.type == 'text':
                        return content.text.value
        return None

    async def workflow(self, assistant_id, thread_id, thread_instructions):
        # Get the response messages from the assistant
        response_thread_messages = await self._get_assistant_response_thread_messages(
            assistant_id=assistant_id,
            thread_id=thread_id,
            thread_instructions=thread_instructions
        )

        # Extract the latest response from the messages
        extracted_message = self._extract_latest_response_from_thread_messages(response_thread_messages)
        
        self.logger.info(f"This is the response from the assistant: '{extracted_message}'")
        return extracted_message
        
# def main():
#     # Configuration and API key setup
#     yaml_data = run_config()
#     openai.api_key = os.getenv('OPENAI_API_KEY')

#     # Create client and manager instances
#     gpt_client = openai.OpenAI()
#     gpt_clast_mgr = GPTClientAssistantManager(config_data=yaml_data, gpt_client=gpt_client)
#     gpt_thrd_mgr = GPTThreadManager(gpt_client=gpt_client)
#     gpt_resp_mgr = GPTAssistantResponseManager(gpt_client=gpt_client)

#     # Create assistant
#     startstory_assistant = gpt_clast_mgr.create_assistant(
#         assistant_name='startstory',
#         assistant_instructions='you"re a bot with an attitude'
#     )
#     startstory_assistant_id = startstory_assistant.id

#     # Create thread
#     startstory_thread = gpt_thrd_mgr.create_thread(thread_name='startstory')
#     startstory_thread_id = gpt_thrd_mgr.threads['startstory']['id']

#     # Add message to thread
#     gpt_thrd_mgr.add_message_to_thread(
#         thread_id=startstory_thread_id, 
#         role='user', 
#         message_content="once upon a time..."
#     )

#     # Run workflow and retrieve response
#     something = asyncio.run(gpt_resp_mgr.workflow(
#         assistant_id=startstory_assistant_id,
#         thread_id=startstory_thread_id,
#         thread_instructions="finish the sentence in <20 words"
#     ))

#     # Example logging (if you have a logger setup)
#     # root_logger.info(f"Workflow output: {something}")

if __name__ == "__main__":
    # Configuration and API key setup
    yaml_data = run_config()
    openai.api_key = os.getenv('OPENAI_API_KEY')

    # Create client and manager instances
    gpt_client = openai.OpenAI()
    gpt_clast_mgr = GPTClientAssistantManager(config_data=yaml_data, gpt_client=gpt_client)
    gpt_thrd_mgr = GPTThreadManager(gpt_client=gpt_client)
    gpt_resp_mgr = GPTAssistantResponseManager(gpt_client=gpt_client)

    # Create assistant
    startstory_assistant = gpt_clast_mgr.create_assistant(
        assistant_name='startstory',
        assistant_instructions='you"re a bot with an attitude'
    )
    startstory_assistant_id = startstory_assistant.id

    # Create thread
    startstory_thread = gpt_thrd_mgr.create_thread(thread_name='startstory')
    startstory_thread_id = gpt_thrd_mgr.threads['startstory']['id']

    # Add message to thread
    gpt_thrd_mgr.add_message_to_thread(
        thread_id=startstory_thread_id, 
        role='user', 
        message_content="once upon a time..."
    )

    # Run workflow and retrieve response
    gpt_response_text = asyncio.run(gpt_resp_mgr.workflow(
        assistant_id=startstory_assistant_id,
        thread_id=startstory_thread_id,
        thread_instructions="finish the sentence in <20 words"
    ))