import json
import logging
import logging.config

from classes.ConsoleColoursClass import ColoredFormatter

def setup_logging_from_json(path_to_json: str):
    with open(path_to_json, 'r') as f:
        logging_config_from_json = json.load(f)

    logging.config.dictConfig(logging_config_from_json)

def create_logger(
        dirname='log', 
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
        'CRITICAL': logging.ERROR,
    }

    if debug_level.upper() not in level_mapping:
        raise ValueError(f"Invalid debug_level: {debug_level}. Must be one of: {', '.join(level_mapping.keys())}")

    logger = logging.getLogger(logger_name if logger_name else __name__)
    logger.propagate = False

    # Clear existing handlers
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    logger.setLevel(level_mapping[debug_level.upper()])

    log_format = (
            '%(asctime)s - %(module)s - %(levelname)s - Name: %(funcName)s - Line: %(lineno)d - %(message)s'
        )

    formatter = logging.Formatter(
        log_format,
        datefmt='%H:%M:%S'
        )

    file_handler = logging.FileHandler(f'{dirname}/{logger_name}.log', mode=mode, encoding=encoding)
    file_handler.setLevel(level_mapping[debug_level.upper()])
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if stream_logs == True:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(level_mapping[debug_level.upper()])
        colored_formatter = ColoredFormatter(
            log_format,
            datefmt='%H:%M:%S'
        )      
        stream_handler.setFormatter(colored_formatter)
        logger.addHandler(stream_handler)

    return logger