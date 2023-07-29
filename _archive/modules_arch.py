#modules.py

# Import modules at the beginning of the file
import os
import yaml
import dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

#Load parameters
def load_yaml(yaml_filename='config.yaml', yaml_dirname=''):
    """Load parameters from a yaml file.

    Args:
    yaml_filename (str): Path to the yaml file.

    Returns:
    dict: Dictionary containing parameters loaded from yaml file.
    """

    # use the argument instead of hardcoding the path
    yaml_filepath = os.path.join(os.getcwd(), yaml_dirname, yaml_filename)

    with open(yaml_filename, 'r') as file:
        yaml_config = yaml.safe_load(file)
        logging.info('YAML contents loaded successfully.')
        return yaml_config

def chatforme():
    """A function to demonstrate logging."""
    logging.info('Chatted for you')

def load_env(env_filename='config.env', env_dirname='config'):
    """Load environment variables from a .env file.

    Args:
    env_filepath (str): Path to the .env file.
    """

    # use the argument instead of hardcoding the path
    env_filepath = os.path.join(os.getcwd(), env_dirname, env_filename)

    if dotenv.load_dotenv(env_filepath):
        logging.info('Environment file loaded successfully.')
    else:
        logging.error('Failed to load environment file.')
