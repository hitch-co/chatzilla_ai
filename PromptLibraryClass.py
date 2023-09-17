import json
import PromptListEnum
import random

class PromptLibrary:    
    prompt_lists = []

    def loadData(self, filePath: str):
        #filePath = 'config//prompts.json'
        print(f'FILEPATH: {filePath}')
        
        with open(filePath, "r") as file:
            print(type(file))
            self.prompt_lists = json.load(file)
            file.close

        #print(f'JSON prompt_lists:')
        #print(json.dumps(self.prompt_lists, indent=4))


    def GetPromptList(self, prompt_list_id):
        returnIndex = []

        #for each prompt message list in prompts.json
        for prompt_list in self.prompt_lists:            
            if int(prompt_list['MessageTypeID']) == prompt_list_id.value:                
                returnIndex = prompt_list["PromptMessageList"]

        #return the list of dictionaries containing prompts only
        return returnIndex


    def GetRandomPrompt(self, prompt_list_id):
        prompt_list_prompts = self.GetPromptList(prompt_list_id)
        automsg_percent_chance_list = []
        automsg_prompts = []

        print(f'LOG: Prompt item:')
        print(prompt_list_prompts)
        len(prompt_list_prompts)

        for promptItem in prompt_list_prompts:
            print(f'LOG: Prompt item: {promptItem}')
            automsg_prompts.append(promptItem['Prompt'])
            automsg_percent_chance_list.append(promptItem['Weight'])
        
        print(automsg_prompts)
        print(automsg_percent_chance_list)

        weighted_prompt_choice_Final = random.choices(automsg_prompts, 
                                                      weights=automsg_percent_chance_list, 
                                                      k=1)[0]

        return weighted_prompt_choice_Final


                
                

        
