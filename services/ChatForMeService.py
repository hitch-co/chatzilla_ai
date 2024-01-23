import asyncio
import copy

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

    async def _send_output_message_and_voice(
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
            # Generate speech object and create .mp3:
            output_filename = "chatforme_"+"_"+datetime_string+"_"+self.botclass.tts_file_name
            
            # TODO: Does this class need botclass injected simply to get a tts_client??
            self.botclass.tts_client.workflow_t2s(
                text_input=text,
                voice_name=voice_name,
                output_dirpath=self.botclass.tts_data_folder,
                output_filename=output_filename
                )

        # TODO: Does this class need botclass injected simply to send messages? 
        await self.botclass.channel.send(text)

        if incl_voice == 'yes':
            self.botclass.tts_client.play_local_mp3(
                dirpath=self.botclass.tts_data_folder, 
                filename=output_filename
                )
            
    async def make_singleprompt_gpt_response(
            self,
            prompt_text, 
            replacements_dict=None,
            incl_voice='yes',
            voice_name='nova'
            ) -> str:
        """
        Asynchronously generates a GPT response for a single prompt.

        This method takes a single prompt, optionally applies replacements, and generates a response using the GPT model. It also handles sending the response and optionally playing the corresponding voice message.

        Parameters:
        - prompt_text (str): The text prompt to generate a response for.
        - replacements_dict (dict, optional): A dictionary of replacements to apply to the prompt text.
        - incl_voice (str): Specifies whether to include voice output ('yes' or 'no'). Default is 'yes'.
        - voice_name (str): The name of the voice to be used in the text-to-speech service. Default is 'nova'.

        Returns:
        - str: The generated GPT response.

        """
        try:
            prompt_text = gpt.prompt_text_replacement(
                gpt_prompt_text=prompt_text,
                replacements_dict = replacements_dict
                )
            
            prompt_listdict = gpt.make_string_gptlistdict(
                prompt_text=prompt_text,
                prompt_text_role='user'
                )
            try:
                gpt_response = gpt.openai_gpt_chatcompletion(messages_dict_gpt=prompt_listdict)
            except Exception as e:
                self.logger.error(f"Error occurred in 'openai_gpt_chatcompletion': {e}")        

        except Exception as e:
            self.logger.error(f"Error occurred in 'make_singleprompt_gpt_response': {e}")

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
            voice_name='nova'
            ) -> str: 
        """
        Asynchronously generates a GPT response considering message history.

        This method processes a prompt and an existing message history to generate a GPT response. It handles replacements in the prompt, merges the prompt with the message history, and manages the response and voice message output.

        Parameters:
        - prompt_text (str): The text prompt to generate a response for.
        - replacements_dict (dict, optional): A dictionary of replacements to apply to the prompt text.
        - msg_history (list[dict], optional): The existing message history to consider in response generation.
        - incl_voice (str): Specifies whether to include voice output ('yes' or 'no'). Default is 'yes'.
        - voice_name (str): The name of the voice to be used in the text-to-speech service. Default is 'nova'.

        Returns:
        - str: The generated GPT response.
        
        """
        self.logger.info(f"incl_voice: {incl_voice}")
        self.logger.info(f"prompt_text: {prompt_text}")
        self.logger.info(f"msg_history: {msg_history}")
        self.logger.info(f"replacements_dict: {replacements_dict}")

        try:
            prompt_text = gpt.prompt_text_replacement(
                gpt_prompt_text=prompt_text,
                replacements_dict = replacements_dict
                )
            prompt_listdict = self.combine_msghistory_and_prompttext(
                prompt_text = prompt_text,
                prompt_text_role = 'user',
                msg_history_list_dict = msg_history,
                output_new_list=True
            )
            try:
                gpt_response = gpt.openai_gpt_chatcompletion(messages_dict_gpt=prompt_listdict)
            except Exception as e:
                self.logger.error(f"Error occurred in 'chatforme': {e}")

        except Exception as e:
            self.logger.error(f"Error occurred in 'chatforme': {e}")    

        await self._send_output_message_and_voice(
            text=gpt_response,
            incl_voice=incl_voice,
            voice_name=voice_name
        )
        return gpt_response

    def combine_msghistory_and_prompttext(
            self,
            prompt_text,
            prompt_text_role='user',
            prompt_text_name='unknown',
            msg_history_list_dict=None,
            combine_messages=False,
            output_new_list=False
            ) -> list[dict]:
        """
        Combines message history with a new prompt text.

        This method merges a given prompt text with an existing message history. It supports customization of the prompt's role and can combine all messages into a single entry or keep them separate.

        Parameters:
        - prompt_text (str): The text of the new prompt to be merged.
        - prompt_text_role (str): The role associated with the prompt text ('user', 'assistant', or 'system'). Default is 'user'.
        - prompt_text_name (str): The name associated with the prompt text. Default is 'unknown'.
        - msg_history_list_dict (list[dict], optional): The existing message history list to merge with. Default is None.
        - combine_messages (bool): If True, combines all messages into a single entry. Default is False.
        - output_new_list (bool): If True, outputs a new list instead of modifying the existing one. Default is False.

        Returns:
        - list[dict]: A list of dictionaries representing the merged message history and prompt.

        """
        if output_new_list == True:
            msg_history_list_dict_temp = copy.deepcopy(msg_history_list_dict)
        else:
            msg_history_list_dict_temp = msg_history_list_dict

        if prompt_text_role == 'system':
            prompt_dict = {'role': prompt_text_role, 'content': f'{prompt_text}'}
        elif prompt_text_role in ['user', 'assistant']:
            prompt_dict = {'role': prompt_text_role, 'content': f'<<<{prompt_text_name}>>>: {prompt_text}'}

        if combine_messages == True:
            msg_history_string = " ".join(item["content"] for item in msg_history_list_dict_temp if item['role'] != 'system')
            reformatted_msg_history_list_dict = [{
                'role': prompt_text_role, 
                'content': msg_history_string
            }]
            reformatted_msg_history_list_dict.append(prompt_dict)
            msg_history_list_dict_temp = reformatted_msg_history_list_dict
            self.logger.debug(msg_history_list_dict_temp)
        else:
            msg_history_list_dict_temp.append(prompt_dict)
            self.logger.debug(msg_history_list_dict_temp)

        utils.write_json_to_file(
            data=msg_history_list_dict_temp, 
            variable_name_text='msg_history_list_dict_temp', 
            dirname='log/get_combine_msghistory_and_prompttext_combined', 
            include_datetime=False
        )
        return msg_history_list_dict_temp

    def make_string_gptlistdict(
            self,
            prompt_text, 
            prompt_text_role='user'
            ) -> list[dict]:
        
        prompt_listdict = [{'role': prompt_text_role, 'content': f'{prompt_text}'}]
        return prompt_listdict

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