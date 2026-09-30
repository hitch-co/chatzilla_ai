import asyncio
import json
import re

from collections import defaultdict
from typing import Dict, List, Callable
import requests

from my_modules.my_logging import create_logger

from classes.ConfigManagerClass import ConfigManager

from my_modules import utils

gpt_base_debug_level = 'INFO'
gpt_thread_mgr_debug_level = 'INFO'
gpt_assistant_mgr_debug_level = 'INFO'
gpt_response_mgr_debug_level = 'INFO'

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
            debug_level=gpt_base_debug_level,
            logger_name='GPTBaseClass',
            stream_logs=True
            )
        self.gpt_client = gpt_client
        self.yaml_data = ConfigManager.get_instance()

        def create():
            print("did a create")
        def delete():
            print("did a delete")

    def get_models(self) -> dict:
        url = 'https://api.openai.com/v1/models'
        headers = {'Authorization': f'Bearer {self.yaml_data.openai_api_key}'}

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch models: {e}")
            return {}

class GPTFunctionCallManager(GPTBaseClass):
    """
    Returns structured decisions through Responses for existing function-call consumers.
    """

    def __init__(self, gpt_client, gpt_thread_manager, gpt_response_manager, gpt_assistant_manager):
        super().__init__(gpt_client)
        self.logger = create_logger(
            dirname='log',
            debug_level='INFO',
            logger_name='GPTFunctionCallManager',
            stream_logs=True
        )
        self.gpt_thread_manager = gpt_thread_manager
        self.gpt_response_manager = gpt_response_manager
        self.gpt_assistant_manager = gpt_assistant_manager

        # Initialize thread-specific locks
        self.thread_run_locks = defaultdict(asyncio.Lock)

    async def execute_function_call(
            self,
            thread_name: str, 
            assistant_name: str, 
            function_schema: json, 
            get_response=False
            ):
        """Returns the structured decision and no follow-up chat response."""
        if get_response:
            raise ValueError("Structured classifications do not generate a follow-up chat response.")

        assistant = self.gpt_assistant_manager.assistants[assistant_name]
        function = function_schema['function']
        text_format = {
            'type': 'json_schema',
            'name': function['name'],
            'description': function['description'],
            'schema': function['parameters'],
            'strict': True
        }

        async with self.thread_run_locks[thread_name]:
            self.logger.info(f"Classifying thread '{thread_name}' with assistant '{assistant_name}' using Responses")
            response = await self.gpt_response_manager._create_response(
                assistant_name=assistant_name,
                thread_name=thread_name,
                thread_instructions=assistant['instructions'],
                text_format=text_format
            )
            output_data = json.loads(response)
            self.logger.info(f"...Output data: {output_data}")
            return output_data, None

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
        assistants (dict): A dictionary of local assistant configurations.
    """
    def __init__(self, gpt_client):
        super().__init__(gpt_client)
        self.logger = create_logger(
            dirname='log', 
            debug_level=gpt_assistant_mgr_debug_level,
            logger_name='GPTAssistantManager',
            stream_logs=True
            )
        self.assistants = {}

    def _create_assistant(
            self, 
            assistant_name, 
            assistant_instructions="you're a question answering machine", 
            replacements_dict: dict=None,
            assistant_model=None
            ):
        """
        Registers a local assistant configuration with the specified parameters.

        Args:
            assistant_name (str): The name of the assistant to create. Default is 'default'.
            assistant_instructions (str): Instructions for the assistant. Default is a generic instruction.
            assistant_model: The model of the assistant. Defaults to the model specified in the configuration.

        Returns:
            The local assistant configuration dictionary.
        """
        assistant_model = assistant_model or self.yaml_data.gpt_model
        assistant_instructions = utils.populate_placeholders(
            logger=self.logger,
            prompt_template=assistant_instructions,
            replacements=replacements_dict
            )
        
        assistant = {
            'name': assistant_name,
            'instructions': assistant_instructions,
            'model': assistant_model
        }
        self.assistants[assistant_name] = assistant

        self.logger.info(f"Local assistant configured for '{assistant_name}' with instructions: {assistant_instructions[0:100]}...")
        if replacements_dict:
            self.logger.debug(f"Replacements Dict: {replacements_dict}")
        self.logger.debug(assistant)
        return assistant

    def create_assistants(self, assistants_config: dict) -> dict:
        """
            assistants_config: A dictionary of assistant names and their prompts.
        """
        self.logger.info('Creating GPT Assistants')
        self.assistants = {}
        replacements_dict = {
            "wordcount_short":self.yaml_data.wordcount_short,
            "wordcount_medium":self.yaml_data.wordcount_medium,
            "wordcount_long":self.yaml_data.wordcount_long,
            "vibecheckee_username": 'chad',
            "vibecheck_message_wordcount": self.yaml_data.vibechecker_message_wordcount,
            "bot_archetype": self.yaml_data.gpt_bot_archetype_prompt
        }

        # Get suffix one from assistants_config
        gpt_assistants_suffix = self.yaml_data.gpt_assistants_suffix

        for assistant_name, prompt in assistants_config.items():
            final_prompt = prompt + gpt_assistants_suffix
            self._create_assistant(
                assistant_name=assistant_name,
                assistant_instructions=final_prompt,
                replacements_dict=replacements_dict,
                assistant_model=self.yaml_data.gpt_model
            )        
        return self.assistants

    def _create_assistant_with_function(self, assistant_name, instructions, function_schema):
        """
        Registers a local assistant configuration with its structured decision schema.
        """
        self.assistants[assistant_name] = {
            'name': assistant_name,
            'instructions': instructions,
            'model': self.yaml_data.gpt_model,
            'tools': [function_schema]
        }
        self.logger.info(f"Local assistant configured for '{assistant_name}' with function schema")

    def create_assistants_with_functions(self, assistants_with_functions: list):
        """
        Creates multiple assistants with their respective function schemas.

        Args:
            assistants_with_functions (list): A list of dictionaries, each containing
                                            'name', 'instructions', and 'json_schema'.
        Returns:
            dict: A dictionary of local assistant configurations.
        """
        self.logger.info('Creating GPT Assistants with functions')

        for assistant_details in assistants_with_functions:
            name = assistant_details["name"]
            instructions = assistant_details["instructions"]
            json_schema = assistant_details["json_schema"]
            self.logger.debug(f'Creating assistant with function: {name}')
            self.logger.debug(f'Instructions: {instructions}')
            self.logger.debug(f"Json Schema Type: {type(json_schema)}")
            self.logger.debug(f'JSON Schema: {json_schema}')

            try:
                self._create_assistant_with_function(
                    assistant_name=name,
                    instructions=instructions,
                    function_schema=json_schema
                )
                self.logger.info(f"Assistant '{name}' created successfully.")
            except Exception as e:
                self.logger.error(f"Error creating assistant '{name}': {e}")

        self.logger.info(f"Current assistants: {list(self.assistants.keys())}")
        return self.assistants

class GPTThreadManager(GPTBaseClass):
    def __init__(self, gpt_client):
        super().__init__(gpt_client=gpt_client)
        self.logger = create_logger(
            dirname='log', 
            debug_level=gpt_thread_mgr_debug_level,
            logger_name='GPTThreadManager',
            stream_logs=True
        )

        self.threads: Dict[str, dict] = {}

    def _create_thread(self, thread_name: str):
        """
        Creates local message history with the given thread name.

        Args:
            thread_name (str): The name of the thread to be created.

        """
        self.threads[thread_name] = {'messages': []}

        self.logger.info(f"Created local thread '{thread_name}'")

    def create_threads(self, thread_names):
        self.logger.info('Creating GPT Threads')
        for thread_name in thread_names:

            #NOTE: Part of 'reusing threads' logic
            #If thread does not exist, create it
            if thread_name not in self.threads:
                self._create_thread(thread_name)
            else:
                self.logger.warning(f"Thread '{thread_name}' already exists")

        self.logger.info(f"...threads created: {self.threads}")        
        return self.threads

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
    def __init__(self, gpt_client, gpt_thread_manager, gpt_assistant_manager, max_waittime_for_gpt_response=120):
        super().__init__(gpt_client=gpt_client)
        self.logger = create_logger(
            dirname='log', 
            debug_level=gpt_response_mgr_debug_level,
            logger_name='GPTResponseManager',
            stream_logs=True
            )
        self.gpt_thread_manager = gpt_thread_manager
        self.gpt_assistant_manager = gpt_assistant_manager
        self.max_waittime_for_gpt_response = max_waittime_for_gpt_response

    async def _create_response(self, assistant_name, thread_name, thread_instructions, replacements_dict=None, text_format=None):
        assistant = self.gpt_assistant_manager.assistants[assistant_name]
        final_thread_instructions = utils.populate_placeholders(
            logger=self.logger,
            prompt_template=thread_instructions,
            replacements=replacements_dict
        )
        if text_format is None:
            response_style = utils.populate_placeholders(
                logger=self.logger,
                prompt_template=self.yaml_data.gpt_assistants_suffix,
                replacements={'wordcount_short': self.yaml_data.wordcount_short}
            )
            final_thread_instructions += f"\n{response_style}\nYour bot archetype is: {self.yaml_data.gpt_bot_archetype_prompt}."
        messages = list(self.gpt_thread_manager.threads[thread_name]['messages'])
        response_options = {}
        if text_format is not None:
            response_options['text'] = {'format': text_format}
        response = await asyncio.to_thread(
            self.gpt_client.responses.create,
            model=assistant['model'],
            instructions=final_thread_instructions if messages else None,
            input=messages or [{'role': 'developer', 'content': final_thread_instructions}],
            store=False,
            timeout=self.max_waittime_for_gpt_response,
            **response_options
        )
        if response.status != 'completed':
            raise RuntimeError(f"Response {response.id} did not complete: status={response.status}, error={response.error}, incomplete_details={response.incomplete_details}")
        if not response.output_text.strip():
            raise ValueError(f"No assistant text found for response {response.id}")
        return response.output_text

    async def execute_thread(
        self, 
        assistant_name: str, 
        thread_name: str, 
        thread_instructions: str, 
        replacements_dict=None
        ) -> str:
        """
        Executes the workflow to get the GPT assistant's response to a thread.

        Args:
            assistant_name (str): The local assistant configuration name.
            thread_name (str): The local message history name.
            thread_instructions (str): Instructions for the assistant.

        Returns:
            The final response message from the assistant.
        """
        self.logger.info(f"Scheduler-3: Executing Assistant/Thread: '{assistant_name}' / '{thread_name}' using Responses")
        self.logger.info(f"...Thread_instructions: {thread_instructions[0:50]}...")

        try:
            extracted_message = await self._create_response(
                assistant_name=assistant_name,
                thread_name=thread_name,
                thread_instructions=thread_instructions,
                replacements_dict=replacements_dict
            )        
            self.logger.debug(f"...Extracted message and length: ({len(extracted_message)}) Message: {extracted_message}")
        except Exception as e:
            self.logger.error(f"...Error running assistant on thread: {e}")
            raise ValueError(f"...Error running assistant on thread: {e}")
        
        #Check length of output
        if len(extracted_message) > self.yaml_data.assistant_response_max_length:
            self.logger.warning(f"...Message exceeded character length ({self.yaml_data.assistant_response_max_length}), processing the gpt thread again")
            self.logger.debug(f"...This is the shorten_response_length_prompt: {self.yaml_data.shorten_response_length_prompt}")
            
            # Add {message_to_shorten} to replacements_dict
            replacements_dict = dict(replacements_dict or {})
            original_thread_instructions = utils.populate_placeholders(
                logger=self.logger,
                prompt_template=thread_instructions,
                replacements=replacements_dict
            )
            replacements_dict['message_to_shorten'] = extracted_message
            replacements_dict['original_thread_instructions'] = original_thread_instructions

            try:
                extracted_message = await self._create_response(
                    assistant_name=assistant_name,
                    thread_name=thread_name,
                    thread_instructions=self.yaml_data.shorten_response_length_prompt,
                    replacements_dict=replacements_dict
                )
            except Exception as e:
                self.logger.error(f"...Error running assistant on thread")
                self.logger.error(e)
                raise ValueError(f"...Error running assistant on thread")
                        
        bot_names = '|'.join(re.escape(name) for name in (
            self.yaml_data.twitch_bot_username, self.yaml_data.twitch_bot_display_name
        ) if name)
        if bot_names:
            extracted_message = re.sub(rf'^\s*(?:{bot_names})\s*:\s*', '', extracted_message, count=1, flags=re.IGNORECASE)
        self.logger.info(f"...This is the final response from execute_thread(): '{extracted_message}'")
        return extracted_message

    async def add_message_to_thread(
            self, 
            message_content: str, 
            thread_name: str, 
            role='user'
            ) -> object:
        """
        Adds a message to the local history for the specified thread.

        Args:
            message_content (str): The textual content of the message to be added to the thread.
            thread_name (str): The name of the thread to which the message will be added. The thread must be previously created and registered.
            role (str): Specifies the role of the entity sending the message. Must be either 'user' or 'assistant'.
                        The default role is 'user'.

        Returns:
            The message dictionary, or None if the specified thread does not exist.

        Raises:
            ValueError: If the 'role' parameter is not 'user' or 'assistant'.
        """
        self.logger.debug(f"Message content (role: {role}, thread_name: {thread_name}): {message_content[0:50]}...")
        
        # Validate the role
        if role not in ['user', 'assistant']:
            raise ValueError(f"Invalid role: {role}. Role must be 'user' or 'assistant'.")

        if thread_name in self.gpt_thread_manager.threads:
            message_object = {'role': role, 'content': message_content}
            messages = self.gpt_thread_manager.threads[thread_name]['messages']
            messages.append(message_object)
            del messages[:-self.yaml_data.msg_history_limit]
            self.logger.info(f"... added message to local thread ({thread_name}): Message content {message_content[0:50]}...")
            return message_object
        else:
            self.logger.warning(f"Thread '{thread_name}' not found.")
            return None

async def main(director_messages=None):
    import dotenv
    import os
    import openai

    dotenv_load_result = dotenv.load_dotenv(dotenv_path='./config/.env')
    yaml_filepath=os.getenv('CHATZILLA_CONFIG_YAML_FILEPATH')
    ConfigManager.initialize(yaml_filepath)
    config = ConfigManager.get_instance()

    # openai client
    gpt_client = openai.OpenAI(api_key = config.openai_api_key)

    # Initialize the thread manager and assistant manager and response manager
    assistant_manager = GPTAssistantManager(gpt_client)
    thread_manager = GPTThreadManager(gpt_client)
    response_manager = GPTResponseManager(gpt_client, thread_manager, assistant_manager)
    function_call_manager = GPTFunctionCallManager(gpt_client, thread_manager, response_manager, assistant_manager)

    assistant_manager.create_assistants(config.gpt_assistants_config)
    assistant_manager.create_assistants_with_functions(config.gpt_assistants_with_functions_config)

    thread_manager.create_threads(config.gpt_thread_names)

    thread_name = "chatformemsgs"
    if director_messages is not None:
        try:
            for message in director_messages:
                await response_manager.add_message_to_thread(message, thread_name)
            output_data, response = await function_call_manager.execute_function_call(
                thread_name=thread_name,
                assistant_name='conversationdirector',
                function_schema=config.function_schemas['conversationdirector']
            )
            print(f"Director decision: {json.dumps(output_data)}")
        finally:
            gpt_client.close()
        return

    response = await response_manager.execute_thread(
        thread_name=thread_name,
        assistant_name='chatforme',
        thread_instructions=config.hello_assistant_prompt,
        replacements_dict={
            'wordcount': config.wordcount_veryshort,
            'twitch_bot_display_name': config.twitch_bot_display_name,
            'twitch_bot_channel_name': config.twitch_bot_channel_name,
            'param_in_text': 'variable_from_scope',
            'bot_archetype': config.gpt_bot_archetype_prompt
        }
    )
    print(f"Assistant's Response: {response}")
    gpt_client.close()

# Run the async main function
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--director', nargs='*', metavar='MESSAGE',
                        help='Classify optional messages instead of generating the startup greeting.')
    args = parser.parse_args()
    asyncio.run(main(director_messages=args.director))
