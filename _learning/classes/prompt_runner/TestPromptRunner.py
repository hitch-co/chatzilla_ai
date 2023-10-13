import PromptListEnum
import PromptLibraryClass

promptLibrary = PromptLibraryClass.PromptLibrary()

promptLibrary.loadData('config//prompts.json')


def CheckList(prompt_list_id):
    print ('\n\n' + str(prompt_list_id))
    standardItems = promptLibrary.GetPromptList(prompt_list_id)
    for msg in standardItems:
        print(msg)
    print ('\n\n 5 random Items')

    randomPrompt = promptLibrary.GetRandomPrompt(prompt_list_id)
    print(randomPrompt)
    # for i in range(0,5):
    #     randomPrompt = promptLibrary.GetRandomPrompt(prompt_list_id)
    #     print(randomPrompt)

#call checklist with a value from the PromptTypeEnum.py
CheckList(PromptListEnum.PromptList.Standard)

#CheckList(PromptListEnum.PromptList.NonStandard)