import json
import os
from datetime import datetime

from my_modules.my_logging import create_logger

logger = create_logger(
    dirname='log', 
    logger_name='logger_utils',
    debug_level='DEBUG',
    mode='a',
    stream_logs=False
    )

def show_json(obj):
    # Assuming obj.model_dump_json() returns a JSON string
    json_data = json.loads(obj.model_dump_json())
    return json.dumps(json_data, indent=4)

def format_previous_messages_to_string(message_list):
    # message_list=[
    #     {'role':'bot','content':'hello there im eric'},
    #     {'role':'bot','content':'hello there im eric'}
    # ]
    formatted_messages = []

    for message in message_list:
        if message['role'] == 'bot':
            formatted_messages.append(f'- "{message["content"]}"')

    formatted_str = '\n'.join(formatted_messages)
    return formatted_str

def get_user_input(predefined_text=None):
    """
    Get user input with basic error-checking.

    Parameters:
    - predefined_text (str): A predefined text that can be used in lieu of user input.

    Returns:
    str: Validated user input or the predefined text.
    """
    while True:
        # Check predefined text
        if predefined_text:
            user_text = predefined_text
            predefined_text = None  # Clear it after using once to ensure next iterations use input
        else:
            user_text = input("Please enter the gpt prompt text here: ")

        # 1. Check for empty input
        if not user_text.strip():
            print("Error: Text input cannot be empty. Please provide valid text.")
            continue

        # 2. Check for maximum length
        max_length = 100
        if len(user_text) > max_length:
            print(f"Error: Your input exceeds the maximum length of {max_length} characters. Please enter a shorter text.")
            continue

        # 3. Check for prohibited characters
        prohibited_chars = ["@", "#", "$", "%", "&", "*", "!"]
        if any(char in user_text for char in prohibited_chars):
            print(f"Error: Your input contains prohibited characters. Please remove them and try again.")
            continue

        # 4. Check if string contains only numbers
        if user_text.isdigit():
            print("Error: Text input should not be only numbers. Please provide a valid text.")
            continue

        # 5. Check for profanities
        profanities = ["idiot", "loser", "asshole"]
        if any(word in user_text.lower() for word in profanities):
            print("Error: Please avoid using inappropriate language.")
            continue
            
        return user_text
    
def shutdown_server():
    from flask import request 
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

def combine_json_files(directory ='.path/to/directory/of/jsonfiles') -> list[list[dict]]:
    combined_data = []

    # List all the .json files in the given directory
    files = [f for f in os.listdir(directory) if f.endswith('.json')]

    for filename in files:
        filepath = os.path.join(directory, filename)
        
        # Open the .json file and load its content
        with open(filepath, 'r') as file:
            data = json.load(file)
            combined_data.append(data)
    
    return combined_data

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

def conv_datetime_formats(ctx_message_timestamp):
    timestamp_formatted = datetime.utcfromtimestamp(ctx_message_timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
    print("convert")
    return timestamp_formatted

def format_record_timestamp(record: dict) -> dict:
    """Format the 'timestamp' field in a record."""
    record['timestamp'] = datetime.utcfromtimestamp(record['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
    return record

def write_msg_history_to_file(msg_history, variable_name_text, logger, dirname='log/ouat_story_history', include_datetime=False):
    if include_datetime:
        current_datetime = "_"+get_datetime_formats()['filename_format']
    else:
        current_datetime = ''

    if not os.path.exists(dirname):
        os.makedirs(dirname)
    filename = f"{dirname}/final_{variable_name_text}{current_datetime}.json"
    
    with open(filename, 'w') as file:
        json.dump(msg_history, file, indent=4)

    logger.debug(f"Message history written to {filename}")

def write_json_to_file(data, variable_name_text, dirname='log/get_chatters_data', include_datetime=False):
    if include_datetime:
        current_datetime = "_"+get_datetime_formats()['filename_format']
    else:
        current_datetime = ''

    if not os.path.exists(dirname):
        os.makedirs(dirname)
        logger.debug(f"Directory {dirname} created.")
    
    filename = f"{dirname}/final_{variable_name_text}{current_datetime}.json"

    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)
        file.close()

    logger.debug(f"JSON data written to {filename}")

def write_query_to_file(formatted_query, dirname='log/queries', queryname='default', include_datetime=False):
    if include_datetime:
        current_datetime = "_"+get_datetime_formats()['filename_format']
    else:
        current_datetime = ''

    if not os.path.exists(dirname):
        os.makedirs(dirname)
        logger.debug(f"Directory {dirname} created.")

    filename = f"{dirname}/{queryname}{current_datetime}.sql"

    with open(filename, 'w', encoding='utf-8') as file:
        file.write(formatted_query)

    logger.debug(f"Query written to {filename}")