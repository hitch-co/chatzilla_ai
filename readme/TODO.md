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

