import os
import yaml
import dotenv

from my_modules.my_logging import create_logger

runtime_logger_level = 'DEBUG'

class ConfigManager:
    _instance = None

    @classmethod
    def initialize(cls, yaml_filepath):
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
        try:
            self.load_yaml_config(yaml_full_path=yaml_filepath)
        except Exception as e:
            self.logger.error(f"Error, exception in load_yaml_config(): {e}", exc_info=True)

        try:
            self.set_env_variables()
        except Exception as e:
            self.logger.error(f"Error, exception in set_env_variables(): {e}", exc_info=True)

    def load_yaml_config(self, yaml_full_path):
        try:
            with open(yaml_full_path, 'r') as file:
                self.logger.debug("loading individual configs...")
                yaml_config = yaml.safe_load(file)
                
                self.yaml_twitchbot_config(yaml_config)
                
                self.yaml_depinjector_config(yaml_config)
                self.update_config_from_yaml(yaml_config)

                self.yaml_gcp_config(yaml_config)
                
                self.yaml_botears_config(yaml_config)
                self.yaml_gpt_config(yaml_config)
                self.yaml_chatforme_config(yaml_config)
                self.yaml_ouat_config(yaml_config)
                self.yaml_vibecheck_config(yaml_config)

                self.yaml_helloworld_config(yaml_config)
                self.yaml_todo_config(yaml_config)
                
        except FileNotFoundError:
            self.logger.error(f"YAML configuration file not found at {yaml_full_path}")
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML configuration: {e}")
        except Exception as e:
            self.logger.error(f"Error in load_yaml_config(): {e}")

    def set_env_variables(self):
        if self.env_file_directory and self.env_file_name:
            env_path = os.path.join(self.env_file_directory, self.env_file_name)
            if os.path.exists(env_path):
                dotenv.load_dotenv(env_path)
                self.update_config_from_env()
                #TODO: self.other_update_from_env()
            else:
                self.logger.error(f".env file not found at {env_path}")

    def update_config_from_env(self):
        try:
            self.openai_api_key = os.getenv('OPENAI_API_KEY')
            
            # Load and set runtime parameters from environment variables set in .bat
            self.include_ouat = os.getenv("include_ouat", "yes")
            self.include_automsg = os.getenv("include_automsg", "no")
            self.include_sound = os.getenv("include_sound", "no")
            self.input_port_number = os.getenv("input_port_number", 3000)
            self.prompt_list_ouat = os.getenv("prompt_list_ouat", "newsarticle_dynamic")
            self.prompt_list_automsg = os.getenv("prompt_list_automsg", "videogames")
            self.prompt_list_chatforme = os.getenv("prompt_list_chatforme", "standard")

            # Load twitch bot and mod identifiers
            self.twitch_broadcaster_author_id = os.getenv('TWITCH_BROADCASTER_AUTHOR_ID')
            self.twitch_bot_moderator_id = os.getenv('TWITCH_BOT_MODERATOR_ID')
            self.twitch_bot_client_id = os.getenv('TWITCH_BOT_CLIENT_ID')
            self.twitch_bot_client_secret = os.getenv('TWITCH_BOT_CLIENT_SECRET')

            # Load runtime parameters from .bat
            self.include_ouat = os.getenv("include_ouat", "yes")
            self.include_automsg = os.getenv("include_automsg", "no")
            self.include_sound = os.getenv("include_sound", "yes")
            self.prompt_list_name_ouat = os.getenv("prompt_list_ouat", "newsarticle_dynamic")
            self.prompt_list_name_automsg = os.getenv("prompt_list_automsg", "videogames")
            self.prompt_list_chatforme = os.getenv("prompt_list_chatforme", "standard")
            self.prompt_list_name_botthot = os.getenv("prompt_list_botthot", "standard")
            self.input_port_number = int(os.getenv("input_port_number", 3000))
                    
        except Exception as e:
            self.logger.error(f"Error in update_config_from_env(): {e}")

    def yaml_gcp_config(self, yaml_config):
        try:
            self.keys_dirpath = yaml_config['keys_dirpath']
            self.google_service_account_credentials_file = yaml_config['twitch-ouat']['google_service_account_credentials_file']

            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join(
                self.keys_dirpath, 
                self.google_service_account_credentials_file
                )
        except Exception as e:
            self.logger.error(f"Error in yaml_gcp_config(): {e}\nTraceback:", exc_info=True)

    def yaml_botears_config(self, yaml_config):
        try:
            self.botears_devices_json_filepath = yaml_config['botears_devices_json_filepath']
            self.botears_prompt = yaml_config['botears_prompt']
            self.botears_device_mic = yaml_config['botears_device_mic']
            self.botears_audio_n_seconds = yaml_config['botears_audio_n_seconds']
            self.botears_audio_path = yaml_config['botears_audio_path']
            self.botears_audio_filename = yaml_config['botears_audio_filename']
            self.botears_save_last_n_seconds = yaml_config['botears_save_last_n_seconds']

        except Exception as e:
            self.logger.error(f"Error in yaml_botears_config(): {e}")

    def yaml_gpt_config(self, yaml_config):
        try:
            self.wordcount_short = str(yaml_config['wordcounts']['short'])
            self.wordcount_medium = str(yaml_config['wordcounts']['medium'])
            self.wordcount_long = str(yaml_config['wordcounts']['long'])
        except Exception as e:
            self.logger.error(f"Error in yaml_gpt_config(): {e}")

    def yaml_vibecheck_config(self, yaml_config):
        try:
            self.vibechecker_max_interaction_count = yaml_config['vibechecker_max_interaction_count']
            self.formatted_gpt_vibecheck_prompt = yaml_config['formatted_gpt_vibecheck_prompt']
            self.formatted_gpt_viberesult_prompt = yaml_config['formatted_gpt_viberesult_prompt']
            self.newusers_sleep_time = yaml_config['newusers_sleep_time']
            self.newusers_nonewusers_prompt = yaml_config['newusers_nonewusers_prompt']
            self.vibechecker_message_wordcount = str(yaml_config['vibechecker_message_wordcount'])
            self.vibechecker_question_session_sleep_time = yaml_config['vibechecker_question_session_sleep_time']
            self.vibechecker_listener_sleep_time = yaml_config['vibechecker_listener_sleep_time']
            self.formatted_gpt_vibecheck_alert = yaml_config['formatted_gpt_vibecheck_alert']
        except Exception as e:
            self.logger.error(f"Error in yaml_vibecheck_config(): {e}")

    def yaml_twitchbot_config(self, yaml_config):
        try:
            self.twitch_bot_channel_name = yaml_config['twitch-app']['twitch_bot_channel_name']
            self.twitch_bot_username = yaml_config['twitch-app']['twitch_bot_username']
            self.twitch_bot_display_name = yaml_config['twitch-app']['twitch_bot_display_name']
            self.num_bot_responses = yaml_config['num_bot_responses']
            self.twitch_bot_operatorname = yaml_config['twitch-app']['twitch_bot_operatorname']
        except Exception as e:
            self.logger.error(f"Error in yaml_twitchbot_config(): {e}")

    def yaml_chatforme_config(self, yaml_config):
        try:
            self.chatforme_prompt = yaml_config['chatforme_prompts']['standard']
            self.chatforme_prompt_prefix = str(yaml_config['chatforme_prompts']['chatforme_prompt_prefix'])
            self.chatforme_prompt_suffix = str(yaml_config['chatforme_prompts']['chatforme_prompt_suffix'])
        except Exception as e:
            self.logger.error(f"Error in yaml_chatforme_config(): {e}")

    def yaml_helloworld_config(self, yaml_config):
        try:
            # GPT Hello World Vars:
            self.gpt_hello_world = self.gpt_hello_world = True if os.getenv('gpt_hello_world') == 'True' else False
            self.hello_assistant_prompt = yaml_config['formatted_gpt_helloworld_prompt']
            self.helloworld_message_wordcount = yaml_config['helloworld_message_wordcount']
        except Exception as e:
            self.logger.error(f"Error in yaml_helloworld_config(): {e}")

    def yaml_todo_config(self, yaml_config):
        try:
            # GPT todo command prompts:
            self.gpt_todo_prompt = yaml_config['gpt_todo_prompt']
            self.gpt_todo_prompt_prefix = yaml_config['gpt_todo_prompt_prefix']
            self.gpt_todo_prompt_suffix = yaml_config['gpt_todo_prompt_suffix']
        except Exception as e:
            self.logger.error(f"Error in yaml_todo_config(): {e}")

    def yaml_ouat_config(self, yaml_config):
        try:
            # News Article Feed/Prompts
            self.newsarticle_rss_feed = yaml_config['twitch-ouat']['newsarticle_rss_feed']
            self.story_article_bullet_list_summary_prompt = yaml_config['gpt_thread_prompts']['story_article_bullet_list_summary_prompt'] 
            self.story_user_bullet_list_summary_prompt = yaml_config['gpt_thread_prompts']['story_user_bullet_list_summary_prompt']

            # GPT Thread Prompts
            self.storyteller_storysuffix_prompt = yaml_config['gpt_thread_prompts']['story_suffix']
            self.storyteller_storystarter_prompt = yaml_config['gpt_thread_prompts']['story_starter']
            self.storyteller_storyprogressor_prompt = yaml_config['gpt_thread_prompts']['story_progressor']
            self.storyteller_storyfinisher_prompt = yaml_config['gpt_thread_prompts']['story_finisher']
            self.storyteller_storyender_prompt = yaml_config['gpt_thread_prompts']['story_ender']
            self.ouat_prompt_addtostory_prefix = yaml_config['gpt_thread_prompts']['story_addtostory_prefix']

            # OUAT Progression flow / Config
            self.ouat_message_recurrence_seconds = yaml_config['ouat_message_recurrence_seconds']
            self.ouat_story_progression_number = yaml_config['ouat_story_progression_number']
            self.ouat_story_max_counter = yaml_config['ouat_story_max_counter']

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

    def update_config_from_yaml(self, yaml_config):
        try:
            # Update instance variables with YAML configurations
            self.env_file_directory = yaml_config['env_dirname']
            self.env_file_name = yaml_config['env_filename']
            self.app_config_dirpath = yaml_config['app_config_dirpath']
            
            self.twitch_get_chatters_endpoint = yaml_config['twitch-ouat']['twitch_get_chatters_endpoint']
            self.shorten_response_length = yaml_config['gpt_thread_options']['shorten_response_length']

            self.config_dirpath = yaml_config['config_dirpath']
            self.keys_dirpath = yaml_config['keys_dirpath']
            self.command_spellcheck_terms_filename = yaml_config['command_spellcheck_terms_filename']
            
            self.google_application_credentials_file = yaml_config['twitch-ouat']['google_service_account_credentials_file']
            self.talkzillaai_userdata_table_id = yaml_config['twitch-ouat']['talkzillaai_userdata_table_id']
            self.talkzillaai_usertransactions_table_id = yaml_config['twitch-ouat']['talkzillaai_usertransactions_table_id']
            
            self.twitch_bot_redirect_path = yaml_config['twitch-app']['twitch_bot_redirect_path']
            self.twitch_bot_scope = yaml_config['twitch-app']['twitch_bot_scope']

            # openai t2s, models, prompt
            self.gpt_model = yaml_config.get('openai-api',{}).get('assistant_model', 'gpt-3.5-turbo') 
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

def main(yaml_filepath):
    ConfigManager.initialize(yaml_filepath)
    config = ConfigManager.get_instance()
    return config

if __name__ == "__main__":
    yaml_filepath = r'C:\Users\Admin\OneDrive\Desktop\_work\__repos (unpublished)\_____CONFIG\chatzilla_ai\config\config.yaml'
    print(f"yaml_filepath_type: {type(yaml_filepath)}")

    config = main(yaml_filepath)

    print(config.tts_data_folder)
    print(config.tts_file_name)