import logging
import inspect

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

def log_runtime_params(logger, context_object, args_list=None):
    if args_list is None:
        logger.warning("No arguments provided to print_runtime_params.")
        return

    logger.info("These are the runtime params for this bot:")
    for arg in args_list:
        try:
            value = getattr(context_object, arg)
            logger.info(f"{arg}: {value}")
        except AttributeError:
            logger.error(f"Attribute {arg} not found in the provided object.")

def log_function_args(logger):
    """
    Decorator for logging the arguments of a function as a dictionary.

    Args:
        logger (logging.Logger): The logger object to use for logging the arguments.

    This decorator creates a single log entry containing both positional and
    keyword arguments passed to the function it decorates, formatted as a dictionary.
    It's useful for concise logging and easier tracking of function calls.

    Usage:
        @log_function_args(logger)
        def some_function(arg1, arg2, ...):
            ...

    Note:
        The logger must be configured beforehand to ensure proper logging output.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            arg_names = inspect.getfullargspec(func).args
            args_dict = {name: value for name, value in zip(arg_names, args)}
            args_dict.update(kwargs)
            logger.debug(f"Function '{func.__name__}' called with arguments: {args_dict}")
            return func(*args, **kwargs)    
        return wrapper
    return decorator

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