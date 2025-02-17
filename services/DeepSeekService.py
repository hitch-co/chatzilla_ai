import asyncio
import aiohttp
import json
import re

from my_modules.my_logging import create_logger
from my_modules import utils
from classes.ConfigManagerClass import ConfigManager

runtime_logger_level = 'INFO'

# -------------------------------
# Async DeepSeek AI Client using aiohttp
# -------------------------------
class AsyncDeepSeekAIClient:
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
        self.lock = asyncio.Lock()

        self.logger = create_logger(
            dirname='log',
            logger_name='AsyncDeepSeekAIClient',
            debug_level=runtime_logger_level,
            mode='w',
            stream_logs=True,
            encoding='UTF-8'
        )
        self.logger.info(f"Initialized AsyncDeepSeekAIClient with base_url: {self.base_url}")

    async def list_models(self):
        url = f"{self.base_url}/api/tags"
        self.logger.debug(f"Requesting list_models from URL: {url}")
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                self.logger.debug(f"list_models response: {data}")
                return data

    async def list_running_models(self):
        url = f"{self.base_url}/api/ps"
        self.logger.debug(f"Requesting list_running_models from URL: {url}")
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                self.logger.debug(f"list_running_models response: {data}")
                return data

    async def _generate_text(self, model, prompt, stream=False):
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream
        }
        self.logger.debug(f"Generating text with payload: {payload}")
        headers = {"Content-Type": "application/json"}
        
        # Protect GPU-intensive calls by locking
        async with self.lock:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                    response = await resp.json()
                    response_text = response.get("response", "")
                    self.logger.debug(f"_generate_text response: {response}")
                    return response

    async def _chat(self, model, messages, stream=False):
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream
        }
        self.logger.debug(f"Chatting with payload: {payload}")
        headers = {"Content-Type": "application/json"}

        # Protect GPU-intensive calls by locking
        async with self.lock:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                    response = await resp.json()
                    self.logger.debug(f"_chat response: {response}")
                    return response

    async def get_deepseek_response_chat(
            self, 
            model, 
            prompt="tell me a joke.", 
            system_prompt="You are a helpful assistant.",
            messages = None
        ):
        """
        Uses the async deepseek client to send a chat request and cleans the result.
        messages should be a list of dictionaries with keys 'role' and 'content'.
        """
        self.logger.info(f"get_deepseek_response_chat called with model: '{model}', prompt: '{prompt}'")
        self.logger.info(f"System prompt: {system_prompt}")
        self.logger.info(f"Messages: {messages}")

        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
            self.logger.debug(f"Converted string message to list: {messages}")

        if messages is None:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            self.logger.debug("No messages provided, using default system and user messages.")
        else:
            # Ensure messages is properly extended without nesting
            self.logger.debug(f"Original messages: {messages}")
            messages = [{"role": "system", "content": system_prompt}] + messages + [{"role": "user", "content": prompt}]
            self.logger.debug(f"Extended messages: {messages}")

        try:
            response = await self._chat(model, messages)
            self.logger.debug(f"deepseek _chat return: {response}")
        except Exception as e:
            self.logger.error(f"Error during _chat call: {e}")
            raise

        # Expecting a structure like: { "message": { "role": "assistant", "content": "..." } }
        if "message" in response and "content" in response["message"]:
            content = response["message"]["content"]
            self.logger.debug("Extracted content from response message.")
        else:
            content = str(response)
            self.logger.warning("Response did not contain expected 'message' structure. Using stringified response.")

        return content

    async def get_deepseek_response_generate(self, model, prompt):
        """
        Uses the async deepseek client to send a generate request and cleans the result.
        """
        self.logger.info(f"get_deepseek_response_generate called with model: {model}, prompt: {prompt}")

        try:
            response = await self._generate_text(model, prompt)
            self.logger.debug(f"Deepseek _generate_text return: {response}")
        except Exception as e:
            self.logger.error(f"Error during _generate_text call: {e}")
            raise

        # Expecting a structure like: {'model': 'deepseek-r1:7b', 'created_at': '2025-02-16T15:59:43.3383584Z', 'response': '<think>audience.\n</think>\n\nYo mama is', 'done': True, 'done_reason': 'stop', 'context': [15164],...} 
        if "response" in response:
            content = response["response"]
            self.logger.info(f"Extracted content from response using key 'response': {content}")
        else:
            content = str(response)
            self.logger.warning("Response did not contain expected 'response' key. Using stringified response.")

        return content

# -------------------------------
# Dummy implementations for running sample endpoint calls
# -------------------------------
async def run_deepseek_sample():
    ai_client = AsyncDeepSeekAIClient()
    try:
        models = await ai_client.list_models()
        print(f"Models: {models}")
    except Exception as e:
        ai_client.logger.error(f"Error listing models: {e}")

    # Uncomment one of the examples below:

    # # EXAMPLE1: Chat
    # try:
    #     response = await ai_client.get_deepseek_response_chat(
    #         model='deepseek-r1:7b',
    #         messages=[
    #             {"role": "system", "content": "You are a helpful assistant."},
    #             {"role": "user", "content": "Tell me a joke."},
    #             {"role": "user", "content": "like a joke about alligators"},
    #             {"role": "user", "content": "alligator babies actually!"}
    #         ]
    #     )
    #     print(f"Chat Response Content: {response}")
    # except Exception as e:
    #     ai_client.logger.error(f"Error in chat example: {e}")

    # EXAMPLE2: Generate
    try:
        response = await ai_client.get_deepseek_response_generate(
            model='deepseek-r1:7b',
            prompt="Tell me a joke asbout baby chincillas."
        )
        print(f"Generate Response Content: {response}")
    except Exception as e:
        ai_client.logger.error(f"Error in generate example: {e}")

# -------------------------------
# Async main for testing the integrated service
# -------------------------------
if __name__ == "__main__":
    async def main():
        await run_deepseek_sample()

    asyncio.run(main())
