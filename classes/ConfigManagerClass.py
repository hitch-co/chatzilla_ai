import os
import yaml
import dotenv

from my_modules.my_logging import create_logger

runtime_logger_level = 'DEBUG'

class ConfigManager:
    _instance = None

    def __new__(cls, yaml_filepath=None, yaml_filename=None):
        if cls._instance is None:
            cls._instance = object.__new__(cls)
            cls._instance.init_attributes()
            cls._instance.initialize_config(yaml_filepath, yaml_filename)
        return cls._instance

    def init_attributes(self):
        # Create logger
        self.logger = create_logger(
            dirname='log', 
            logger_name='logger_ConfigManagerClass', 
            debug_level=runtime_logger_level,
            mode='w',
            stream_logs=True,
            encoding='UTF-8'
            )
        
        # Initialize all instance attributes
        self.include_ouat = None
        self.include_automsg = None
        self.include_sound = None
        self.input_port_number = None
        self.prompt_list_ouat = None
        self.prompt_list_automsg = None
        self.prompt_list_chatforme = None
        self.env_file_directory = None
        self.env_file_name = None

    def initialize_config(self, yaml_filepath, yaml_filename):
        yaml_full_path = os.path.join(yaml_filepath, yaml_filename)
        self.load_yaml_config(yaml_full_path)
        self.set_env_variables()

    def load_yaml_config(self, yaml_full_path):
        try:
            with open(yaml_full_path, 'r') as file:
                yaml_config = yaml.safe_load(file)
                self.update_config_from_yaml(yaml_config)
        except FileNotFoundError:
            self.logger.error(f"YAML configuration file not found at {yaml_full_path}")
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML configuration: {e}")

    def set_env_variables(self):
        if self.env_file_directory and self.env_file_name:
            env_path = os.path.join(self.env_file_directory, self.env_file_name)
            if os.path.exists(env_path):
                dotenv.load_dotenv(env_path)
                self.update_config_from_env()
            else:
                self.logger.error(f".env file not found at {env_path}")

    def update_config_from_env(self):
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

        # Load runtime parameters from .bat
        self.include_ouat = os.getenv("include_ouat", "yes")
        self.include_automsg = os.getenv("include_automsg", "no")
        self.include_sound = os.getenv("include_sound", "yes")
        self.prompt_list_name_ouat = os.getenv("prompt_list_ouat", "newsarticle_dynamic")
        self.prompt_list_name_automsg = os.getenv("prompt_list_automsg", "videogames")
        self.prompt_list_chatforme = os.getenv("prompt_list_chatforme", "standard")
        self.prompt_list_name_botthot = os.getenv("prompt_list_botthot", "standard")
        self.input_port_number = int(os.getenv("input_port_number", 3000))        

    def update_config_from_yaml(self, yaml_config):
        # Update instance variables with YAML configurations
        self.env_file_directory = yaml_config.get('env_dirname')
        self.env_file_name = yaml_config.get('env_filename')

        # twitch
        # yaml_config.get('twitch-ouat', {}).get('twitch-get-chatters-endpoint','speech.mp3')
        # self.yaml_data['twitch-ouat']['twitch-get-chatters-endpoint']

        # twitch-app/bots
        #yaml_config.get('twitch-app', {}).get('twitch_bot_username','yaml_val_not_found')
        self.bots_automsg = yaml_config.get('twitch-bots', {}).get('automsg','yaml_val_not_found')
        self.bots_chatforme = yaml_config.get('twitch-bots', {}).get('chatforme','yaml_val_not_found')
        self.bots_ouat = yaml_config.get('twitch-bots', {}).get('onceuponatime','yaml_val_not_found')

        # bots_all - Iterate over each key and extend self.bots_all
        self.bots_all = []
        keys = ['automsg', 'chatforme', 'onceuponatime']
        for key in keys:
            bots = yaml_config.get('twitch-bots', {}).get(key, [])
            if bots != 'yaml_val_not_found':
                self.bots_all.extend(bots)
        self.bots_all = list(set(self.bots_all))
        self.logger.info("these are the self.bots_all")
        self.logger.info(self.bots_all)

        # BQ Table IDs
        self.userdata_table_id = yaml_config.get('twitch-ouat',{}).get('talkzillaai_userdata_table_id')
        self.usertransactions_table_id = yaml_config.get('twitch-ouat',{}).get('talkzillaai_usertransactions_table_id')
        
        # openai t2s, models, prompt
        self.gpt_model = yaml_config.get('openai-api',{}).get('assistant_model', 'gpt-3.5-turbo') 
        self.tts_model = yaml_config.get('openai-api', {}).get('tts_model','tts-1')
        self.tts_voice = yaml_config.get('openai-api', {}).get('tts_voice','shimmer')
        self.tts_data_folder = yaml_config.get('openai-api', {}).get('tts_data_folder','data\\tts')
        self.tts_file_name = yaml_config.get('openai-api', {}).get('tts_file_name','speech.mp3')
        self.gpt_shorten_message_prompt = yaml_config.get('ouat_prompts',{}).get('shorten_response_length_prompt', 'shorten this message to 20 characters')

        # Twitch bot details
        self.twitch_bot_channel_name = yaml_config.get('twitch-app', {}).get('twitch_bot_channel_name')
        self.twitch_bot_username = yaml_config.get('twitch-app',{}).get('twitch_bot_username')

        ###################################################################
        # News Article Feed/Prompts
        self.newsarticle_rss_feed = yaml_config.get('twitch-ouat', {}).get('newsarticle_rss_feed')
        self.ouat_news_article_summary_prompt = yaml_config.get('ouat_prompts', {}).get('ouat_news_article_summary_prompt')

        # Generic config items
        self.num_bot_responses = yaml_config.get('num_bot_responses')

        # Load settings and configurations from a YAML file
        self.chatforme_message_wordcount = str(yaml_config.get('chatforme_message_wordcount'))
        self.formatted_gpt_chatforme_prompt_prefix = str(yaml_config.get('formatted_gpt_chatforme_prompt_prefix'))
        self.formatted_gpt_chatforme_prompt_suffix = str(yaml_config.get('formatted_gpt_chatforme_prompt_suffix'))
        self.formatted_gpt_chatforme_prompts = yaml_config.get('formatted_gpt_chatforme_prompts')
        self.formatted_gpt_botthot_prompts = yaml_config.get('formatted_gpt_botthot_prompts')

        # Prompts 
        self.ouat_prompt_addtostory_prefix = yaml_config.get('ouat_prompts', {}).get('ouat_prompt_addtostory_prefix')

        # USED IN OPENAI GPT ASSISTANTS WORKFLOW
        ########################################################################
        # GPT Assistant prompts:
        # self.article_summarizer_assistant_prompt = yaml_config.get('gpt_assistant_prompts', {}).get('article_summarizer')
        # self.storyteller_assistant_prompt = yaml_config.get('gpt_assistant_prompts', {}).get('storyteller')
        # self.ouat_assistant_prompt = yaml_config.get('gpt_assistant_prompts', {}).get('article_summarizer')
        # self.chatforme_assistant_prompt = yaml_config.get('gpt_assistant_prompts', {}).get('chatforme')
        # self.botthot_assistant_prompt = yaml_config.get('gpt_assistant_prompts', {}).get('botthot')

        # GPT Thread Prompts
        self.storyteller_storystarter_prompt = yaml_config.get('gpt_thread_prompts', {}).get('story_starter')
        self.storyteller_storyprogressor_prompt = yaml_config.get('gpt_thread_prompts', {}).get('story_progressor')
        self.storyteller_storyfinisher_prompt = yaml_config.get('gpt_thread_prompts', {}).get('story_finisher')
        self.storyteller_storyender_prompt = yaml_config.get('gpt_thread_prompts', {}).get('story_ender')

        # GPT Writing Style/Theme/Tone Paramaters
        self.writing_tone = yaml_config.get('ouat-writing-parameters', {}).get('writing_tone', 'no specified writing tone')
        self.writing_style = yaml_config.get('ouat-writing-parameters', {}).get('writing_style', 'no specified writing tone')
        self.writing_theme = yaml_config.get('ouat-writing-parameters', {}).get('theme', 'no specified writing tone')


        ########################################################################

        # USED IN OPENAI CHAT COMPLETION ENDPOINT
        ########################################################################
        # OUAT Progression flow / Config
        self.ouat_message_recurrence_seconds = yaml_config.get('ouat_message_recurrence_seconds')
        self.ouat_story_progression_number = yaml_config.get('ouat_story_progression_number')
        self.ouat_story_max_counter = yaml_config.get('ouat_story_max_counter')
        self.ouat_wordcount = yaml_config.get('ouat_wordcount')
        ########################################################################

def main():
    config_manager = ConfigManager(yaml_filepath='.\config', yaml_filename='config.yaml')
    print(config_manager.bots_ouat)
    
if __name__ == "__main__":
    main()
