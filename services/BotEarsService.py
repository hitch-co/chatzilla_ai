import soundfile as sf
import sounddevice as sd
import numpy as np
import asyncio 
import json
import os
from collections import deque 

from my_modules import my_logging, utils

# Set the logging level for the runtime.
runtime_logger_level = 'INFO'

class BotEars():
    """A class to handle the playing of audio files using Pygame."""

    def __init__(
            self,
            config, 
            device_name,
            buffer_length_seconds, 
            ):
        """

        """
        self.logger = my_logging.create_logger(
            debug_level=runtime_logger_level, 
            logger_name='logger_BotEars', 
            mode='w', 
            stream_logs=True
            )
        
        self.config = config

        # Create the output directory if it doesn't exist
        if not os.path.exists(self.config.botears_audio_path):
            os.makedirs(self.config.botears_audio_path)
            
        # Get the audio device details from the JSON file
        self.logger.debug("self.config.app_config_dirpath: " + self.config.app_config_dirpath)
        self.logger.debug("self.config.botears_devices_json_filepath: " + self.config.botears_devices_json_filepath)
        audio_devices = utils.load_json(
            path_or_dir=self.config.app_config_dirpath,
            file_name=self.config.botears_devices_json_filepath
        )
        audio_device = audio_devices['audioDevices']['mic'][device_name]
        self.samplerate = audio_device['samplerate']
        self.channels = audio_device['channels']

        self.logger.debug(f"These are the json audio device details for {device_name}:")
        self.logger.debug(json.dumps(audio_device, indent=4))

        # Load configuration data from YAML file.
        self.botears_audio_filename = self.config.botears_audio_filename  

        # initialize vars
        self.buffer_length_seconds = buffer_length_seconds

        # initialize the audio stream
        self.buffer = deque(maxlen=buffer_length_seconds * self.samplerate * self.channels)

        # Set the audio device to use
        self.stream = sd.InputStream(
            device=device_name,
            callback=self._audio_callback, 
            samplerate=self.samplerate, 
            channels=self.channels
            )

    def log_stream_state(self):
        if self.stream.active:
            self.logger.info("Stream is active.")
        else:
            self.logger.info("Stream is inactive.")

    def find_device_index(device_name):
        devices = sd.query_devices()
        for index, device in enumerate(devices):
            if device_name in device['name']:
                return index
        raise ValueError(f"Device {device_name} not found.")

    def _audio_callback(self, indata, frames, time, status):
        """
        Callback function for the audio stream.
        """
        self.buffer.extend(indata.reshape(-1))

    async def start_botears_audio_stream(self):
        """
        Starts the audio stream continuously.
        """
        try:
            self.stream.start()
            self.logger.info("Audio input stream started.")
        except sd.PortAudioError as e:
            self.logger.error(f"Error starting audio stream: {e}")
    
    async def save_last_n_seconds(
            self, 
            filepath, 
            saved_seconds
            ):
        """
        Saves the last n seconds of audio to a file.
        """
        # Calculate the number of samples to keep
        num_samples = saved_seconds * self.samplerate * self.channels

        # Convert the buffer to a numpy array and reshape it
        audio_data = np.array(self.buffer).reshape(-1, self.channels)

        # Ensure we only keep the last n seconds of samples
        if len(audio_data) > num_samples:
            audio_data = audio_data[-num_samples:]

        # Save the most recent n seconds of audio
        sf.write(filepath, audio_data, self.samplerate)

        self.logger.debug(f"Saved {saved_seconds} seconds of audio to: {filepath}")

async def main():

    from classes.ConfigManagerClass import ConfigManager
    ConfigManager.initialize(yaml_filepath=r'C:\_repos\chatzilla_ai\config\config.yaml')
    config = ConfigManager.get_instance()

    # Get the audio device details from the JSON file
    print("self.config.app_config_dirpath: " + config.app_config_dirpath)
    print("self.config.botears_devices_json_filepath: " + config.botears_devices_json_filepath)
    
    audio_devices = utils.load_json(
        path_or_dir=config.app_config_dirpath,
        file_name=config.botears_devices_json_filepath
    )
    device_name = "Microphone (Yeti Classic), MME"
    audio_device = audio_devices['audioDevices']['mic'][device_name]
    print(f"These are the json audio device details for {device_name}:")
    print(json.dumps(audio_device, indent=4))

    try:
        ears = BotEars(
            config=config,
            device_name=device_name,
            #event_loop=event_loop, # Removed 2024-02-10      
            buffer_length_seconds=4
        )
    except Exception as e:
        print(f"Error creating BotEars instance: {e}")
    
    # run asyncio loop
    await ears.start_botears_audio_stream()

    # wait for 5 seconds
    print("...sleeping app.  This is not done in the class itself as the audio  \
          stream is running constantly.  This is just to simulate the app running.")
    await asyncio.sleep(5)

    # save the last n seconds of audio to a file
    filename = os.path.join(config.botears_audio_path, config.botears_audio_filename + ".wav")
    await ears.save_last_n_seconds(
        filepath=filename,
        n=4
        )

if __name__ == "__main__":
    asyncio.run(main())