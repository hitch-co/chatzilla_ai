import os

class ArgsConfigManager:
    _instance = None

    #singleton
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ArgsConfigManager, cls).__new__(cls)
            cls._instance.initialize_config()
        return cls._instance

    def initialize_config(self):
        self.input_port_number = int(os.getenv("input_port_number", 3000))