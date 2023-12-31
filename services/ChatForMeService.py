from datetime import datetime 
import asyncio

from my_modules.my_logging import create_logger
from my_modules import gpt

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
        prompt_text = gpt.prompt_text_replacement(
            gpt_prompt_text=prompt_text,
            replacements_dict = replacements_dict
            )
        
        prompt_listdict = gpt.make_string_gptlistdict(
            prompt_text=prompt_text,
            prompt_text_role='user'
            )
        gpt_response = gpt.openai_gpt_chatcompletion(messages_dict_gpt=prompt_listdict)
        return gpt_response
    
    async def chatforme_logic(self, ctx):
        """
        A Twitch bot command that interacts with OpenAI's GPT API.
        It takes in chat messages from the Twitch channel and forms a GPT prompt for a chat completion API call.
        """
        self.botclass.run_configuration()
        datetime_string = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Allows to call via twitch command or a direct call
        if ctx:
            self.logger.info("Conditions were met")
            request_user_name = ctx.message.author.name
        else:
            self.logger.info("Conditions were not met")
            request_user_name = "unknown"

        # Extract usernames from previous chat messages stored in chatforme_msg_history.
        users_in_messages_list_text = self.botclass.message_handler._get_string_of_users(usernames_list=self.botclass.message_handler.users_in_messages_list)

        #Select prompt from argument, build the final prompt textand format replacements
        formatted_gpt_chatforme_prompt = self.botclass.formatted_gpt_chatforme_prompts[self.botclass.args_chatforme_prompt_name]
        chatforme_prompt = self.botclass.formatted_gpt_chatforme_prompt_prefix + formatted_gpt_chatforme_prompt + self.botclass.formatted_gpt_chatforme_prompt_suffix
        replacements_dict = {
            "twitch_bot_username":self.botclass.twitch_bot_username,
            "num_bot_responses":self.botclass.num_bot_responses,
            "request_user_name":request_user_name,
            "users_in_messages_list_text":users_in_messages_list_text,
            "chatforme_message_wordcount":self.botclass.chatforme_message_wordcount
        }
        chatforme_prompt = gpt.prompt_text_replacement(
            gpt_prompt_text=chatforme_prompt,
            replacements_dict = replacements_dict
            )

        #TODO: GPTAssistant Manager #######################################################################
        messages_dict_gpt = gpt.combine_msghistory_and_prompttext(prompt_text = chatforme_prompt,
                                                              prompt_text_role='system',
                                                              msg_history_list_dict=self.botclass.message_handler.chatforme_msg_history,
                                                              combine_messages=False)
        
        gpt_response = gpt.openai_gpt_chatcompletion(messages_dict_gpt=messages_dict_gpt)
        gpt_response_clean = gpt.chatforme_gpt_response_cleanse(gpt_response)

        if self.botclass.args_include_sound == 'yes':
            # Generate speech object and create .mp3:
            output_filename = "chatforme_"+"_"+datetime_string+"_"+self.botclass.tts_file_name
            self.botclass.tts_client.workflow_t2s(text_input=gpt_response_clean,
                                            voice_name='onyx',
                                        output_dirpath=self.botclass.tts_data_folder,
                                        output_filename=output_filename)
        
        #send twitch message and generate/play local mp3 if applicable
        await self.botclass.channel.send(gpt_response_clean)

        if self.botclass.args_include_sound == 'yes':
            self.botclass.play_local_mp3(
                dirpath=self.botclass.tts_data_folder, 
                filename=output_filename
                )
            
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