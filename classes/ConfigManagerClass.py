import os
import yaml
import dotenv
import json

from my_modules.my_logging import create_logger
from my_modules import utils

runtime_logger_level = 'DEBUG'

class ConfigManager:
    _instance = None

    @classmethod
    def initialize(cls, yaml_filepath):

        #full path to the yaml file
        yaml_filepath = os.path.abspath(yaml_filepath)

        if cls._instance is None:
            try:
                cls._instance = object.__new__(cls)
            except Exception as e:
                print(f"Exception in object.__new__(cls): {e}")
            
            try:
                cls._instance.create_logger()
            except Exception as e:
                print(f"Exception in create_logger(): {e}")

            try:
                cls._instance.initialize_config(yaml_filepath=yaml_filepath)
            except Exception as e:
                print(f"Exception in initialize_config(): {e}")

    @classmethod
    def get_instance(cls):
        try:
            if cls._instance is None:
                raise Exception("ConfigManager is not initialized. Call 'initialize' first.")
            return cls._instance
        except Exception as e:
            print(f"Exception in get_instance(): {e}")

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
        else:
            raise Exception("You cannot create multiple instances of ConfigManager. Use 'get_instance'.")

    def initialize_config(self, yaml_filepath):
        # Get YAML configurations
        try:
            self.load_yaml_config(yaml_full_path=yaml_filepath)
        except Exception as e:
            self.logger.error(f"Error, exception in load_yaml_config(): {e}", exc_info=True)

        # Set environment variables from .env file
        try:
            self.set_env_file_variables()
        except Exception as e:
            self.logger.error(f"Error, exception in set_env_file_variables(): {e}", exc_info=True)

        # Log the configuration
        try:
            self._log_config()
        except Exception as e:
            self.logger.error(f"Error, exception in log_config(): {e}", exc_info=True)
                              
    def _log_config(self):
        # Primary Configurations
        self.logger.debug(f'------------------------------')
        self.logger.debug(f'--- Primary Configurations ---')
        self.logger.debug(f"CHATZILLA_PORT_NUMBER: {self.CHATZILLA_PORT_NUMBER}")
        self.logger.debug(f"Bot: {self.twitch_bot_username}") 
        self.logger.debug(f"Channel: {self.twitch_bot_channel_name}")
        self.logger.debug(f".env filepath: {self.env_path}")
        self.logger.debug(f".env.keys filepath: {self.keys_env_path}")
        self.logger.debug(f".yaml filepath: {self.app_config_dirpath}")
        
        # Secondary Configurations
        self.logger.debug(f'------------------------------')
        self.logger.debug(f'--- Secondary Configurations ---')
        self.logger.debug(f"self.twitch_bot_gpt_hello_world: {self.twitch_bot_gpt_hello_world}")
        self.logger.debug(f"randomfact_topics_json_filepath: {self.randomfact_topics_json_filepath}")
        self.logger.debug(f"randomfact_areas_json_filepath: {self.randomfact_areas_json_filepath}")
        self.logger.debug(f"randomfact_prompt: {self.randomfact_prompt}")
        self.logger.debug(f"keys_env_dirpath: {self.keys_env_dirpath}")
        self.logger.debug(f"tts_data_folder: {self.tts_data_folder}")
        self.logger.debug(f"tts_file_name: {self.tts_file_name}")
        self.logger.debug(f"gpt_assistants_config: {self.gpt_assistants_config}")
        self.logger.debug(f"newusers_sleep_time: {self.newusers_sleep_time}")
        self.logger.debug(f"gpt_assistants_suffix: {self.gpt_assistants_suffix}")
        self.logger.debug(f"chatzilla_mic_device_name: {self.chatzilla_mic_device_name}")

    def load_yaml_config(self, yaml_full_path):
        try:
            with open(yaml_full_path, 'r') as file:
                self.logger.debug("loading individual configs...")
                yaml_config = yaml.safe_load(file)
        except FileNotFoundError as e:
            self.logger.error(f"Error in load_yaml_config(): {e}")
            raise
        except yaml.YAMLError as e:
            self.logger.error(f"Error in load_yaml_config(): {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error in load_yaml_config(): {e}")
            raise

        try:
            self.update_config_from_yaml(yaml_config)
        except Exception as e:
            self.logger.error(f"Error in update_config_from_yaml(): {e}")
            raise
        
        try:
            self.yaml_twitchbot_config(yaml_config) 
        except Exception as e:
            self.logger.error(f"Error in yaml_twitchbot_config(): {e}")
            raise

        try:
            self.yaml_depinjector_config(yaml_config)
        except Exception as e:
            self.logger.error(f"Error in yaml_depinjector_config(): {e}")
            raise

        try:
            self.update_spellcheck_config(yaml_config)
        except Exception as e:
            self.logger.error(f"Error in update_spellcheck_config(): {e}")
            raise

        try:
            self.yaml_gcp_config(yaml_config)
        except Exception as e:
            self.logger.error(f"Error in yaml_gcp_config(): {e}")
            raise

        try:       
            self.yaml_botears_config(yaml_config)
        except Exception as e:
            self.logger.error(f"Error in yaml_botears_config(): {e}")
            raise

        try:
            self.yaml_gpt_config(yaml_config)
        except Exception as e:
            self.logger.error(f"Error in yaml_gpt_config(): {e}")
            raise

        try:
            self.yaml_gpt_voice_config(yaml_config)
        except Exception as e:
            self.logger.error(f"Error in yaml_gpt_voice_config(): {e}")
            raise

        try:
            self.yaml_gpt_explain_config(yaml_config)
        except Exception as e:
            self.logger.error(f"Error in yaml_gpt_explain_config(): {e}")      
            raise

        try:
            self.yaml_gpt_thread_config(yaml_config)
        except Exception as e:
            self.logger.error(f"Error in yaml_gpt_thread_config(): {e}")
            raise

        try:
            self.yaml_gpt_assistant_config(yaml_config)
        except Exception as e:
            self.logger.error(f"Error in yaml_gpt_assistant_config(): {e}")
            raise

        try:
            self.yaml_chatforme_config(yaml_config)
        except Exception as e:
            self.logger.error(f"Error in yaml_chatforme_config(): {e}")
            raise

        try:
            self.yaml_ouat_config(yaml_config)
        except Exception as e:
            self.logger.error(f"Error in yaml_ouat_config(): {e}")
            raise

        try:
            self.yaml_vibecheck_config(yaml_config)
        except Exception as e:
            self.logger.error(f"Error in yaml_vibecheck_config(): {e}")
            raise
        
        try:
            self.yaml_helloworld_config(yaml_config)
        except Exception as e:
            self.logger.error(f"Error in yaml_helloworld_config(): {e}")
            raise

        try:
            self.yaml_gpt_assistants_with_functions_config(yaml_config)
        except Exception as e:
            self.logger.error(f"Error in yaml_gpt_assistants_with_functions_config(): {e}")
            raise

        try:
            self.yaml_factchecker_config(yaml_config)
        except Exception as e:
            self.logger.error(f"Error in yaml_factchecker_config(): {e}")
            raise

        try:
            self.yaml_tts_config(yaml_config)
        except Exception as e:
            self.logger.error(f"Error in yaml_tts_config(): {e}")
            raise

        try:
            self.yaml_randomfact_json(yaml_config)
        except Exception as e:
            self.logger.error(f"Error in yaml_randomfact_json(): {e}")
            raise

    def set_env_file_variables(self):
        '''Loads environment variables from a .env file.'''
        
        # Load environment variables set at runtime
        self._update_config_from_env_set_at_runtime()
        
        # Load environment variables from .env.keys file
        if self.keys_env_dirpath and self.keys_env_filename:
            self.keys_env_path = os.path.join(self.keys_env_dirpath, self.keys_env_filename)
            if os.path.exists(self.keys_env_path):
                dotenv.load_dotenv(self.keys_env_path)
                self._update_config_from_env_keys()
            else:
                self.logger.error(f".env file not found at {self.keys_env_path}")

        # Load environment variables from .env file
        if self.env_dirpath and self.env_filename:
            self.env_path = os.path.join(self.env_dirpath, self.env_filename)
            if os.path.exists(self.env_path):
                dotenv.load_dotenv(self.env_path)
                self._update_config_from_env()
            else:
                self.logger.error(f".env file not found at {self.env_path}")

    def _update_config_from_env_set_at_runtime(self):
        try:
            self.CHATZILLA_PORT_NUMBER = str(os.getenv("CHATZILLA_PORT_NUMBER"))
        except Exception as e:
            self.logger.error(f"Error in update_config_from_env_set_at_runtime(): {e}")

    def _update_config_from_env_keys(self):
        try:
            # OpenAI API
            self.openai_api_key = os.getenv('OPENAI_API_KEY')
            
            # Twitch API
            self.twitch_broadcaster_author_id = os.getenv('TWITCH_BROADCASTER_AUTHOR_ID')
            self.twitch_bot_client_id = os.getenv('TWITCH_BOT_CLIENT_ID')
            self.twitch_bot_client_secret = os.getenv('TWITCH_BOT_CLIENT_SECRET')

        except Exception as e:
            self.logger.error(f"Error in update_config_from_env(): {e}")

    def _update_config_from_env(self):
        try:
            self.chatzilla_mic_device_name = os.getenv('CHATZILLA_MIC_DEVICE_NAME')
        except Exception as e:
            self.logger.error(f"Error in update_config_from_env(): {e}")

    def yaml_tts_config(self, yaml_config):
        try:
            self.tts_include_voice = yaml_config['openai-api']['tts_include_voice']
        except Exception as e:
            self.logger.error(f"Error in yaml_tts_config(): {e}")

    def yaml_gcp_config(self, yaml_config):
        try:
            self.keys_env_dirpath = yaml_config['keys_env_dirpath']

            self.google_service_account_credentials_file = yaml_config['google_service_account_credentials_file']

            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join(
                self.keys_env_dirpath, 
                self.google_service_account_credentials_file
                )
        except Exception as e:
            self.logger.error(f"Error in yaml_gcp_config(): {e}\nTraceback:", exc_info=True)

    def yaml_botears_config(self, yaml_config):
        try:
            self.botears_devices_json_filepath = yaml_config['botears_devices_json_filepath']
            self.botears_prompt = yaml_config['botears_prompt']
            self.botears_audio_path = yaml_config['botears_audio_path']
            self.botears_audio_filename = yaml_config['botears_audio_filename']
            self.botears_save_length_seconds = yaml_config['botears_save_length_seconds']
            self.botears_buffer_length_seconds = yaml_config['botears_buffer_length_seconds']

        except Exception as e:
            self.logger.error(f"Error in yaml_botears_config(): {e}")

    def yaml_gpt_config(self, yaml_config):
        try:
            self.wordcount_short = str(yaml_config['chatbot_config']['wordcounts']['short']) #2024-06-09: shouldn't these be captured as ints and typecasted when used?
            self.wordcount_medium = str(yaml_config['chatbot_config']['wordcounts']['medium'])
            self.wordcount_long = str(yaml_config['chatbot_config']['wordcounts']['long'])
            self.magic_max_waittime_for_gpt_response = int(yaml_config['openai-api']['magic_max_waittime_for_gpt_response'])
        except Exception as e:
            self.logger.error(f"Error in yaml_gpt_config(): {e}")

    def yaml_gpt_assistant_config(self, yaml_config):
        self.gpt_assistants_config = yaml_config['gpt_assistants_config']
        self.assistant_response_max_length = yaml_config['openai-api']['assistant_response_max_length']
        self.gpt_assistants_suffix = yaml_config['gpt_assistants_suffix']

    def yaml_gpt_assistants_with_functions_config(self, yaml_config):
        """
        Dynamically loads assistants with their instructions and JSON configurations from the YAML file.

        Args:
            yaml_config (dict): The parsed YAML configuration.

        Returns:
            list: A list of dictionaries containing the name, instructions, and JSON data for each assistant.
        """

        self.gpt_assistants_with_functions_config = []

        # Load the function schemas from the JSON file
        self.function_schemas_path = yaml_config['gpt_assistants_with_functions']['function_call_schema_file_path']
        self.function_schemas = utils.load_json(path_or_dir=self.function_schemas_path)

        gpt_assistants_config = yaml_config.get('gpt_assistants_with_functions', {})
        assistants_dict = gpt_assistants_config.get('assistants', {})

        for name, instructions in assistants_dict.items():
            instructions = instructions.get('instructions')
            function_schema = self.function_schemas[name]
            self.logger.info(f'name: {name}')
            self.logger.info(f'instructions: {instructions}')
            self.logger.info(f'function_schema: {function_schema}')
            
            try:
                assistant_entry = {
                    "name": name,
                    "instructions": instructions,
                    "json_schema": function_schema
                }
                self.gpt_assistants_with_functions_config.append(assistant_entry)

            except Exception as e:
                self.logger.error(f"Error in yaml_gpt_assistants_with_functions_config(): {e}")

    def yaml_gpt_thread_config(self, yaml_config):
        self.gpt_thread_names = yaml_config['gpt_thread_names']

    def yaml_gpt_explain_config(self, yaml_config):
        self.gpt_explain_prompts = yaml_config['gpt_explain_prompts']
        self.explanation_suffix = yaml_config['gpt_explain_prompts']['explanation_suffix']
        self.explanation_starter = yaml_config['gpt_explain_prompts']['explanation_starter']
        self.explanation_progressor = yaml_config['gpt_explain_prompts']['explanation_progressor']
        self.explanation_additional_detail_addition = yaml_config['gpt_explain_prompts']['explanation_additional_detail_addition']
        self.explanation_user_opening_summary_prompt = yaml_config['gpt_explain_prompts']['explanation_user_opening_summary_prompt']
        self.explanation_ender = yaml_config['gpt_explain_prompts']['explanation_ender']

        self.explanation_progression_number = yaml_config['gpt_explain_prompts']['explanation_progression_number']
        self.explanation_max_counter_default = yaml_config['gpt_explain_prompts']['explanation_max_counter_default']
        self.explanation_message_recurrence_seconds = yaml_config['gpt_explain_prompts']['explanation_message_recurrence_seconds']

    def yaml_gpt_voice_config(self, yaml_config):
        self.openai_vars = yaml_config['openai-api']
        self.tts_voice_randomfact = yaml_config['openai-api']['tts_voice_randomfact']
        self.tts_voice_chatforme = yaml_config['openai-api']['tts_voice_chatforme']
        self.tts_voice_story = yaml_config['openai-api']['tts_voice_story']
        self.factcheck_voice = yaml_config['openai-api']['tts_voice_factcheck']
        self.tts_voice_newuser = yaml_config['openai-api']['tts_voice_newuser']
        self.tts_voice_default = yaml_config['openai-api']['tts_voice_default']
        self.tts_voice_vibecheck = yaml_config['openai-api']['tts_voice_vibecheck']
        self.flag_returning_users_service = yaml_config['flag_returning_users_service']

    def yaml_vibecheck_config(self, yaml_config):
        try:
            self.vibechecker_max_interaction_count = yaml_config['vibechecker_max_interaction_count']
            self.formatted_gpt_vibecheck_prompt = yaml_config['formatted_gpt_vibecheck_prompt']
            self.formatted_gpt_viberesult_prompt = yaml_config['formatted_gpt_viberesult_prompt']
            self.newusers_sleep_time = yaml_config['newusers_sleep_time']
            self.newusers_msg_prompt = yaml_config['newusers_msg_prompt']
            self.newusers_faiss_default_query = yaml_config['newusers_faiss_default_query']
            self.returningusers_msg_prompt = yaml_config['returningusers_msg_prompt']
            self.vibechecker_message_wordcount = str(yaml_config['vibechecker_message_wordcount'])
            self.vibechecker_question_session_sleep_time = yaml_config['vibechecker_question_session_sleep_time']
            self.vibechecker_listener_sleep_time = yaml_config['vibechecker_listener_sleep_time']
            self.formatted_gpt_vibecheck_alert = yaml_config['formatted_gpt_vibecheck_alert']
        except Exception as e:
            self.logger.error(f"Error in yaml_vibecheck_config(): {e}")

    def yaml_twitchbot_config(self, yaml_config):
        try:
            self.twitch_bot_gpt_hello_world = yaml_config['twitch-app']['twitch_bot_gpt_hello_world']
            self.twitch_bot_channel_name = yaml_config['twitch-app']['twitch_bot_channel_name']
            self.twitch_bot_username = yaml_config['twitch-app']['twitch_bot_username']
            self.twitch_bot_display_name = yaml_config['twitch-app']['twitch_bot_display_name']
            self.twitch_bot_moderators = yaml_config['twitch-app']['twitch_bot_moderators']
            self.num_bot_responses = yaml_config['chatforme_randomfacts']['num_bot_responses']
            self.twitch_bot_operatorname = yaml_config['twitch-app']['twitch_bot_operatorname']
            self.msg_history_limit = yaml_config['chatbot_config']['msg_history_limit']

        except Exception as e:
            self.logger.error(f"Error in yaml_twitchbot_config(): {e}")

    def yaml_chatforme_config(self, yaml_config):
        try:
            self.chatforme_prompt = yaml_config['chatforme_prompts']['standard']
        except Exception as e:
            self.logger.error(f"Error in yaml_chatforme_config(): {e}")

    def yaml_helloworld_config(self, yaml_config):
        try:
            # GPT Hello World Vars:
            self.gpt_hello_world = self.gpt_hello_world = True if os.getenv('gpt_hello_world') == 'True' else False
            self.hello_assistant_prompt = yaml_config['formatted_gpt_helloworld_prompt']
        except Exception as e:
            self.logger.error(f"Error in yaml_helloworld_config(): {e}")

    def yaml_ouat_config(self, yaml_config):

        def set_story_progression_number(max_counter):
            if max_counter < 5:
                progression_number = max_counter - 2
            else:
                progression_number = int(max_counter * 0.60)
            progression_number = max(1, min(progression_number, max_counter - 3))
            return progression_number
        
        def set_story_climax_number(max_counter, progression_number):
            if max_counter < 5:
                climax_number = max_counter - 1
            else:
                climax_number = int(max_counter * 0.75)
            climax_number = max(progression_number + 1, min(climax_number, max_counter - 2))
            return climax_number

        def set_story_finisher_number(max_counter, climax_number):
            if max_counter < 5:
                finisher_number = max_counter - 1
            else:
                finisher_number = int(max_counter * 0.90)
            finisher_number = max(climax_number + 1, min(finisher_number, max_counter - 1))
            return finisher_number
    
        try:
            # News Article Feed/Prompts
            self.newsarticle_rss_feed = yaml_config['ouat_storyteller']['newsarticle_rss_feed']
            self.story_article_bullet_list_summary_prompt = yaml_config['gpt_thread_prompts']['story_article_bullet_list_summary_prompt'] 
            self.story_user_opening_scene_summary_prompt = yaml_config['gpt_thread_prompts']['story_user_opening_scene_summary_prompt']

            # GPT Thread Prompts
            self.storyteller_storysuffix_prompt = yaml_config['gpt_thread_prompts']['story_suffix']
            self.storyteller_storystarter_prompt = yaml_config['gpt_thread_prompts']['story_starter']
            self.storyteller_storyprogressor_prompt = yaml_config['gpt_thread_prompts']['story_progressor']
            self.storyteller_storyfinisher_prompt = yaml_config['gpt_thread_prompts']['story_finisher']
            self.storyteller_storyclimax_prompt = yaml_config['gpt_thread_prompts']['story_climaxer']
            self.storyteller_storyender_prompt = yaml_config['gpt_thread_prompts']['story_ender']
            self.ouat_prompt_addtostory_prefix = yaml_config['gpt_thread_prompts']['story_addtostory_prefix']
            self.aboutme_prompt = yaml_config['gpt_thread_prompts']['aboutme_prompt']

            # OUAT Progression flow / Config
            self.ouat_message_recurrence_seconds = yaml_config['ouat_storyteller']['ouat_message_recurrence_seconds']
            self.ouat_story_max_counter_default = yaml_config['ouat_storyteller']['ouat_story_max_counter_default']
            self.ouat_story_progression_number = set_story_progression_number(self.ouat_story_max_counter_default)
            self.ouat_story_climax_number = set_story_climax_number(self.ouat_story_max_counter_default, self.ouat_story_progression_number)
            self.ouat_story_finisher_number = set_story_finisher_number(self.ouat_story_max_counter_default, self.ouat_story_climax_number)

            # GPT Writing Style/Theme/Tone Paramaters
            self.writing_tone = yaml_config.get('ouat-writing-parameters', {}).get('writing_tone', 'no specified writing tone')
            self.writing_style = yaml_config.get('ouat-writing-parameters', {}).get('writing_style', 'no specified writing tone')
            self.writing_theme = yaml_config.get('ouat-writing-parameters', {}).get('writing_theme', 'no specified writing tone')
        except Exception as e:
            self.logger.error(f"Error in yaml_ouat_config(): {e}")

    def yaml_depinjector_config(self, yaml_config):
        try:
            self.tts_data_folder = yaml_config['openai-api']['tts_data_folder']
            self.tts_file_name = yaml_config['openai-api']['tts_file_name']
            self.tts_voices = yaml_config['openai-api']['tts_voices']
            self.tts_volume = yaml_config['openai-api']['tts_volume']
        except Exception as e:
            self.logger.error(f"Error in yaml_depinjector_config(): {e}")

    def yaml_randomfact_json(self, yaml_config):
        try:
            self.randomfact_sleeptime = yaml_config['chatforme_randomfacts']['randomfact_sleeptime']
            self.randomfact_selected_game = os.getenv('selected_game')
                            
            # Set random fact prompt and response based on selected game
            self.logger.info(f"randomfact_selected_game: {self.randomfact_selected_game}")
            if self.randomfact_selected_game == 'no_game_selected':
                selected_type = 'standard'
            elif self.randomfact_selected_game != 'no_game_selected' and self.randomfact_selected_game is not None:
                selected_type = 'game'
            elif self.randomfact_selected_game == None:
                selected_type = 'standard'
            else:
                self.logger.error("randomfact_selected_game is None and was set to 'standard'")
                selected_type = 'standard'
            self.logger.info(f"Selected_type is {selected_type} and randomfact_selected_game is {self.randomfact_selected_game}")

            self.randomfact_prompt = yaml_config['chatforme_randomfacts']['randomfact_types'][selected_type]['randomfact_prompt']
            self.randomfact_response = yaml_config['chatforme_randomfacts']['randomfact_types'][selected_type]['randomfact_response']

            # Get random fact topics and areas json file paths
            self.randomfact_topics_json_filepath = yaml_config['chatforme_randomfacts']['randomfact_types'][selected_type]['topics_injection_file_path']
            self.randomfact_topics = utils.load_json(path_or_dir=self.randomfact_topics_json_filepath)

            self.randomfact_areas_json_filepath = yaml_config['chatforme_randomfacts']['randomfact_types'][selected_type]['areas_injection_file_path']
            self.randomfact_areas = utils.load_json(path_or_dir=self.randomfact_areas_json_filepath)

        except Exception as e:
            self.logger.error(f"Error in yaml_randomfact_json(): {e}")

    def yaml_factchecker_config(self, yaml_config):
        try:
            self.factchecker_prompts = yaml_config['chatforme_factcheck']['chatforme_factcheck_prompts']
        except Exception as e:
            self.logger.error(f"Error in yaml_factchecker_config(): {e}")

    def update_spellcheck_config(self, yaml_config):
        self.command_spellcheck_terms_filepath = yaml_config['spellcheck_commands_filename']
        self.command_spellcheck_terms = utils.load_json(path_or_dir=self.command_spellcheck_terms_filepath)

    def update_config_from_yaml(self, yaml_config):
        try:
            # Update instance variables with YAML configurations
            self.keys_env_filename = yaml_config['keys_env_filename']
            self.env_filename = yaml_config['env_filename']
            self.keys_env_dirpath = yaml_config['keys_env_dirpath']
            self.env_dirpath = yaml_config['env_dirpath']

            self.app_config_dirpath = yaml_config['app_config_dirpath']
            
            self.shorten_response_length_prompt = yaml_config['gpt_thread_prompts']['shorten_response_length']

            self.google_application_credentials_file = yaml_config['google_service_account_credentials_file']
            self.talkzillaai_userdata_table_id = yaml_config['talkzillaai_userdata_table_id']
            self.talkzillaai_usertransactions_table_id = yaml_config['talkzillaai_usertransactions_table_id']
            
            self.twitch_bot_redirect_path = yaml_config['twitch-app']['twitch_bot_redirect_path']
            self.twitch_bot_scope = yaml_config['twitch-app']['twitch_bot_scope']

            self.gpt_model = yaml_config.get('openai-api',{}).get('assistant_model', 'gpt-3.5-turbo') 
            self.gpt_model_davinci = yaml_config.get('openai-api',{}).get('assistant_model_davinci', 'gpt-3.05-turbo') 

            self.tts_model = yaml_config.get('openai-api', {}).get('tts_model','tts-1')
        except Exception as e:
            self.logger.error(f"Error in update_config_from_yaml(): {e}")

    def create_logger(self):
        self.logger = create_logger(
            logger_name='logger_ConfigManagerClass', 
            debug_level=runtime_logger_level,
            stream_logs=True,
            encoding='UTF-8'
            )

if __name__ == "__main__":

    #yaml_filepath = r'C:\_repos\chatzilla_ai_prod\chatzilla_ai\config\bot_user_configs\chatzilla_ai_ehitch.yaml'
    yaml_filepath = r'C:\_repos\chatzilla_ai_dev\chatzilla_ai\config\bot_user_configs\chatzilla_ai_ehitch.yaml'    
    #yaml_filepath = r'C:\_repos\chatzilla_ai\config\bot_user_configs\chatzilla_ai_ehitch.yaml'
    print(f"yaml_filepath_type: {type(yaml_filepath)}")

    ConfigManager.initialize(yaml_filepath=yaml_filepath)
    config = ConfigManager.get_instance()
    
    # Log the configuration
    config._log_config()