import re

class GPTResponseCleaner:
    @staticmethod
    def _strip_prefix(text: str) -> str:
        """Strips prefixes of the form <<<[some_name]>>> from the text and removes excess colons/spaces correctly."""
        pattern = r'<<<[^>]*>>>'
        stripped_text = re.sub(pattern, '', text).strip()

        # Remove leading colons and spaces
        stripped_text = re.sub(r'^[:\s]+', '', stripped_text).strip()

        return stripped_text

    @staticmethod
    def _remove_quotes(text: str) -> str:
        """Removes surrounding quotes only if they exist at both start and end."""
        if text.startswith('"') and text.endswith('"'):
            return text[1:-1] 
        return text

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """Replaces multiple spaces with a single space."""
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def _clean_think_tags(text: str) -> str:
        """Removes <think>...</think> tags from the text."""
        return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

    @staticmethod
    def perform_all_gpt_response_cleanups(text: str) -> str:
        """Performs all cleanup operations on the text."""
        cleaned_text = GPTResponseCleaner._strip_prefix(text)
        cleaned_text = GPTResponseCleaner._normalize_whitespace(cleaned_text)
        cleaned_text = GPTResponseCleaner._clean_think_tags(cleaned_text)
        cleaned_text = GPTResponseCleaner._remove_quotes(cleaned_text)
        return cleaned_text
    
def main():
    text = '<<<[assistant_name]>>>  : Hello   there!  How can I help you today?'
    cleaned_text = GPTResponseCleaner.perform_all_gpt_response_cleanups(text)
    print(f"Cleaned Text: '{cleaned_text}'")

if __name__ == '__main__':
    main()
