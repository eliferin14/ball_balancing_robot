Always write comments in English
Avoid writing duplicated code
Always use the typing module and specify types
Use pydantic models whenever reading/writing JSON files, and whenever interacting with Zenoh messages
Never remove already existing comments
Always use logging or loguru. Never print()
Use ruff as formatter
Avoid creating huge source files. Prefer a modular approach with clean separation of concerns across files
If need to read/write a file, define the path in the paths.py file as constant and import it where needed