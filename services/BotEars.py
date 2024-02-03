
import soundfile as sf
import sounddevice as sd
import numpy as np
import asyncio 

from my_modules.config import run_config
from my_modules import my_logging

# Set the logging level for the runtime.
runtime_logger_level = 'DEBUG'

class BotEars:
    """A class to handle the playing of audio files using Pygame."""

    def __init__(
            self, 
            audio_device,
            event_loop, 
            duration: int = 7, 
            samplerate = 44100, 
            channels = 2):
        """

        """
        self.logger = my_logging.create_logger(
            debug_level=runtime_logger_level, 
            logger_name='logger_BotEars', 
            mode='w', 
            stream_logs=True
            )

        # Load configuration data from YAML file.
        self.yaml_data = run_config()
        self.botears_audio_filename = self.yaml_data['botears_audio_filename']  
        self.botears_device_audio = audio_device

        # initialize vars
        self.duration = duration
        self.samplerate = samplerate
        self.channels = channels

        # initialize the audio stream
        self.buffer = np.zeros((samplerate * duration, channels))
        
        self.loop = event_loop

        self.stream = sd.InputStream(
            device=self.botears_device_audio,
            callback=self.audio_callback, 
            samplerate=self.samplerate, 
            channels=self.channels
            )

    def find_device_index(device_name):
        devices = sd.query_devices()
        for index, device in enumerate(devices):
            if device_name in device['name']:
                return index
        raise ValueError(f"Device {device_name} not found.")

    def audio_callback(self, indata, frames, time, status):
        """
        Callback function for the audio stream.
        """
        self.buffer = np.roll(self.buffer, -frames, axis=0)
        self.buffer[-frames:] = indata

    async def start_stream(self):
        """
        Starts the audio stream.
        """
        with self.stream:
            await asyncio.sleep(self.duration)

    def save_last_n_seconds(self):
        """
        Saves the last n seconds of audio to a file.
        """
        filename = self.botears_audio_filename 
        buffer = self.buffer
        samplerate = self.samplerate
        
        sf.write(filename, buffer, samplerate)

async def main():
    # Create an event loop
    event_loop = asyncio.get_event_loop()
    
    yaml_data = run_config()
    botears_device_audio = yaml_data['botears_device_mic']

    # Create an instance of BotEars
    ears = BotEars(
        audio_device=botears_device_audio,
        event_loop=event_loop,
        duration=4,
        samplerate=48000,
        channels=2
    )

    # pause script
    await asyncio.sleep(5)

    # run asyncio loop
    await ears.start_stream()

    # save the last n seconds of audio to a file
    ears.save_last_n_seconds()
    

if __name__ == "__main__":
    # Create an event loop
    event_loop = asyncio.get_event_loop()

    # Run the main function
    event_loop.run_until_complete(main())
    