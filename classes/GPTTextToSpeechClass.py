from pathlib import Path
import os

import openai
from openai import OpenAI

from my_modules.config import load_env, load_yaml
from my_modules import my_logging

#TODO: SHould take a client as an argument
class GPTTextToSpeech:
    def __init__(self, output_filename='class_default_speech.mp3', output_dirpath=None):
        self.logger = my_logging.create_logger(
            debug_level='INFO', 
            logger_name='logger_GPTTextToSpeechClass', 
            mode='a', 
            stream_logs=True
            )
        
        load_env() # Load environment variables
        openai.api_key = os.getenv('OPENAI_API_KEY')        
        
        self.yaml_data = load_yaml() # Load assistant configuration from a YAML file
        self.tts_model=self.yaml_data['openai-api']['tts_model']
        self.tts_voice=self.yaml_data['openai-api']['tts_voice']
        self.tts_data_folder = self.yaml_data['openai-api']['tts_data_folder']

        ##folder/file details
        self.output_filename = output_filename
        self.output_dirpath = output_dirpath if output_dirpath is not None else self.tts_data_folder

        self.tts_client = OpenAI()

    def _get_speech_response(self, 
                            text_input:str,
                            voice_name=None
                            ) -> object:
        if voice_name==None:
            voice_name = self.tts_voice

        self.logger.info(f"Starting speech create with params: input={text_input}, model={self.tts_model}, voice={self.tts_voice}")
        response = self.tts_client.audio.speech.create(
            model=self.tts_model, #low latency
            voice=voice_name,
            input=text_input)
        self.logger.info("Got response:")
        self.logger.info(response)
        return response
    
    def _write_speech_to_file(self,
                             response:object,
                             speech_file_path:str
                             ) -> None:
        self.logger.info("starting stream to speech file")
        response.stream_to_file(speech_file_path)
        self.logger.info(f"finished stream to speech file: {speech_file_path}")

    def workflow_t2s(self,
                     text_input,
                     voice_name,
                     output_filename=None,
                     output_dirpath=None):
        if output_filename is None:
            output_filename = self.output_filename
        if output_dirpath is None:
            output_dirpath = self.output_dirpath
        if voice_name is None:
            voice_name = self.tts_voice
            
        speech_file_path = os.path.join(os.getcwd(),output_dirpath, output_filename)
        
        response = self._get_speech_response(
            text_input=text_input,
            voice_name=voice_name
            )

        self._write_speech_to_file(
            response=response, 
            speech_file_path=speech_file_path
            )

if __name__ == "__main__":
    print(f"The use of __file__ for relative path traversal prevents this module from being run directly \
          but an exmaple of how to use is provided in {__name__}")

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