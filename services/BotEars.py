import soundfile as sf
import sounddevice as sd
import numpy as np
import asyncio 
import json
import os
from collections import deque 
from datetime import datetime

from my_modules import my_logging, utils

# Set the logging level for the runtime.
runtime_logger_level = 'INFO'

class BotEars():
    """A class to handle the playing of audio files using Pygame."""

    def __init__(
            self,
            config, 
            device_name,
            event_loop, 
            duration = 15, 
            ):
        """

        """
        self.logger = my_logging.create_logger(
            debug_level=runtime_logger_level, 
            logger_name='logger_BotEars', 
            mode='w', 
            stream_logs=True
            )
        
        self.yaml_data = config
        
        # Get the audio device details from the JSON file
        self.logger.debug("self.yaml_data.app_config_dirpath: " + self.yaml_data.app_config_dirpath)
        self.logger.debug("self.yaml_data.botears_devices_json_filepath: " + self.yaml_data.botears_devices_json_filepath)
        audio_devices = utils.load_json(
            self,
            dir_path=self.yaml_data.app_config_dirpath,
            file_name=self.yaml_data.botears_devices_json_filepath
        )
        audio_device = audio_devices['audioDevices']['mic'][device_name]
        self.logger.debug(json.dumps(audio_device, indent=4))
        
        # Load device details from audio_device dictionary
        self.samplerate = audio_device['samplerate']
        self.channels = audio_device['channels']

        # Load configuration data from YAML file.
        self.botears_audio_filename = self.yaml_data.botears_audio_filename  
        self.botears_device_audio = device_name

        # initialize vars
        self.duration = duration

        # initialize the audio stream
        self.buffer = deque(maxlen=self.samplerate * duration * self.channels)
        
        self.loop = event_loop

        # Set the audio device to use
        self.stream = sd.InputStream(
            device=self.botears_device_audio,
            callback=self.audio_callback, 
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

    def audio_callback(self, indata, frames, time, status):
        """
        Callback function for the audio stream.
        """
        self.buffer.extend(indata.reshape(-1))

    async def start_stream(self):
        """
        Starts the audio stream continuously.
        """
        try:
            self.stream.start()
            self.logger.info("Audio input stream started.")
        except sd.PortAudioError as e:
            self.logger.error(f"Error starting audio stream: {e}")
    
    async def save_last_n_seconds(self, filepath, n):
        """
        Saves the last n seconds of audio to a file.
        """
        # Calculate the number of samples to keep
        num_samples = n * self.samplerate * self.channels

        # Convert the buffer to a numpy array and reshape it
        audio_data = np.array(self.buffer).reshape(-1, self.channels)

        # Ensure we only keep the last n seconds of samples
        if len(audio_data) > num_samples:
            audio_data = audio_data[-num_samples:]

        # Save the most recent n seconds of audio
        sf.write(filepath, audio_data, self.samplerate)

async def main():

    from classes.ConfigManagerClass import ConfigManager
    ConfigManager.initialize(yaml_filepath=r'C:\Users\Admin\OneDrive\Desktop\_work\__repos (unpublished)\_____CONFIG\chatzilla_ai\config\config.yaml')
    config = ConfigManager.get_instance()

    # Get the audio device details from the JSON file
    print("self.yaml_data.app_config_dirpath: " + config.app_config_dirpath)
    print("self.yaml_data.botears_devices_json_filepath: " + config.botears_devices_json_filepath)
    
    audio_devices = load_json(
        dir_path=config.app_config_dirpath,
        file_name=config.botears_devices_json_filepath
    )
    device_name = "Microphone (Yeti Classic), MME"
    audio_device = audio_devices['audioDevices']['mic'][device_name]
    print(json.dumps(audio_device, indent=4))

    # Create an event loop
    event_loop = asyncio.get_event_loop()

    try:
        ears = BotEars(
            config=config,
            device_name=device_name,
            event_loop=event_loop,
            duration=4
        )
    except Exception as e:
        print(f"Error creating BotEars instance: {e}")
    
    # run asyncio loop
    print("...starting stream")
    ears.start_stream()

    # wait for 5 seconds
    print("...sleeping app ")
    await asyncio.sleep(5)

    # save the last n seconds of audio to a file
    print("...saving audio")
    filename = os.path.join(config.botears_audio_path, config.botears_audio_filename + ".wav")
    await ears.save_last_n_seconds(
        filepath=filename,
        n=2
        )

def load_json(
        dir_path,
        file_name
        ):
    file_path = os.path.join(dir_path, file_name)
    
    #Add Error Checkign
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        return None

    return data

if __name__ == "__main__":
    asyncio.run(main())