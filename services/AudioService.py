import os
import pygame

from my_modules.config import run_config
from my_modules import my_logging

# Set the logging level for the runtime.
runtime_logger_level = 'WARNING'

class AudioPlayer:
    """A class to handle the playing of audio files using Pygame."""

    def __init__(self):
        """
        Initializes the AudioPlayer instance.
        - Sets up logging with specified runtime logger level.
        - Loads configuration data from YAML file.
        """
        self.logger = my_logging.create_logger(
            debug_level=runtime_logger_level, 
            logger_name='logger_AudioPlayerService', 
            mode='w', 
            stream_logs=True
            )

        # Load configuration data from YAML file.
        self.yaml_data = run_config()

    def play_local_mp3(self, filename: str, dirpath: str, volume: int = 0.5):
        """
        Plays an MP3 file located at the specified directory with the given volume.

        Args:
            filename (str): Name of the MP3 file.
            dirpath (str): Directory path where the MP3 file is located.
            volume (int, optional): Volume for playing the audio. Defaults to 0.5.
        """
        # Construct the full path to the MP3 file.
        pathname_to_mp3 = os.path.join(dirpath, filename)
        
        # Initialize pygame mixer, load and play the audio file.
        pygame.mixer.init()
        pygame.mixer.music.load(pathname_to_mp3)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play()

        # Wait for the music to finish playing.
        while pygame.mixer.music.get_busy():
            continue
        
        # Stop the mixer after the music has finished.
        pygame.mixer.music.stop()
        pygame.mixer.quit()

def main():
    """
    Main function to create an instance of AudioPlayer and play a specific audio file.
    """
    audio_player = AudioPlayer()
    audio_player.play_local_mp3(
        filename='surprise-sound-effect-99300.mp3',
        dirpath='data/media',
        volume=0.5
        )

if __name__ == "__main__":
    main()
