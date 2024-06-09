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
    if replacements:
        replaced_text = prompt_template.format(**replacements)
    else:
        replaced_text = prompt_template

    logger.debug(f"replacements: {replacements}")
    logger.debug(f"replaced_text: {replaced_text[:75]}")
    return replaced_text