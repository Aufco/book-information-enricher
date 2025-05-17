# Book Information Enrichment Project

This project enhances a CSV file of books by querying the OpenAI API to retrieve additional information for each entry. The script processes the file line by line, overwriting each row with enriched book data.

## Features

- Processes books sequentially, one API call at a time
- Updates each line with Title, Author, Publication Date, Genre, Literary Form, and Reading Level
- Includes error handling with automatic retries
- Provides progress tracking with tqdm
- Logs all activity to both console and log file
- Configurable through command-line arguments
- Option to create backups and start from specific rows

## Prerequisites

- Python 3.6+
- OpenAI API key set as environment variable `OPENAI_API_KEY`
- WSL on Windows (optional)

## Installation

```bash
# Navigate to your project directory
cd ~/Projects/Books

# Install dependencies
sudo pip install openai tqdm --break-system-packages
```

## Usage

### Basic Usage

```bash
python book_info_updater_enhanced.py
```

This will process all books in the default file (`Arumiyomis_1001_Books_v7.csv`) using the GPT-4o model.

### Advanced Usage

```bash
python book_info_updater_enhanced.py --input my_books.csv --model gpt-3.5-turbo --start 50 --delay 1 --backup
```

### Command-line Arguments

- `--input`, `-i`: Input CSV file (default: `Arumiyomis_1001_Books_v7.csv`)
- `--model`, `-m`: OpenAI model to use (default: `gpt-4o`)
- `--start`, `-s`: Start processing from this row number (default: 1)
- `--delay`, `-d`: Delay between API calls in seconds (default: 0.5)
- `--backup`, `-b`: Create a backup of the original file

## Example

Input:
```
Aesop's Fables,Aesopus
```

Output:
```
Aesop's Fables,Aesopus,6th century BCE,Fables,Folklore,Easy
```

## Cost Considerations

- Using `gpt-4o` provides the most accurate results but costs more
- For lower cost, use `gpt-3.5-turbo` with the `--model` option
- The script processes 1318 rows, so be aware of potential API costs

## Troubleshooting

If the script stops before completion:
1. Check the logs in the `logs` directory
2. Restart the script from the last processed row using the `--start` option

Example for resuming from row 100:
```bash
python book_info_updater_enhanced.py --start 100 --backup
```

## Notes

- The API is prompted one at a time, and the next request is not sent until the current line is processed
- The script includes a delay between requests to avoid rate limits
- All original data is temporarily preserved in a temp file during processing
