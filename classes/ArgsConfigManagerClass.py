import os

class ArgsConfigManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ArgsConfigManager, cls).__new__(cls)
            cls._instance.initialize_config()
        return cls._instance

    def initialize_config(self):
        # Load parameters from argparse here, or directly from the environment variables
        self.include_ouat = os.getenv("include_ouat", "yes")
        self.include_automsg = os.getenv("include_automsg", "no")
        self.include_sound = os.getenv("include_sound", "no")
        self.prompt_list_ouat = os.getenv("prompt_list_ouat", "newsarticle_dynamic")
        self.prompt_list_automsg = os.getenv("prompt_list_automsg", "videogames")
        self.prompt_list_chatforme = os.getenv("prompt_list_chatforme", "standard")
        self.input_port_number = int(os.getenv("input_port_number", 3000))