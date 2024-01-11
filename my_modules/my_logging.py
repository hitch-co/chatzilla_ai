import logging
import inspect
import json

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

def ___log_runtime_params(logger, context_object, args_list=None):
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

def ___log_function_args(logger):
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

def ___truncate_obj_strings(obj):
    """
    Truncates string values in the object to a maximum length of 50 characters.
    This function is recursively applied to each value in the object.
    """
    if isinstance(obj, dict):
        return {k: ___truncate_obj_strings(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [___truncate_obj_strings(v) for v in obj]
    elif isinstance(obj, str):
        return obj[:50] + '...' if len(obj) > 50 else obj
    else:
        return obj

def ___log_as_json(logger, obj, indent=2):
    """
    Log an object as a JSON-formatted string, with individual string values truncated.

    Args:
        logger (logging.Logger): The logger object to use for logging the formatted string.
        obj (object): The object to be logged.
        indent (int, optional): The indentation level for the JSON string. Defaults to 2.
    """
    try:
        # Serialize the object to a JSON string with custom serialization for long strings
        json_string = json.dumps(obj, indent=indent, default=_truncate_long_strings)

        logger.debug(json_string)

    except TypeError as e:
        # Fallback in case serialization fails
        logger.warning(f"Failed to serialize object to JSON: {e}")
        logger.debug(str(obj))