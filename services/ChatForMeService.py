import asyncio

from classes.GPTTextToSpeechClass import GPTTextToSpeech

from my_modules.my_logging import create_logger
from my_modules import gpt
from my_modules import utils

runtime_logger_level = 'DEBUG'
class ChatForMeService:
    def __init__(
            self,
            botclass
            ):

        self.logger = create_logger(
            dirname='log', 
            logger_name='logger_ChatForMeService', 
            debug_level=runtime_logger_level,
            mode='w',
            stream_logs=True,
            encoding='UTF-8'
            )

        # TODO: configuration
        #
        #

        # bot class
        self.botclass = botclass

        # gpt text to speech class
        self.tts_service = GPTTextToSpeech(
            output_filename=self.botclass.tts_file_name,
            output_dirpath=self.botclass.tts_data_folder
        )

    async def _send_output_message_and_voice(
            self,
            text,
            incl_voice,
            voice_name
            ):
        datetime_string = utils.get_datetime_formats()['filename_format']
        if incl_voice == 'yes':
            # Generate speech object and create .mp3:
            output_filename = "chatforme_"+"_"+datetime_string+"_"+self.botclass.tts_file_name
            self.botclass.tts_client.workflow_t2s(
                text_input=text,
                voice_name=voice_name,
                output_dirpath=self.botclass.tts_data_folder,
                output_filename=output_filename
                )
            
        await self.botclass.channel.send(text)

        if incl_voice == 'yes':
            self.tts_service.play_local_mp3(
                dirpath=self.botclass.tts_data_folder, 
                filename=output_filename
                )
            
    async def make_singleprompt_gpt_response(
            self,
            prompt_text, 
            replacements_dict=None,
            incl_voice='yes',
            voice_name='onyx'
            ) -> str:
        try:
            prompt_text = gpt.prompt_text_replacement(
                gpt_prompt_text=prompt_text,
                replacements_dict = replacements_dict
                )
            
            prompt_listdict = gpt.make_string_gptlistdict(
                prompt_text=prompt_text,
                prompt_text_role='user'
                )
            gpt_response = gpt.openai_gpt_chatcompletion(messages_dict_gpt=prompt_listdict)
        
        except Exception as e:
            self.logger.error(f"Error occurred in 'chatforme': {e}")

        await self._send_output_message_and_voice(
            text=gpt_response,
            incl_voice=incl_voice,
            voice_name=voice_name
        )
        return gpt_response

    async def make_msghistory_gpt_response(
            self,
            prompt_text, 
            replacements_dict=None,
            msg_history=None,
            incl_voice='yes',
            voice_name='onyx'
            ) -> str:
        try:
            prompt_text = gpt.prompt_text_replacement(
                gpt_prompt_text=prompt_text,
                replacements_dict = replacements_dict
                )
            prompt_listdict = gpt.combine_msghistory_and_prompttext(
                prompt_text = prompt_text,
                prompt_text_role = 'user',
                msg_history_list_dict = msg_history,
                output_new_list=True
            )
            gpt_response = gpt.openai_gpt_chatcompletion(messages_dict_gpt=prompt_listdict)
    
        except Exception as e:
            self.logger.error(f"Error occurred in 'chatforme': {e}")    

        await self._send_output_message_and_voice(
            text=gpt_response,
            incl_voice=incl_voice,
            voice_name=voice_name
        )
        return gpt_response

async def main():
    class botclass:
        def __init__():
            botclass.tts_data_folder = "data\\tts"
            botclass.tts_file_name = "speech.mp3"
            print(botclass.tts_file_name)
    chatforme_service = ChatForMeService(botclass)
    gpt_response = await chatforme_service.make_singleprompt_gpt_response(
        prompt_text="hello how are you", 
        replacements_dict=None
        )
    return gpt_response

if __name__ == "__main__":
    gpt_response = asyncio.run(main())
    print(gpt_response)