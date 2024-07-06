import os
import pygame
import re
import json

from my_modules import my_logging
from classes.ConfigManagerClass import ConfigManager

runtime_logger_level = 'INFO'

class GPTTextToSpeech:
    def __init__(self, openai_client):
        self.logger = my_logging.create_logger(
            debug_level=runtime_logger_level, 
            logger_name='logger_GPTTextToSpeechClass', 
            mode='w', 
            stream_logs=True
            )
        
        self.config = ConfigManager.get_instance()
        self.tts_client = openai_client

        self.tts_model=self.config.tts_model
        self.tts_volume = self.config.tts_volume
        self.tts_data_folder = self.config.tts_data_folder
        self.tts_file_name = self.config.tts_file_name

        if not os.path.exists(self.config.tts_data_folder):
            os.makedirs(self.config.tts_data_folder)

        # Read in json file of things to rename for text to speech
        with open(self.config.tts_text_replacements_filename, 'r') as f:
            self.tts_text_replacements = json.load(f)
            self.logger.debug("Finished reading in json file of things to rename for text to speech")

    def _strip_story_number(self, text_input):
        # Stories include a number in parenthesis that should be removed from tts
        pattern = r'\(\d+ of \d+\)'
        return re.sub(pattern, '', text_input).strip()

    def _rename_things_for_tts(self, text_input):
        # This is a workaround for poor tts pronunciation
        # NOTE: partial matches will also be substituted
        for original, new in self.tts_text_replacements.items():
            pattern = re.compile(r'\b' + re.escape(original) + r'\b', re.IGNORECASE)
            text_input = pattern.sub(new, text_input)
        
        return text_input

    def _get_speech_response(
            self, 
            text_input:str,
            voice_name
            ) -> object:
        self.logger.debug(f"Starting speech create with params: input={text_input}, model={self.tts_model}, voice={voice_name}")
        
        text_input = self._strip_story_number(text_input)
        text_input = self._rename_things_for_tts(text_input)
        
        response = self.tts_client.audio.speech.create(
            model=self.tts_model,
            voice=voice_name,
            input=text_input
            )
        self.logger.debug("Got response:")
        self.logger.debug(response)
        return response
    
    def _write_speech_to_file(
            self,
            response:object,
            speech_file_path:str
            ) -> None:
        self.logger.debug("starting stream to speech file")
        response.stream_to_file(speech_file_path)
        self.logger.debug(f"finished stream to speech file: {speech_file_path}")

    def workflow_t2s(
            self,
            text_input,
            voice_name,
            output_filename=None,
            output_dirpath=None
            ):
        if output_filename is None:
            output_filename = self.tts_data_folder
            self.logger.debug(f"output_filename is None, setting to {output_filename}")
        if output_dirpath is None:
            output_dirpath = self.output_dirpath
            self.logger.debug(f"output_dirpath is None, setting to {output_dirpath}")
            
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