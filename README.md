# Book Information Enricher

This tool enriches a CSV file containing book titles and authors by adding publication dates, literary forms, reading levels, and word counts using OpenAI's API.

## What it does

Takes a simple CSV with book titles and authors, then uses AI to add detailed information like publication year, literary form (novel, poem, etc.), appropriate reading level, and estimated word count for each book.

## Files in this project

- **book_info_updater_v2.py** - Main program that processes the CSV file
- **Arumiyomis_1001_Books_v7.csv** - Input file containing book titles and authors
- **logs/** - Directory containing processing logs
- **gitignore/** - Directory for large files excluded from git

## How to run

1. Make sure you have Python 3.6+ installed
2. Set your OpenAI API key:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```
3. Install required packages:
   ```bash
   pip install openai tqdm colorama chardet --break-system-packages
   ```
4. Run the program:
   ```bash
   python book_info_updater_v2.py
   ```

## Options

- `--input filename.csv` - Use a different input file
- `--start 50` - Start from row 50 (useful if restarting)
- `--backup` - Create a backup of your original file
- `--quiet` - Less verbose output
- `--model gpt-3.5-turbo` - Use a different AI model
- `--delay 1.0` - Change delay between API calls

## Example

Input: `"To Kill a Mockingbird","Harper Lee"`
Output: `"To Kill a Mockingbird","Harper Lee","1960","Novel","High School","99121"`

The program processes one book at a time and saves progress automatically.