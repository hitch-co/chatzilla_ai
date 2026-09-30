import os
import pygame
import re

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

    def _strip_story_number(self, text_input):
        pattern = r'\(\d+\s*(?:/|of)\s*\d+\)'
        return re.sub(pattern, '', text_input).strip()

    def _get_speech_response(
            self, 
            text_input:str,
            voice_name
            ) -> object:
        self.logger.debug(f"Starting speech create with params: input={text_input}, model={self.tts_model}, voice={voice_name}")
        
        text_input = self._strip_story_number(text_input)
        
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
        self.logger.debug("starting write to speech file")
        response.write_to_file(speech_file_path)
        self.logger.debug(f"finished write to speech file: {speech_file_path}")

    def workflow_t2s(
            self,
            text_input,
            voice_name,
            output_filename=None,
            output_dirpath=None
            ):
        if output_filename is None:
            output_filename = self.tts_file_name
            self.logger.debug(f"output_filename is None, setting to {output_filename}")
        if output_dirpath is None:
            output_dirpath = self.tts_data_folder
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

def main():
    import dotenv
    import openai
    from my_modules import utils

    dotenv.load_dotenv(dotenv_path='./config/.env')
    yaml_filepath = os.getenv('CHATZILLA_CONFIG_YAML_FILEPATH')
    ConfigManager.initialize(yaml_filepath)
    config = ConfigManager.get_instance()

    with openai.OpenAI(api_key=config.openai_api_key) as gpt_client:
        tts_client = GPTTextToSpeech(gpt_client)
        datetime_string = utils.get_current_datetime_formatted()['filename_format']
        output_filename = "milestone5_" + datetime_string + "_" + tts_client.tts_file_name
        print(f"Generating speech with {tts_client.tts_model}, voice {config.tts_voice_chatforme}")
        tts_client.workflow_t2s(
            text_input="Hello! This is Chatzilla's speech check. The robot gardener is ready to plant a moon garden.",
            voice_name=config.tts_voice_chatforme,
            output_filename=output_filename
        )
        speech_file_path = os.path.abspath(os.path.join(tts_client.tts_data_folder, output_filename))
        print(f"Speech saved to: {speech_file_path}")
        tts_client.play_local_mp3(filename=output_filename, dirpath=tts_client.tts_data_folder)
        print("Speech playback complete.")

if __name__ == "__main__":
    main()
