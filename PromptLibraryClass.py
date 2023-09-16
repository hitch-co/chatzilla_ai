import json
import PromptTypeEnum
import random

class PromptLibrary:    
    promptData = []

    def loadData(self, filePath: str):
        promptFile = open(filePath)

        self.promptData = json.load(promptFile)
    
    def GetPromptList(self, pType):
        returnIndex = []

        for p in self.promptData:            
            if int(p['MessageTypeID']) == pType.value:                
                returnIndex = p["PromptMessageList"]

        return returnIndex
    
    def GetRandomPrompt(self, pType):
        foundList = self.GetPromptList(pType)
        automsg_percent_chance_list = []
        automsg_prompts = []

        for promptItem in foundList:
            automsg_prompts.append(promptItem['Prompt'])
            automsg_percent_chance_list.append(promptItem['Weight'])
        
        weighted_prompt_choice_Final = random.choices(automsg_prompts, weights=automsg_percent_chance_list, k=1)[0]

        return weighted_prompt_choice_Final


                
                

        
