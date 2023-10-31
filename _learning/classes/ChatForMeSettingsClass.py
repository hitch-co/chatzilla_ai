import yaml
import logging
import os

class ChatForMeSettings:    
    env_filename = ''
    env_dirname = ''
    server_guild_id = -1
    server_channel_id = -1
    discord_games_countdown_username = ''
    discord_games_countdown_default_minutes = -1
    DISCORD_BOT_PLAY_GAMES_IN_BOT_TOKEN = ''
    msg_history_limit = ''
    num_bot_responses = ''
    automated_message_seconds = ''
    automated_message_wordcount = ''
    formatted_gpt_automsg_prompt_prefix = ''
    formatted_gpt_automsg_prompt_suffix  = ''
    formatted_gpt_chatforme_prompt_prefix = ''
    formatted_gpt_chatforme_prompt_suffix = ''
    automsg_prompt_lists = ''
    
    #Load parameters from config.yaml
    def load_yaml_raw(self, yaml_filename='config.yaml', yaml_dirname='', is_testing=False):

        """
        Load parameters from a YAML file.

        Parameters:
        - yaml_filename (str): Name of the YAML file to be loaded.
        - yaml_dirname (str): Directory path containing the YAML file.
        - is_testing (bool): Flag to indicate if the function is being run for testing purposes.

        Returns:
        dict: Dictionary containing parameters loaded from the YAML file.
        """
        

        #is_testing = True
        if is_testing == True:
            yaml_dirname='C:\_repos\chatforme_bots\config'
            yaml_filename='config.yaml'

        # use the argument instead of hardcoding the path
        yaml_filepath = os.path.join(os.getcwd(), yaml_dirname, yaml_filename)
        with open(yaml_filepath, 'r') as file:
            yaml_config = yaml.safe_load(file)
            logging.info('LOG: YAML contents loaded successfully.')
            
        return yaml_config

    def has_config_value(self, target_data, field_name):
        if field_name in target_data:
            return True
        else:
            return False
    
    def get_default_value(self, target_data, field_name, default_value):
        if self.has_config_value(target_data, field_name):
            return target_data[field_name]
        else:
            return default_value        

    def load_yaml(self, yaml_filename='config.yaml', yaml_dirname='', is_testing=False):
        raw_yaml_data = self.load_yaml_raw(yaml_filename, yaml_dirname, is_testing)
        self.env_filename = self.get_default_value(raw_yaml_data, 'env_filename', '')
        self.env_dirname = self.get_default_value(raw_yaml_data, 'env_dirname', '')
        self.server_guild_id = int(self.get_default_value(raw_yaml_data, 'server_guild_id', '-1'))
        self.server_channel_id = int(self.get_default_value(raw_yaml_data, 'server_channel_id', -1))
        self.discord_games_countdown_username = self.get_default_value(raw_yaml_data, 'discord_games_countdown_username', '')
        self.discord_games_countdown_default_minutes = int(self.get_default_value(raw_yaml_data, 'discord_games_countdown_default_minutes', '-1'))       
        self.DISCORD_BOT_PLAY_GAMES_IN_BOT_TOKEN = self.get_default_value(raw_yaml_data, 'DISCORD_BOT_PLAY_GAMES_IN_BOT_TOKEN', '')
        
        self.msg_history_limit = self.get_default_value(raw_yaml_data, 'msg_history_limit', '')
        self.num_bot_responses = self.get_default_value(raw_yaml_data, 'num_bot_responses', '')
        self.automated_message_seconds = self.get_default_value( raw_yaml_data, 'automated_message_seconds', '')
        self.automated_message_wordcount = str(self.get_default_value(raw_yaml_data, 'automated_message_wordcount',''))
        self.formatted_gpt_automsg_prompt_prefix = str(self.get_default_value(raw_yaml_data, 'formatted_gpt_automsg_prompt_prefix', ''))
        self.formatted_gpt_automsg_prompt_suffix = str(self.get_default_value(raw_yaml_data, 'formatted_gpt_automsg_prompt_suffix', ''))
        self.formatted_gpt_chatforme_prompt_prefix = str(self.get_default_value(raw_yaml_data, 'formatted_gpt_chatforme_prompt_prefix', ''))
        self.formatted_gpt_chatforme_prompt_suffix = str(self.get_default_value(raw_yaml_data, 'formatted_gpt_chatforme_prompt_suffix', ''))
        self.automsg_prompt_lists = self.get_default_value(raw_yaml_data, 'automsg_prompt_lists', '')
    
