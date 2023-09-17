import PromptLibraryClass
import PromptTypeEnum

promptLibrary = PromptLibraryClass.PromptLibrary()

promptLibrary.loadData('config//prompts.json')


def CheckList(promptTypeInput):
    print ('\n\n' + str(promptTypeInput))
    standardItems = promptLibrary.GetPromptList(promptTypeInput)
    for msg in standardItems:
        print(msg)
    print ('\n\n 5 random Items')
    for i in range(0,5):
        randomPrompt = promptLibrary.GetRandomPrompt(promptTypeInput)
        print(randomPrompt)

CheckList(PromptTypeEnum.PromptType.Standard)

CheckList(PromptTypeEnum.PromptType.NonStandard)






