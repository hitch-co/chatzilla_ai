# TODO: Migrate `os.path.join` calls to `pathlib.Path`
- **Reason**: `pathlib.Path` offers more intuitive, cross-platform file handling.
- **Steps**:
  1. Search for all instances of `os.path.join`, `os.path.isfile`, `os.makedirs`, etc.
  2. Replace them with the equivalent `pathlib.Path` methods (e.g., `Path(...).joinpath(...)`, `Path(...).is_file()`, `Path(...).mkdir(parents=True, exist_ok=True)`, etc.).
  3. Double-check that relative/absolute path logic still works as intended.
- **Outcome**: Cleaner, more maintainable, and platform-agnostic code.