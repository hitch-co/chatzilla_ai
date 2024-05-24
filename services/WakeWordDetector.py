import sounddevice as sd
import numpy as np
import asyncio
from vosk import Model, KaldiRecognizer
import json

from my_modules.my_logging import create_logger

class WakeWordDetector:
    def __init__(self):
        self.loop = None  # Event loop, to be set externally if not available at init

    def set_loop(self, loop):
        self.loop = loop

    async def initialize(self, device_index, model_path, wake_word, buffer_length_seconds, handle_wake_word_func, device_name=None):
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000)
        self.wake_word = wake_word.lower()
        self.handle_wake_word = handle_wake_word_func

        self.stream = sd.InputStream(
            device=device_index,
            channels=1,
            samplerate=16000,
            callback=self.audio_callback,
            dtype='int16'
        )

    async def audio_callback(self, indata, frames, time, status):
        """
        Callback function that processes the incoming audio data.
        """
        if status:
            self.logger.error(f"Stream status: {status}")

        audio_data = indata.tobytes()
        if self.recognizer.AcceptWaveform(audio_data):
            result = json.loads(self.recognizer.Result())
            text = result.get('text', '').lower()
            if self.wake_word in text:
                self.logger.info("Wake word detected!")
                # Call the custom handler function asynchronously
                # asyncio.run_coroutine_threadsafe(self.handle_wake_word(text), asyncio.get_running_loop())
                asyncio.run_coroutine_threadsafe(self.handle_wake_word(text), self.loop)
                #await self.handle_wake_word(text)
    
    async def start(self):
        """
        Starts the audio stream asynchronously.
        """
        self.stream.start()
        self.logger.info("Audio input stream started.")

    async def stop(self):
        """
        Stops the audio stream and cleans up resources.
        """
        self.stream.stop()
        self.stream.close()
        self.logger.info("Audio input stream stopped.")

if __name__ == "__main__":
    async def custom_wake_word_action(recognized_text):
        print(f"Custom action for detected wake word: {recognized_text}")

    async def main():
        detector = WakeWordDetector(
            device_index=4,
            model_path=r"C:\_repos\chatzilla_ai_prod\chatzilla_ai\models\vosk-model-small-en-us-0.15",
            wake_word="computer",
            buffer_length_seconds=10,
            handle_wake_word_func=custom_wake_word_action  # Pass the custom function here
        )
        await detector.start()

        try:
            while True:
                await asyncio.sleep(1)  # Run indefinitely
        except KeyboardInterrupt:
            print("Stopping...")
        finally:
            await detector.stop()

    asyncio.run(main())
