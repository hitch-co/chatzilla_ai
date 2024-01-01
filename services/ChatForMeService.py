import asyncio

from my_modules.my_logging import create_logger
from my_modules import gpt
from my_modules.text_to_speech import play_local_mp3

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

        # bot class
        self.botclass = botclass

    async def make_singleprompt_gpt_response(
            self,
            prompt_text, 
            replacements_dict=None
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

        await self.botclass.channel.send(gpt_response)

    async def make_msghistory_gpt_response(
            self,
            prompt_text, 
            replacements_dict=None,
            msg_history=None
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

        await self.botclass.channel.send(gpt_response)

async def main():
    botclass=None
    chatforme_service = ChatForMeService(botclass)
    gpt_response = await chatforme_service.make_singleprompt_gpt_response(
        prompt_text="hello how are you", 
        replacements_dict=None
        )
    return gpt_response

if __name__ == "__main__":
    gpt_response = asyncio.run(main())
    print(gpt_response)