import os
import openai

from classes.ConfigManagerClass import ConfigManager
from my_modules import my_logging

#TODO: SHould take a client as an argument
class GPTTextToSpeech:
    def __init__(self, tts_file_name=None, tts_data_folder=None):
        self.logger = my_logging.create_logger(
            debug_level='INFO', 
            logger_name='logger_GPTTextToSpeechClass', 
            mode='a', 
            stream_logs=True
            )
        
        # Create instance of configmanager
        self.config = ConfigManager(yaml_filepath='.\config', yaml_filename='config.yaml')

        # Initialize OpenAI client
        self.tts_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))      

        ##folder/file details
        self.config.tts_file_name = tts_file_name if tts_file_name is not None else self.config.tts_file_name 
        self.config.tts_data_folder = tts_data_folder if tts_data_folder is not None else self.config.tts_data_folder

    def _get_speech_response(self, 
                            text_input:str,
                            voice_name=None
                            ) -> object:
        if voice_name==None:
            voice_name = self.config.tts_voice

        self.logger.info(f"Starting speech create with params: input={text_input}, model={self.config.tts_model}, voice={self.config.tts_voice}")
        response = self.tts_client.audio.speech.create(
            model=self.config.tts_model, #low latency
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
                     tts_file_name=None,
                     tts_data_folder=None):
        if tts_file_name is None:
            tts_file_name = self.tts_file_name
        if tts_data_folder is None:
            tts_data_folder = self.tts_data_folder
        if voice_name is None:
            voice_name = self.config.tts_voice
            
        speech_file_path = os.path.join(os.getcwd(),tts_data_folder, tts_file_name)
        
        response = self._get_speech_response(
            text_input=text_input,
            voice_name=voice_name
            )

        self._write_speech_to_file(
            response=response, 
            speech_file_path=speech_file_path
            )

if __name__ == "__main__":
    print(f"The use of __file__ for relative path traversal prevents this module from being run directly but an exmaple of how to use is provided in tests/GPTTextToSpeech_main.py")