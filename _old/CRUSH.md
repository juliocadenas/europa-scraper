# CRUSH Development Guidelines

## Build Commands
- Build EXE: `python build_exe.py`
- Build Single EXE: `python build_single_exe.py`
- Build Optimized EXE: `python build_optimized_exe.py`

## Test Commands
- Run all tests: `python test_scraper.py`
- Run specific test: `python -m pytest tests/ -k "test_name"`

## Lint/Format Commands
- Install dependencies: `pip install -r requirements.txt`
- Check code: Manual review (no automated linting configured)

## Code Style Guidelines

### Imports
- Use absolute imports when possible
- Group imports in order: standard library, third-party, local
- Import modules at the top of files

### Formatting
- Follow PEP 8 style guide
- Use 4 spaces for indentation
- Limit lines to 100 characters
- Use meaningful variable names

### Types
- Use type hints for function parameters and return values
- Prefer specific types over generic ones

### Naming Conventions
- Use snake_case for functions and variables
- Use PascalCase for classes
- Use UPPER_CASE for constants

### Error Handling
- Use try/except blocks for expected exceptions
- Log errors with appropriate context
- Return meaningful error messages to users

## Module Structure
Follow the scraper module organization in `utils/scraper/`:
- controller.py: Main coordination
- browser_manager.py: Browser handling
- search_engine.py: Search functionality
- content_extractor.py: Content extraction
- text_processor.py: Text analysis
- result_manager.py: Result storage
- progress_reporter.py: Progress tracking
- url_utils.py: URL utilities

## Git
- Add `.crush` to `.gitignore`