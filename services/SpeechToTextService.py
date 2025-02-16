import speech_recognition as sr
import asyncio

from my_modules.my_logging import create_logger

class SpeechToTextService:
    def __init__(self):
        self.recognizer = sr.Recognizer()

        self.logger = create_logger(
            debug_level='DEBUG',
            logger_name='logger_SpeechToTextService',
            mode='w',
            stream_logs=True
        )

        self.logger.info(f"Initialized SpeechToTextService")

    async def convert_audio_to_text(self, file_path):
        # Ensure the file is a .wav file
        if not file_path.endswith('.wav'):
            raise ValueError("This class only processes .wav files")

        # Load the .wav file
        with sr.AudioFile(file_path) as source:
            audio_data = self.recognizer.record(source)
            # Convert speech to text
            try:
                text = self.recognizer.recognize_google(audio_data)
                self.logger.info(f"Audio file converted to text: '{text}'")
                return text
            except sr.UnknownValueError:
                self.logger.error("Speech Recognition could not understand the audio")
                return "Speech Recognition could not understand the audio"
            except sr.RequestError as e:
                self.logger.error(f"Could not request results from Speech Recognition service; {e}")
                return f"Could not request results from Speech Recognition service; {e}"
            
def main():
    # Create an instance of the SpeechToTextConverter class
    stt = SpeechToTextService()

    # Convert the audio file to text
    filepath = r'C:\_repos\chatzilla_ai_dev\chatzilla_ai\assets\ears\latest_ears.wav'
    
    # Run async
    text = asyncio.run(stt.convert_audio_to_text(filepath))
    print(text)
    
if __name__ == "__main__":
    main()