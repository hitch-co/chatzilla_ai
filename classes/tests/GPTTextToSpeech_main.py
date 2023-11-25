from classes import GPTTextToSpeechClass

tts_file_name = 'speech.mp3'
tts_data_folder = 'data\\tts'
#speech_file_path = Path(__file__).parent.parent / output_dirname / output_filename
text_input="hello how are you?  My name is nova and I'm watching ehitch's stream"

#Create client
tts_client = GPTTextToSpeechClass.GPTTextToSpeech(
    tts_file_name=tts_file_name,
    tts_data_folder=tts_data_folder
    )

# #write_speech_to_file:
tts_client.workflow_t2s(
    voice_name='shimmer',
    tts_file_name = tts_file_name,
    tts_data_folder=tts_data_folder,
    text_input=text_input
    )