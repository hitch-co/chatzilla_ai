import speech_recognition as sr

class SpeechToTextService:
    def __init__(self):
        self.recognizer = sr.Recognizer()

    def convert_audio_to_text(self, file_path):
        # Ensure the file is a .wav file
        if not file_path.endswith('.wav'):
            raise ValueError("This class only processes .wav files")

        # Load the .wav file
        with sr.AudioFile(file_path) as source:
            audio_data = self.recognizer.record(source)
            # Convert speech to text
            try:
                text = self.recognizer.recognize_google(audio_data)
                return text
            except sr.UnknownValueError:
                return "Google Speech Recognition could not understand the audio"
            except sr.RequestError as e:
                return f"Could not request results from Google Speech Recognition service; {e}"
            
def main():
    # Create an instance of the SpeechToTextConverter class
    stt = SpeechToTextService()

    filepath = r'C:\_repos\chatzilla_ai\data\ears\latest_ears.wav'
    # Convert the audio file to text
    print(stt.convert_audio_to_text(filepath))

if __name__ == "__main__":
    main()