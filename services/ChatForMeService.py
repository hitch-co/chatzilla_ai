from my_modules.my_logging import create_logger
from my_modules import utils

# from classes.GPTAssistantManagerClass import GPTAssistantManager, GPTThreadManager, GPTResponseManager
from classes.ConfigManagerClass import ConfigManager

runtime_logger_level = 'INFO'
class ChatForMeService:
    def __init__(
            self,
            tts_client, # Check where this comes from, may be duplicative of gpt_client
            send_channel_message
            ):
        
        # Get Instance of Config
        self.config = ConfigManager.get_instance()

        # Set the send_channel_message method
        self.send_channel_message = send_channel_message

        self.logger = create_logger(
            dirname='log', 
            logger_name='logger_ChatForMeService', 
            debug_level=runtime_logger_level,
            mode='w',
            stream_logs=True,
            encoding='UTF-8'
            )

        # tts client
        self.tts_client = tts_client

    async def send_output_message_and_voice(
            self,
            text,
            incl_voice,
            voice_name
            ):
        """
        Asynchronously sends a text message and optionally plays a voice message.

        This internal method sends a text message to the specified channel and, if requested, generates and plays a voice message using the text-to-speech service.

        Parameters:
        - text (str): The text message to be sent.
        - incl_voice (str): Specifies whether to include voice output ('yes' or 'no').
        - voice_name (str): The name of the voice to be used in the text-to-speech service.
        """
        datetime_string = utils.get_datetime_formats()['filename_format']
        if incl_voice == 'yes':
            # Generate speech object and generate speech object/mp3
            output_filename = "chatforme_"+"_"+datetime_string+"_"+self.tts_client.tts_file_name
            self.tts_client.workflow_t2s(
                text_input=text,
                voice_name=voice_name,
                output_dirpath=self.tts_client.tts_data_folder,
                output_filename=output_filename
                )

        # TODO: Does this class need botclass injected simply to send messages? 
        await self.send_channel_message(text)

        if incl_voice == 'yes':
            self.tts_client.play_local_mp3(
                dirpath=self.tts_client.tts_data_folder, 
                filename=output_filename
                )
            

if __name__ == "__main__":
    yaml_filepath = r'C:\_repos\chatzilla_ai\config\config.yaml'
    # gpt_response = asyncio.run(main(yaml_filepath))
    # print(gpt_response)