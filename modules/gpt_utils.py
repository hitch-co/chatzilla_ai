def replace_prompt_text(logger, prompt_template, replacements=None):
    """
    Replaces placeholders in the prompt template with the corresponding values from the replacements dictionary.

    Parameters:
    logger (Logger): The logger object to use for debugging output.
    prompt_template (str): The template text containing placeholders for replacement.
    replacements (dict, optional): A dictionary containing the replacement values. Defaults to None.

    Returns:
    str: The prompt text with placeholders replaced by actual values.
    """
    try:
        if replacements:
            try:
                replaced_text = prompt_template.format(**replacements)
            except:
                logger.warning("Error replacing prompt text with format method. Using original prompt_template.")
                replaced_text = prompt_template
        else:
            replaced_text = prompt_template

        logger.debug(f"replacements: {replacements}")
        logger.debug(f"replaced_text: {replaced_text[:75]}")
    except Exception as e:
        logger.error(f"Error replacing prompt text: {e}")

    return replaced_text