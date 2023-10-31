import ChatForMeSettingsClass

setting = ChatForMeSettingsClass.ChatForMeSettings()

setting.load_yaml(yaml_dirname='d:\\projects\\ehitch\\chatforme_bots\\config\\')

print("\n\nenv_filename=" + setting.env_filename);
print("\n\nserver_guild_id=" + str(setting.server_guild_id));

print('\n\nMessage Prompts:')
for msg in setting.automsg_prompt_lists:
    print(msg)


