
import os
import requests
import openai
import tiktoken
from typing import List
import re
import asyncio
import json

from jsonschema import validate, ValidationError

from classes.ConfigManagerClass import ConfigManager

from my_modules.my_logging import create_logger
import modules.gpt_utils as gpt_utils

class GPTChatCompletion:
    def __init__(self, gpt_client=None, yaml_data=None):
        self.config = yaml_data
        self.gpt_client = gpt_client

        #LOGGING
        stream_logs = True
        runtime_logger_level = 'INFO'

        self.logger = create_logger(
            dirname='log',
            logger_name='GPTChatCompletionClass',
            debug_level=runtime_logger_level,
            mode='w',
            stream_logs=stream_logs
            )

    async def make_singleprompt_gpt_response(
            self,
            prompt_text, 
            replacements_dict=None,
            model=None
            ) -> str:
        """
        Asynchronously generates a GPT response for a single prompt.

        This method takes a single prompt, optionally applies replacements, and generates a response using the GPT model. It also handles sending the response and optionally playing the corresponding voice message.

        Parameters:
        - prompt_text (str): The text prompt to generate a response for.
        - replacements_dict (dict, optional): A dictionary of replacements to apply to the prompt text.
        - incl_voice (str): Specifies whether to include voice output (True or False). Default is True.
        - voice_name (str): The name of the voice to be used in the text-to-speech service. Default is 'nova'.

        Returns:
        - str: The generated GPT response.

        """
        self.logger.info(f"Entered 'make_singleprompt_gpt_response'")
        self.logger.info(f"...model: {model}")
        self.logger.info(f"...prompt_text: {prompt_text}")
        self.logger.info(
            "...replacements_dict: " +
            str({k: (v[:50] + '...' if len(v) > 50 else v) for k, v in replacements_dict.items()})
        )
        
        try:
            prompt_text = gpt_utils.replace_prompt_text(
                logger = self.logger,
                prompt_template=prompt_text,
                replacements = replacements_dict
                )
            self.logger.info(f"...Replaced prompt_text: {prompt_text}")
            
            prompt_listdict = self._make_string_gptlistdict(
                prompt_text=prompt_text,
                prompt_text_role='user'
                )
            self.logger.info(f"...prompt_listdict: {prompt_listdict}")
            try:
                gpt_response = self._openai_gpt_chatcompletion(
                    messages=prompt_listdict,
                    model=model
                    )
                self.logger.info(f"...Generated GPT response: {gpt_response}")
            except Exception as e:
                self.logger.error(f"Error occurred in '_openai_gpt_chatcompletion': {e}")        
        except Exception as e:
            self.logger.error(f"Error occurred in 'make_singleprompt_gpt_response': {e}", exc_info=True)

        self.logger.info(f"prompt_text: {prompt_text}")
        self.logger.info(f"final gpt_response: {gpt_response}")
        return gpt_response
    
    def _openai_gpt_chatcompletion(
            self,
            messages: list[dict],
            max_characters: int = 300,
            count_tokens: bool = False,
            max_attempts: int = 3,
            frequency_penalty: float = 1.0,
            presence_penalty: float = 1.0,
            temperature: float = 0.6,
            model: str = None,
            message_count: int = 5
            ) -> str: 
        """
        Sends a list of messages to the OpenAI GPT self.config.gpt_model and retrieves a generated response.

        This function interacts with the OpenAI GPT self.config.gpt_model to generate responses based on the provided message structure. It attempts to ensure the response is within a specified character limit, retrying up to a maximum number of attempts if necessary.

        Parameters:
        - messages (list[dict]): A list of dictionaries, each representing a message in the conversation history, formatted for the GPT prompt.
        - max_characters (int): Maximum allowed character count for the generated response. Default is 200 characters.
        - max_attempts (int): Maximum number of attempts to generate a response within the character limit. Default is 5 attempts.
        - frequency_penalty (float): The frequency penalty parameter to control repetition in the response. Default is 1.
        - presence_penalty (float): The presence penalty parameter influencing the introduction of new concepts in the response. Default is 1.
        - temperature (float): Controls randomness in the response generation. Lower values make responses more deterministic. Default is 0.6.

        Returns:
        - str: The content of the message generated by the GPT self.config.gpt_model. If the maximum number of attempts is exceeded without generating a response within the character limit, an exception is raised.

        Raises:
        - ValueError: If the initial message exceeds a token limit after multiple attempts to reduce its size.
        - Exception: If the maximum number of retries is exceeded without generating a valid response.
        """

        def _strip_prefix(text):
            # Regular expression pattern to match the prefix <<<[some_name]>>>:
            # Use re.sub() to replace the matched pattern with an empty string
            pattern = r'<<<[^>]*>>>'
            stripped_text = re.sub(pattern, '', text)

            #finally, strip out any extra colons that typically tend to prefix the message.
            #Sometimes it can be ":", ": :", " : ", etc. Only strip if it's the first characters (excluding spaces) 
            stripped_text = stripped_text.lstrip(':').lstrip(' ').lstrip(':').lstrip(' ') 

            return stripped_text

        model = model or self.config.gpt_model
        self.logger.info(f"This is the messages submitted to GPT ChatCompletion with model {model}: {messages[-message_count:]}")
        
        # TODO: This loop is wonky.  Should probably divert to a 'while' statement
        for attempt in range(max_attempts):
            self.logger.info(f"THIS IS ATTEMPT #{attempt + 1}")
            try:
                generated_response = self.gpt_client.chat.completions.create(
                    model=self.config.gpt_model,
                    messages=messages,
                    presence_penalty=presence_penalty,
                    frequency_penalty=frequency_penalty,
                    temperature=temperature
                )
            except Exception as e:
                self.logger.error(f"Exception occurred during API call: {e}: Attempt {attempt + 1} of {max_attempts} failed.")
                continue

            self.logger.info(f"Completed generated response using self.gpt_client.chat.completions.create")          
            gpt_response_text = generated_response.choices[0].message.content
            gpt_response_text_len = len(gpt_response_text)
    
            self.logger.info(f"generated_response type: {type(generated_response)}, length: {gpt_response_text_len}:")
            if gpt_response_text_len < max_characters:
                self.logger.info(f'OK: The generated message was <{max_characters} characters')
                self.logger.info(f"gpt_response_text: {gpt_response_text}")
                break
            else: # Did not get a msg < n chars, try again.
                self.logger.warning(f'gpt_response_text_len: >{max_characters} characters, retrying call to _openai_gpt_chatcompletion')
                messages_updated = [{'role':'user', 'content':f"{self.config.shorten_response_length_prompt}: '{gpt_response_text}'"}]
                generated_response = self.gpt_client.chat.completions.create(
                    model=self.config.gpt_model,
                    messages=messages_updated,
                    presence_penalty=presence_penalty,
                    frequency_penalty=frequency_penalty,
                    temperature=temperature
                    )
                gpt_response_text = generated_response.choices[0].message.content
                gpt_response_text_len = len(gpt_response_text)

                if gpt_response_text_len > max_characters:
                    self.logger.warning(f'gpt_response_text length was {gpt_response_text_len} characters (max: {max_characters}), trying again...')
                elif gpt_response_text_len < max_characters:
                    self.logger.info(f"OK on attempt --{attempt}-- gpt_response_text: {gpt_response_text}")
                    break
        else:
            message = "Maxium GPT call retries exceeded"
            self.logger.error(message)        
            raise Exception(message)

        # Strip the prefix from the response
        gpt_response_text = _strip_prefix(gpt_response_text)
        
        return gpt_response_text

    async def make_singleprompt_gpt_response_json(self, model, chat_history, schema) -> dict:
        self.logger.info(f"Entered 'make_singleprompt_gpt_response_json', result will be 'fact' or 'respond'")
        
        if chat_history is None:
            chat_history = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant. There is no prior chat history."
                }
            ]
        
        response_text_full = self.gpt_client.chat.completions.create(
            model=model,
            messages=chat_history,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "conversation_director",
                    "schema": schema,
                    "strict": True
                }
            }
        )

        self.logger.info(f"...chat_history: \n{chat_history}")
        self.logger.debug(f"...response_text_full: {response_text_full}")
        response_data = json.loads(response_text_full.choices[0].message.content)
        self.logger.info(f"...response_type: {response_data['response_type']}")
        self.logger.info(f"...reasoning: {response_data['reasoning']}")

        return response_data

    def _make_string_gptlistdict(
            self,
            prompt_text, 
            prompt_text_role='user'
            ) -> list[dict]:
        """
        Returns:
        - list[dict]: A list containing a single dictionary with the message text and role.
        """
        prompt_listdict = [{'role': prompt_text_role, 'content': f'{prompt_text}'}]
        return prompt_listdict
    
    def get_models(self):
        """
        Function to fetch the available models from the OpenAI API.

        Args:
            api_key (str): The API key for the OpenAI API.

        Returns:
            dict: The JSON response from the API containing the available models.
        """
        url = 'https://api.openai.com/v1/models'
        headers = {'Authorization': f'Bearer {self.config.openai_api_key}'}
        response = requests.get(url, headers=headers)

        return response.json()

if __name__ == '__main__':
    import time
    import json
    ConfigManager.initialize(yaml_filepath=r'C:\_repos\chatzilla_ai\config\bot_user_configs\chatzilla_ai_ehitch.yaml')
    config = ConfigManager.get_instance()
    gpt_client = openai.OpenAI(api_key = config.openai_api_key)
    gpt_chat_completion = GPTChatCompletion(gpt_client=gpt_client, yaml_data=config)

    ############################
    # # test1 -- _openai_gpt_chatcompletion_json

    #load json from file
    with open(r'C:\_repos\chatzilla_ai\config\conversation_director_response_format.json', 'r') as f:
        conversation_director_response_format = json.load(f)
    print(f"type: {type(conversation_director_response_format)}")
    print(conversation_director_response_format)

    messages=[
        {'role':'user', 'content':'crube: going ok. heading out soonly to visit my cousins'},
        {'role':'user', 'content':'crube: my computer still screams when it wakes up, but stops after like 5 minutes'},
        {'role':'user', 'content':'crube: watch football. hang out mostly'}, 
        {'role':'user', 'content':'ehitch: Yeah wooooh!'}
        ]

    response = asyncio.run(gpt_chat_completion.make_singleprompt_gpt_response_json(
        model="gpt-4o-mini", #"gpt-4-1106-preview", #"gpt-4o-mini", #"gpt-4o-2024-08-06", #config.gpt_model_davinci,
        chat_history=messages,
        schema=conversation_director_response_format
        ))
    
    print(f"type: {type(response)}")
    print(response)

    ############################
    # # test2 -- Get models
    # gpt_models = gpt_chat_completion.get_models()
    # print("GPT Models:")
    # print(json.dumps(gpt_models, indent=4))

    ############################
    # # test3 -- call to chatgpt chatcompletion
    # gpt_chat_completion._openai_gpt_chatcompletion(
    #     messages=[
    #         {'role':'user', 'content':'Whats a tall buildings name?'}, 
    #         {'role':'user', 'content':'Whats a tall Statues name?'}
    #         ],
    #     max_characters=config.assistant_response_max_length,
    #     max_attempts=5,
    #     frequency_penalty=1,
    #     presence_penalty=1,
    #     temperature=0.7
    #     )

    ############################
    # # # Test4 -- call to make_singleprompt_gpt_response
    # # Measure time to complete
    # start = time.time()
    # response = asyncio.run(gpt_chat_completion.make_singleprompt_gpt_response(
    #     prompt_text=r"What is the tallest building in {country}?",
    #     replacements_dict={'country':'Dubai'},
    #     model=config.model
    #     ))
    # end = time.time()
    # print(f"Time to complete: {end - start}")
    # print(f"This is the GPT Response: {response}")

    ############################
    # # # Test5 -- call to make_singleprompt_gpt_response_json
    # # Measure time to complete
    # start = time.time()
    # response = asyncio.run(gpt_chat_completion.make_singleprompt_gpt_response_json(
    #     prompt_text="""You are part of a control flow system that decides if the chatbot should 
    #     engage directly or share a general fact. Using the following conversation 
    #     history: '{chat_history}', determine the 'response_type' as follows:

    #     Output only a JSON object with these two attributes:
    #         'response_type': '<respond or fact>',
    #         'content': '<brief explanation for decision>'

    #     Guidelines:
    #     - In 100% of cases your response should be a JSON object as described, not a text output
    #     - Set 'response_type' to 'respond' only if the conversation clearly invites 
    #       engagement or would benefit from direct interaction.
    #     - If the conversation lacks questions or active engagement, set 'response_type' 
    #       to 'fact' for a neutral, informative contribution.
    #     - If you were the last speaker and no one responded, choose 'fact' to avoid 
    #       repetition.
    #     - Even if a conversation was previously active, respond only when it adds 
    #       clear value—otherwise, default to 'fact.'
    #     - When users don’t acknowledge your responses or questions, assume 'fact' is 
    #       appropriate.
    #     - Again, you're not a significant part of this conversation, so use 'fact' 
    #       more often than 'respond' to avoid dominating the chat.
    #     - Don't get sucked into the conversation; response should be 'fact' unless 
    #       the conversation clearly invites engagement.
    #     - Don't be a victim by responding to every message. Response value should be 
    #       'fact' unless the conversation clearly invites engagement.

    #     Note:
    #     'response_type' should default to 'fact' more often than 'respond,' aligning 
    #     with the bot's informational role in ongoing streams.""",
    #     replacements_dict={'country':'Dubai'},
    #     model=config.model
    #     ))
    # end = time.time()

