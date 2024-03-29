import openai
import os 
import asyncio

from my_modules.my_logging import create_logger

from classes.ConfigManagerClass import ConfigManager

debug_level = 'INFO'

root_logger = create_logger(
    dirname='log', 
    debug_level=debug_level,
    logger_name='logger_root_GPTAssistantManager',
    stream_logs=True
    ) 

# def get_thread_ids(assistant_name, client_manager):
#     assistant_id = client_manager.assistants.get(assistant_name, {}).get('id')
#     if assistant_id is None:
#         raise ValueError(f"No ID found for assistant '{assistant_name}'")
        
# def get_thread_and_assistant_ids(thread_name, thread_manager, client_manager):
#     # This function takes a thread_name and the manager instances
#     # Returns the thread_id and assistant_id

#     assistant_name = thread_manager._get_thread_assistant(thread_name)
#     if assistant_name is None:
#         raise ValueError(f"No assistant found for thread '{thread_name}'")

#     assistant_id = client_manager.assistants.get(assistant_name, {}).get('id')
#     if assistant_id is None:
#         raise ValueError(f"No ID found for assistant '{assistant_name}'")

#     thread_id = thread_manager.beta.threads.get(thread_name, {}).get('id')
#     if thread_id is None:
#         raise ValueError(f"No ID found for thread '{thread_name}'")

#     root_logger.info("thread_id and assistant_id:")
#     root_logger.info(f"assistant_id:{assistant_id}, thread_id:{thread_id}")
#     return thread_id, assistant_id

# def get_thread_id(thread_name, gpt_client):
#     thread_id = gpt_client.beta.threads.get(thread_name, {}).get('id')
#     if thread_id is None:
#         raise ValueError(f"No ID found for thread '{thread_name}'")
#     return thread_id

def prompt_text_replacement(logger, gpt_prompt_text, replacements_dict=None):
    if replacements_dict:
        prompt_text_replaced = gpt_prompt_text.format(**replacements_dict)   
    else:
        prompt_text_replaced = gpt_prompt_text

    logger.debug(f"prompt_text_replaced: {prompt_text_replaced}")
    return prompt_text_replaced

class GPTBaseClass:
    """
    Initializes the GPT Base Class.

    Args:
        gpt_client: An instance of the OpenAI client.

    Attributes:
        logger (Logger): A logger for this class.
        gpt_client: The OpenAI client instance.
    """
    def __init__(self, gpt_client):
        self.logger = create_logger(
            dirname='log', 
            debug_level=debug_level,
            logger_name='GPTBaseClass',
            stream_logs=True
            )
        self.gpt_client = gpt_client
        self.yaml_data = ConfigManager.get_instance()

        def create():
            print("did a create")
        def delete():
            print("did a delete")

class GPTAssistantManager(GPTBaseClass):
    """
    Initializes the GPT Assistant Manager.

    Args:
        yaml_data: Configuration data loaded from a YAML file.
        gpt_client: An instance of the OpenAI client.

    Attributes:
        logger (Logger): A logger for this class.
        yaml_data (dict): Configuration data extracted from yaml_data.
        gpt_client: The OpenAI client instance.
        assistants (dict): A dictionary to store assistant objects and their IDs.
    """
    def __init__(self, gpt_client):
        super().__init__(gpt_client)
        self.logger = create_logger(
            dirname='log', 
            debug_level=debug_level,
            logger_name='GPTAssistantManager',
            stream_logs=True
            )
        self.assistants = {}

    def _create_assistant(
            self, 
            assistant_name='default', 
            assistant_instructions="you're a question answering machine", 
            replacements_dict: dict=None,
            assistant_type=None, 
            assistant_model=None
            ):
        """
        Creates an assistant with the specified parameters.

        Args:
            assistant_name (str): The name of the assistant to create. Default is 'default'.
            assistant_instructions (str): Instructions for the assistant. Default is a generic instruction.
            assistant_type: The type of the assistant. Defaults to the type specified in the configuration.
            assistant_model: The model of the assistant. Defaults to the model specified in the configuration.

        Returns:
            The created assistant object.
        """
        assistant_type = assistant_type or self.yaml_data.gpt_assistant_type
        assistant_model = assistant_model or self.yaml_data.gpt_model
        assistant_instructions = prompt_text_replacement(
            logger=self.logger, 
            gpt_prompt_text=assistant_instructions,
            replacements_dict=replacements_dict
            )
        
        assistant = self.gpt_client.beta.assistants.create(
            name=assistant_name,
            instructions=assistant_instructions,
            tools=[{"type": assistant_type}],
            model=assistant_model
        )
        self.assistants[assistant_name] = {'object':assistant, 'id':assistant.id}

        self.logger.debug(f"This is the assistant object for '{assistant_name}' with instructions: {assistant_instructions}")
        self.logger.debug(assistant)
        return assistant

    def create_assistants(self, assistants_config) -> dict:
        # Create Assistants
        replacements_dict = {
            "wordcount_short":self.yaml_data.wordcount_short,
            "wordcount_medium":self.yaml_data.wordcount_medium,
            "wordcount_long":self.yaml_data.wordcount_long,
            "vibecheckee_username": 'chad',
            "vibecheck_message_wordcount": self.yaml_data.vibechecker_message_wordcount,
        }

        self.logger.debug('Creating GPT Assistants')
        for assistant_name, prompt in assistants_config.items():
            self._create_assistant(
                assistant_name=assistant_name,
                assistant_instructions=prompt,
                replacements_dict=replacements_dict,
                assistant_type='code_interpreter',
                assistant_model=self.yaml_data.gpt_model
            )        
        return self.assistants

class GPTThreadManager(GPTBaseClass):
    """
    Initializes the GPT Thread Manager.

    Args:
        gpt_client: An instance of the OpenAI client.

    Attributes:
        logger (Logger): A logger for this class.
        gpt_client: The OpenAI client instance.
        threads (dict): A dictionary to store thread objects and their IDs.
        thread_to_assistant (dict): A mapping of threads to their corresponding assistants.
    """
    def __init__(self, gpt_client):
        super().__init__(gpt_client=gpt_client)
        self.logger = create_logger(
            dirname='log', 
            debug_level=debug_level,
            logger_name='logger_GPTThreadManager',
            stream_logs=True
        )
        self.threads = {}

    def _create_thread(self, thread_name):
        """
        Creates a new thread with the given name and optionally associates it with an assistant.

        Args:
            thread_name (str): The name of the thread to be created.
            assistant_name (str, optional): The name of the assistant to be associated with this thread.

        Returns:
            The created thread object.
        """
        thread = self.gpt_client.beta.threads.create()
        self.threads[thread_name] = {'object': thread, 'id': thread.id}

        self.logger.debug(f"Created thread '{thread_name}' with ID: {thread.id}")

        return thread

    def create_threads(self, threads_config):
        self.logger.debug('Creating GPT Threads')
        for thread_name in threads_config:
            self._create_thread(thread_name)
        return self.threads

    def create_new_thread(self, thread_name):
        """
        Adds a new thread to the thread manager.

        Args:
            thread_name (str): The name of the thread to be added.

        Returns:
            The created thread object.
        """
        return self._create_thread(thread_name)
    
    def ____get_thread_assistant(self, thread_name):
        """
        Retrieves the assistant name associated with a given thread.

        Args:
            thread_name (str): The name of the thread whose assistant needs to be retrieved.

        Returns:
            The name of the assistant associated with the specified thread, or None if no association exists.
        """
        return self.thread_to_assistant.get(thread_name)

    def ____associate_thread_with_assistant(self, thread_name, assistant_name):
        """
        Associates a thread with an assistant.

        Args:
            thread_name (str): The name of the thread.
            assistant_name (str): The name of the assistant to be associated with the thread.
        """
        if thread_name in self.threads:
            self.thread_to_assistant[thread_name] = assistant_name
            self.logger.debug(f"Thread '{thread_name}' associated with assistant '{assistant_name}'")
        else:
            self.logger.warning(f"Attempted to associate non-existent thread '{thread_name}' with assistant '{assistant_name}'")

    async def add_message_to_thread(self, message_content, thread_name, role='user'):
        """
        Adds a message to a specified thread by its name.

        Args:
            message_content (str): The content of the message to be added.
            thread_name (str): The name of the thread to which the message is to be added.
            role (str): The role of the sender ('user' or 'assistant'). Defaults to 'user'.

        Returns:
            The created message object or None if the thread does not exist.
        """
        if thread_name in self.threads:
            thread_id = self.threads[thread_name]['id']
            message_object = self.gpt_client.beta.threads.messages.create(
                thread_id=thread_id, 
                role='user', 
                content=message_content
            )
            self.logger.debug(f"Added message to thread '{thread_name}' (ID: {thread_id})")
            return message_object
        else:
            self.logger.warning(f"Thread '{thread_name}' not found.")
            return None
  
class GPTResponseManager(GPTBaseClass):
    """
    Initializes the GPT Assistant Response Manager.

    Args:
        gpt_client: An instance of the OpenAI client.

    Attributes:
        logger (Logger): A logger for this class.
        gpt_client: The OpenAI client instance.
        yaml_data: Configuration data loaded from a YAML file.
    """
    def __init__(self, gpt_client):
        super().__init__(gpt_client=gpt_client)
        self.logger = create_logger(
            dirname='log', 
            debug_level=debug_level,
            logger_name='logger_GPTAssistantResponseManager',
            stream_logs=True
            )

    async def _get_response(self, thread_id, run_id, polling_seconds=1):
        """
        Asynchronously retrieves the response for a given thread and run ID.

        Args:
            thread_id (str): The ID of the thread.
            run_id (str): The ID of the run.
            polling_seconds (int): The interval in seconds between polling attempts. Default is 4 seconds.

        Returns:
            The response object once the status is 'completed'.
        """
        counter=1
        while counter < 15:
            response = self.gpt_client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )
            if response.status == 'completed':
                self.logger.debug("This is the completed 'response' object:")
                self.logger.debug(response)
                return response
            else:
                self.logger.debug(f"The 'response' object is not completed yet. Polling time: {counter*polling_seconds} seconds...")
                counter+=1
            await asyncio.sleep(polling_seconds)
        raise ValueError(f"Response not completed after {counter*polling_seconds} seconds")

    async def _run_and_get_assistant_response_thread_messages(
            self, 
            thread_id, 
            assistant_id,
            thread_instructions:str='Answer the question using clear and concise language',
            replacements_dict:dict=None
            ):
        """
        Asynchronously runs the assistant on a specified thread and retrieves the thread messages.

        Args:
            thread_id (str): The ID of the thread on which the assistant is run.
            assistant_id (str): The ID of the assistant to be run on the thread.
            thread_instructions (str): Instructions for the assistant. Defaults to a generic instruction.

        Returns:
            A list of response thread messages.
        """
        try:
            thread_instructions = prompt_text_replacement(
                logger=self.logger, 
                gpt_prompt_text=thread_instructions,
                replacements_dict=replacements_dict
                )
            self.logger.debug(f"This is the thread_instructions: {thread_instructions}")
        except Exception as e:
            self.logger.error(f"Error replacing prompt text with replacements_dict")
            self.logger.error(e)
            raise ValueError(f"Error replacing prompt text with replacements_dict")   
        try:
            run = self.gpt_client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=assistant_id,
                instructions=thread_instructions
            )
            self.logger.debug("This is the 'run' object:")
            self.logger.debug(run)

        except Exception as e:
            self.logger.error(f"Error running assistant on thread")
            self.logger.error(e)
            raise ValueError(f"Error running assistant on thread")
        
        await self._get_response(thread_id, run.id)
        response_thread_messages = self.gpt_client.beta.threads.messages.list(thread_id=thread_id)

        self.logger.debug("This is the 'messages' object response_thread_messages:")
        self.logger.debug(response_thread_messages)
        return response_thread_messages
    
    def _extract_latest_response_from_thread_messages(self, response_thread_messages):
        """
        Extracts the latest response from the thread messages.

        Args:
            response_thread_messages (list): A list of messages from a thread.

        Returns:
            The latest response message from the assistant, or None if no response is found.
        """
        try:
            sorted_response_thread_messages = sorted(response_thread_messages.data, key=lambda msg: msg.created_at, reverse=True)
            self.logger.debug("This is the sorted_response_thread_messages:")
            self.logger.debug(sorted_response_thread_messages)

            for message in sorted_response_thread_messages:
                self.logger.debug(f"This is the message.role: {message.role}")
                # self.logger.debug(f"This is the message.content: {message.type}")
                
                if message.role == 'assistant':
                    for content in message.content:
                        if content.type == 'text':
                            self.logger.debug("This is the content.text.value")
                            self.logger.debug(content.text.value)
                            return content.text.value
                else:
                    self.logger.error("No response found in thread messages")
                    raise ValueError("No response found in thread messages")    
            return None
        except Exception as e:
            self.logger.error(f"Error extracting latest response from thread messages")
            self.logger.error(e)
            raise ValueError(f"Error extracting latest response from thread messages")
        
    async def make_gpt_response_from_msghistory(
        self, 
        assistant_id, 
        thread_id, 
        thread_instructions, 
        replacements_dict=None
        ):
        """
        Executes the workflow to get the GPT assistant's response to a thread.

        Args:
            assistant_id (str): The ID of the assistant.
            thread_id (str): The ID of the thread.
            thread_instructions (str): Instructions for the assistant.

        Returns:
            The final response message from the assistant.
        """

        self.logger.debug(f"Starting make_gpt_response_from_msghistory() with thread_instructions: {thread_instructions[0:25]}...")
        try:
            response_thread_messages = await self._run_and_get_assistant_response_thread_messages(
                assistant_id=assistant_id,
                thread_id=thread_id,
                thread_instructions=thread_instructions,
                replacements_dict=replacements_dict
            )        
            self.logger.debug(f"Starting _extract_latest_response_from_thread_messages() with response_thread_messages: {response_thread_messages}...")
            extracted_message = self._extract_latest_response_from_thread_messages(response_thread_messages)
            self.logger.debug(f"Extracted message and length: {len(extracted_message)} chars, {extracted_message}")
        except Exception as e:
            self.logger.error(f"Error running assistant on thread")
            self.logger.error(e)
            raise ValueError(f"Error running assistant on thread")
        
        #Check length of output
        if len(extracted_message) > self.yaml_data.assistant_response_max_length:
            self.logger.warning(f"Message exceeded character length ({self.yaml_data.assistant_response_max_length}), processing the gpt thread again")
            self.logger.debug(f"This is the gpt_assistants_prompt_shorten_response: {self.yaml_data.gpt_assistants_prompt_shorten_response}")
            
            # Add {message_to_shorten} to replacements_dict
            replacements_dict['message_to_shorten'] = extracted_message
            replacements_dict['original_thread_instructions'] = thread_instructions

            # Add original response #NOTE: FORMAT
            self.logger.debug(f"This is the extracted_message_incl_shorten_prompt: {self.yaml_data.gpt_assistants_prompt_shorten_response}")  
            try:
                response_thread_messages = await self._run_and_get_assistant_response_thread_messages(
                    assistant_id=assistant_id,
                    thread_id=thread_id,
                    thread_instructions=self.yaml_data.gpt_assistants_prompt_shorten_response,
                    replacements_dict=replacements_dict
                )
            except Exception as e:
                self.logger.error(f"Error running assistant on thread")
                self.logger.error(e)
                raise ValueError(f"Error running assistant on thread")
                        
            # Extract the latest response from the messages
            extracted_message = self._extract_latest_response_from_thread_messages(response_thread_messages)

        self.logger.debug("This is the response_thread_messages object:")
        self.logger.debug(response_thread_messages)
        self.logger.info(f"This is the final response from make_gpt_response_from_msghistory(): '{extracted_message}'")
        return extracted_message

if __name__ == "__main__":
    # Configuration and API key setup
    ConfigManager().initialize(yaml_filepath=r'C:\Users\Admin\OneDrive\Desktop\_work\__repos (unpublished)\_____CONFIG\chatzilla_ai\config\config.yaml')
    # config.gpt_assistants_prompt_article_summarizer

    # # Create client and manager instances
    # gpt_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    # gpt_base = GPTBaseClass(gpt_client=gpt_client)
    # gpt_clast_mgr = GPTAssistantManager(gpt_client=gpt_client, yaml_data=config)
    # gpt_thrd_mgr = GPTThreadManager(gpt_client=gpt_client, yaml_data=config)
    # gpt_resp_mgr = GPTResponseManager(gpt_client=gpt_client, yaml_data=config)
    
    # # article_summarizer - Create assistant
    # article_summarizer_assistant = gpt_clast_mgr.create_assistant(
    #     assistant_name='article_summarizer',
    #     assistant_instructions=config.gpt_assistants_prompt_article_summarizer
    # )

    # # article_summarizer - Create thread
    # article_summarizer_thread = gpt_thrd_mgr._create_thread(thread_name='article_summarizer')
    # article_summarizer_thread_id = gpt_thrd_mgr.threads['article_summarizer']['id']

    # random_article_content = "CNN — Wreaths, candles and calendars. These are sure signs of Advent for many Christian groups around the world. But what is Advent exactly? The word Advent derives from the Latin adventus, which means an arrival or visit. Advent is the beginning of the spiritual year for these churches, and it’s ob"

    # # article_summarizer - Add message to thread
    # gpt_thrd_mgr.add_message_to_thread(
    #     thread_id=article_summarizer_thread_id, 
    #     role='user', 
    #     message_content=random_article_content
    # )

    # # article_summarizer assistant+thread - Run workflow and retrieve response
    # gpt_response_text = asyncio.run(gpt_resp_mgr.make_gpt_response_from_msghistory(
    #     assistant_id=article_summarizer_assistant.id,
    #     thread_id=article_summarizer_thread_id,
    #     thread_instructions=config.gpt_assistants_prompt_article_summarizer
    # ))

    # article_summary_plotline = gpt_response_text

    # print(article_summary_plotline)