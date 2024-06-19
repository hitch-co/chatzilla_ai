import logging

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
    CRITICAL = '\033[1;31m'

class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': bcolors.OKCYAN,
        'INFO': bcolors.OKGREEN,
        'WARNING': bcolors.WARNING,
        'ERROR': bcolors.FAIL,
        'CRITICAL': bcolors.BOLD + bcolors.FAIL,
    }

    def format(self, record):
        color = self.COLORS.get(record.levelname, bcolors.ENDC)
        message = super().format(record)
        return f"{color}{message}{bcolors.ENDC}"