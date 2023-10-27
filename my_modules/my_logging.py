import logging
import inspect

def my_logger(dirname='log', 
              logger_name=None, 
              debug_level='DEBUG', 
              mode='w',
              stream_logs = True,
              encoding='UTF-8'
              ):
    
    level_mapping = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'EXCEPTION': logging.ERROR,  # Exception is not a level in Python logging; it's usually logged as an ERROR
    }

    if debug_level.upper() not in level_mapping:
        raise ValueError(f"Invalid debug_level: {debug_level}. Must be one of: {', '.join(level_mapping.keys())}")

    logger = logging.getLogger(logger_name if logger_name else __name__)
    
    # Clear existing handlers
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    logger.setLevel(level_mapping[debug_level.upper()])

    formatter = logging.Formatter('%(asctime)s - %(module)s - %(levelname)s - Name: %(funcName)s - Line: %(lineno)d - %(message)s')

    file_handler = logging.FileHandler(f'{dirname}/{logger_name}.log', mode=mode, encoding=encoding)
    file_handler.setLevel(level_mapping[debug_level.upper()])
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if stream_logs == True:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(level_mapping[debug_level.upper()])
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
    
    return logger


def my_function_logger(dirname = 'log', 
                       logger_name=None
                       ):
    
    logger = logging.getLogger(logger_name if logger_name else __name__)
    
    # Clear existing handlers
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(module)s - %(funcName)s - %(levelname)s - Line: %(lineno)d - %(message)s')

    file_handler = logging.FileHandler(f'{dirname}/{logger_name}_{inspect.currentframe().f_code.co_name}.log')
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger    

def log_list_or_dict(logger, obj:list|dict=None):
    # Logging logic
    if isinstance(obj, list):
        for item in obj:
            logger.debug("Role: %s, Content: %.50s%s", item['role'], item['content'], '...' if len(item['content']) > 50 else '')
    elif isinstance(obj, dict):
        logger.debug("Role: %s, Content: %.50s%s", obj['role'], obj['content'], '...' if len(item['content']) > 50 else '')
    else:
        logger.warning("Unsupported data type")

def log_dynamic_dict(logger, obj: dict = None):
    # Logging logic for a generic dictionary
    if obj is None:
        logger.warning("Empty dictionary passed")
        return

    if not isinstance(obj, dict):
        logger.warning("Unsupported data type")
        return

    for key, value in obj.items():
        truncated_value = str(value)[:50]  # Truncate the value to 50 characters if needed
        logger.debug("Key: %s, Value: %.50s%s", key, truncated_value, '...' if len(str(value)) > 50 else '')