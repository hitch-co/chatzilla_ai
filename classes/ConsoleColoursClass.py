class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    PRAG_SUX = '\033[91m'

def printc(message, color_name):
    """Prints a message in a specific color.

    Args:
        message (str): The message to be printed.
        color_name (str): One of HEADER, WARNING, FAIL, etc.

    """
    print(color_name + message + bcolors.ENDC)