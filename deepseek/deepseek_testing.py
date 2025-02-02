import openai
import re

# Configure OpenAI API (Ollama local)
openai.api_base = "http://localhost:11434/v1"
openai.api_key = "not-needed"  # Ollama doesn’t require an API key

def get_clean_response():
    """Fetches a joke from the model and cleans up unwanted tags and formatting."""
    response = openai.ChatCompletion.create(
        model="deepseek-r1:7b",  # Adjust as needed
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Tell me a joke."},
        ]
    )

    content = response["choices"][0]["message"]["content"]

    # Remove everything between <think> and </think>, including the tags themselves
    cleaned_content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)

    # Normalize spaces and ensure the output is a single line
    cleaned_content = re.sub(r"\s+", " ", cleaned_content.strip())

    return cleaned_content

if __name__ == "__main__":
    joke = get_clean_response()
    print(joke)