import re
from typing import Optional

class GPTResponseCleaner:
    @staticmethod
    def strip_prefix(text: str) -> str:
        """Strips prefixes of the form <<<[some_name]>>> from the text."""
        pattern = r'<<<[^>]*>>>'
        stripped_text = re.sub(pattern, '', text)
        return stripped_text.lstrip(':').lstrip(' ').lstrip(':').lstrip(' ')

    def remove_quotes(text: str) -> str:
        """Removes quotes from the text only if they are explicitly the first and the last character. If the yare the first or the last, don't do it (cuz it might start with a quote or end with a quote)"""
        if text.startswith('"') and text.endswith('"'):
            return text[1:-1] 
        return text
    
    def perform_all_gpt_response_cleanups(text: str) -> str:
        """Performs all the cleanup operations on the text."""
        cleaned_text = GPTResponseCleaner.strip_prefix(text)
        cleaned_text = GPTResponseCleaner.remove_quotes(cleaned_text)
        return cleaned_text
    
def main():
    text = '<<<[assistant_name]>>>: Hello there! How can I help you today?'
    cleaned_text = GPTResponseCleaner.strip_prefix(text)
    print(cleaned_text)

if __name__ == '__main__':
    main()