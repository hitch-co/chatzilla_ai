import os
import pygame

from my_modules import my_logging
from classes.ConfigManagerClass import ConfigManager

runtime_logger_level = 'WARNING'

#TODO: SHould take a client as an argument
class GPTTextToSpeech:
    # TODO (48):
    def __init__(self, openai_client):
        self.logger = my_logging.create_logger(
            debug_level=runtime_logger_level, 
            logger_name='logger_GPTTextToSpeechClass', 
            mode='w', 
            stream_logs=True
            )

        self.config = ConfigManager.get_instance()

        self.tts_client = openai_client

        # Set other class vars
        self.tts_model=self.config.tts_model
        self.tts_volume = self.config.tts_volume
        self.tts_data_folder = self.config.tts_data_folder
        self.tts_file_name = self.config.tts_file_name

    def _get_speech_response(
            self, 
            text_input:str,
            voice_name
            ) -> object:
        self.logger.info(f"Starting speech create with params: input={text_input}, model={self.tts_model}, voice={voice_name}")
        response = self.tts_client.audio.speech.create(
            model=self.tts_model,
            voice=voice_name,
            input=text_input)
        self.logger.info("Got response:")
        self.logger.info(response)
        return response
    
    def _write_speech_to_file(
            self,
            response:object,
            speech_file_path:str
            ) -> None:
        self.logger.info("starting stream to speech file")
        response.stream_to_file(speech_file_path)
        self.logger.info(f"finished stream to speech file: {speech_file_path}")

    def workflow_t2s(
            self,
            text_input,
            voice_name,
            output_filename=None,
            output_dirpath=None
            ):
        if output_filename is None:
            output_filename = self.tts_data_folder
        if output_dirpath is None:
            output_dirpath = self.output_dirpath
            
        speech_file_path = os.path.join(os.getcwd(),output_dirpath, output_filename)
        
        response = self._get_speech_response(
            text_input=text_input,
            voice_name=voice_name
            )

        self._write_speech_to_file(
            response=response, 
            speech_file_path=speech_file_path
            )

    def play_local_mp3(
            self,
            filename,
            dirpath
            ):
        pathname_to_mp3 = os.path.join(dirpath, filename)
        
        pygame.mixer.init()
        pygame.mixer.music.load(pathname_to_mp3)
        pygame.mixer.music.set_volume(self.tts_volume)
        pygame.mixer.music.play()

        # Wait for the music to finish playing
        while pygame.mixer.music.get_busy():
            continue
        
        pygame.mixer.music.stop()
        pygame.mixer.quit()

if __name__ == "__main__":
    print(f"The use of __file__ for relative path traversal prevents this module \
          from being run directly but an exmaple of how to use is provided in \
          {__name__}")

    # # Workflow
    # from classes import GPTTextToSpeech

    # output_filename = 'speech.mp3'
    # output_dirpath = 'data/tts'
    # #speech_file_path = Path(__file__).parent.parent / output_dirname / output_filename
    # text_input="hello how are you?  My name is nova and I'm watching ehitch's stream"

    # #Create client
    # tts_client = GPTTextToSpeechClass.GPTTextToSpeech(
    #     output_filename=output_filename,
    #     output_dirpath=output_dirpath
    #     )

    # # #write_speech_to_file:
    # tts_client.workflow_t2s(text_input=text_input)