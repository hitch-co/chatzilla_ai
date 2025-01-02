# TODO: Instructions for cloning:
- **Steps from clone**:
  0. Clone from repo 
  0. Update run_chatzilla-ai_dev.bat with...
    1. The yaml filename you created inside config/bot_user_configs/chatzilla_ai_example.yaml
    2. Desired port (leave as 3001 if you can)
    3. the folder location that you cloned the repo to
  0. update the .env file
    - After copying the template...
    - etc.
  0. Create miniconda environment named "openai_chatzilla_ai_env"
    1. lotum 
    2. ipdum
    3. delorum

- **Steps from launch**
  0. Select the game you are playing (leave null for random facts rather than game facts)
  0. Select the microphone you are using (for the !what and related commands.)  This will only prompt the first time you set it up, otherwise you'll have to update the value manually (.env `CHATZILLA_MIC_DEVICE_NAME`)
  0. 

# TODO: Adjust config manager to load env > yaml
- **Reason**: Allows the mmoving of all config values to .env (reduces user touchpoints on mirroring/dockerizing)

# TODO: Migrate `os.path.join` calls to `pathlib.Path`
- **Reason**: `pathlib.Path` offers more intuitive, cross-platform file handling.
- **Steps**:
  1. Search for all instances of `os.path.join`, `os.path.isfile`, `os.makedirs`, etc.
  2. Replace them with the equivalent `pathlib.Path` methods (e.g., `Path(...).joinpath(...)`, `Path(...).is_file()`, `Path(...).mkdir(parents=True, exist_ok=True)`, etc.).
  3. Double-check that relative/absolute path logic still works as intended.
- **Outcome**: Cleaner, more maintainable, and platform-agnostic code.

# TODO: Upgrade the 'returning users' FAISS feature
- **Reason**: The current implementation is repetitive and always picks the same answers
- **ideation**: It should probably not only look for relevant messages, but also look at the last interactions from the bot and the user to make a better decision on what sets of message sto return
- **difficulty**: This isn't handled directly by FAISS, so it might be a bit more complex

# TODO: Implement a good "callback" using FAISS
## Description
- **Steps**:
  1. Implement a callback function that uses FAISS to find the most similar messages to a given input.
  2. Use the callback function to return the most similar messages to the user.
  3. Test the callback function to ensure it works as expected.

