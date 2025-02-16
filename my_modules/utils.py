import json
import os
import re
from datetime import datetime

from my_modules.my_logging import create_logger

logger = create_logger(
    dirname='log', 
    logger_name='logger_utils',
    debug_level='DEBUG',
    mode='w',
    stream_logs=False
    )

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_config_instance():
    from classes.ConfigManagerClass import ConfigManager
    return ConfigManager.get_instance()

def load_json(path_or_dir: str, file_name: str = None) -> dict:
    """
    Loads a JSON file either from a single full path or by joining a directory with a file name.
    Interprets relative paths as being relative to REPO_ROOT.
    """
    if file_name:
        file_path = os.path.join(path_or_dir, file_name)
    else:
        file_path = path_or_dir

    # If it's a relative path, make it absolute relative to REPO_ROOT.
    if not os.path.isabs(file_path):
        file_path = os.path.join(REPO_ROOT, file_path)

    if not os.path.exists(file_path):
        logger.error(f"File {file_path} does not exist.")
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.debug(f"Successfully loaded JSON from {file_path}")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON in {file_path}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error loading JSON from {file_path}: {e}")

    return None

def show_json(obj):
    # Assuming obj.model_dump_json() returns a JSON string
    json_data = json.loads(obj.model_dump_json())
    return json.dumps(json_data, indent=4)

async def find_unique_to_new_list(
        source_list, 
        new_list
        ) -> list:
    set1 = set(source_list)
    set2 = set(new_list)
    unique_strings = set2 - set1
    unique_list = list(unique_strings)

    # print("_find_unique_to_new_list inputs/output:")
    # print(f"source_list: {source_list}")
    # print(f"new_list: {new_list}")
    # print(f"unique_list: {unique_list}")
    return unique_list

async def find_unique_to_new_dict(
        source_dict, 
        new_dict
        ) -> list:
    # Assuming the first dictionary in list2 represents the key structure
    keys = new_dict[0].keys()

    # Convert list1 and list2 to sets of a primary key (assuming the first key is unique)
    primary_key = next(iter(keys))
    set1 = {user[primary_key] for user in source_dict}
    set2 = {user[primary_key] for user in new_dict}

    # Find the difference - users in list2 but not in list1
    unique_user_ids = set2 - set1

    # Convert the unique user_ids back to dictionary format
    unique_users = [user for user in new_dict if user[primary_key] in unique_user_ids]
    # print("This is the list of unique_users:")
    # print(unique_users)
    
    return unique_users
    
def shutdown_server():
    from flask import request 
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

def get_datetime_formats():
    """
    Generate a dictionary containing formatted datetime strings for SQL and filenames.

    Returns:
    dict: A dictionary with the following keys and values:
        - 'sql_format': A string representing the current date and time formatted as 'YYYY-MM-DD HH:MM:SS'.
        - 'filename_format': A string representing the current date and time formatted as 'YYYY-MM-DD_HH-MM-SS'.
    """
    now = datetime.now()
    sql_format = now.strftime('%Y-%m-%d %H:%M:%S')
    filename_format = now.strftime('%Y-%m-%d_%H-%M-%S')
    dates_dict = {"sql_format":sql_format, "filename_format":filename_format}
    return dates_dict

def populate_placeholders(logger, prompt_template, replacements: dict = None):
    """
    Replaces placeholders in the prompt template with the corresponding values from the replacements dictionary.

    Parameters:
    logger (Logger): The logger object to use for debugging output.
    prompt_template (str): The template text containing placeholders for replacement.
    replacements (dict, optional): A dictionary containing the replacement values. Defaults to None.

    Returns:
    str: The prompt text with placeholders replaced by actual values.
    """
    yaml_data = load_config_instance()

    default_replacements = {
        "wordcount_veryshort": yaml_data.wordcount_veryshort,
        "wordcount_short": yaml_data.wordcount_short,
        "wordcount_medium": yaml_data.wordcount_medium,
        "wordcount_long": yaml_data.wordcount_long
    }

    if replacements:
        try:
            replacements.update(default_replacements)
        except Exception as e:
            logger.warning(f"Error updating replacements with default_replacements: {e}")
            logger.warning(f"replacements: {replacements}")
    if not replacements:
        replacements = default_replacements

    try:
        if replacements:
            try:
                replaced_text = prompt_template.format(**replacements)
            except Exception as e:
                logger.warning(f"Error replacing prompt text with format method. Using original prompt_template: {e}")
                logger.warning(f"replacements: {replacements}")
                replaced_text = prompt_template
        else:
            replaced_text = prompt_template

        logger.debug(f"replacements: {replacements}")
        logger.debug(f"replaced_text: {replaced_text[:100]}{'...' if len(replaced_text) > 100 else ''}")
    except Exception as e:
        logger.error(f"Error replacing prompt text: {e}")

    return replaced_text