#!/usr/bin/env python3
import os
import csv
import time
import logging
from tqdm import tqdm
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/book_updater.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")

client = OpenAI(api_key=api_key)

# Configuration
INPUT_FILE = "Arumiyomis_1001_Books_v7.csv"
TEMP_FILE = "temp_output.csv"
MODEL = "gpt-4o"  # You can change this to gpt-3.5-turbo to save costs
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

def create_prompt(title, author):
    """Create the API prompt for a book."""
    return [
        {"role": "system", "content": """
You are a helpful literary assistant. I will give you the title and author of a book. 
You must respond with one single line only in the following comma-separated format:
[Title],[Author],[Publication Date],[Genre],[Literary Form],[Reading Level]

Follow these rules exactly:
- Do not include any extra text, notes, or explanations.
- Do not add line breaks or labels.
- Use only one line of plain text.
- For the Reading Level, choose only one of the following:
  Easy, Medium, Hard, Adult, Advanced
- If any information is uncertain, make your best reasonable guess based on general knowledge.
        """},
        {"role": "user", "content": f"{title},{author}"}
    ]

def get_book_info(title, author, retry_count=0):
    """Query the OpenAI API for book information with retry logic."""
    try:
        messages = create_prompt(title, author)
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.3,  # Lower temperature for more consistent responses
            max_tokens=150    # Limit response length
        )
        
        # Extract the response content
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        logger.error(f"Error processing '{title}' by {author}: {str(e)}")
        
        if retry_count < MAX_RETRIES:
            logger.info(f"Retrying in {RETRY_DELAY} seconds... (Attempt {retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return get_book_info(title, author, retry_count + 1)
        else:
            logger.error(f"Failed to process '{title}' after {MAX_RETRIES} retries")
            return f"{title},{author},Unknown,Unknown,Unknown,Unknown"

def process_books():
    """Process each book in the CSV file and update it with enriched information."""
    try:
        # Count total number of rows for progress bar
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            total_rows = sum(1 for _ in f)
        
        logger.info(f"Found {total_rows} books to process")
        
        # Process file line by line
        with open(INPUT_FILE, 'r', encoding='utf-8') as input_file, \
             open(TEMP_FILE, 'w', encoding='utf-8', newline='') as temp_file:
            
            csv_reader = csv.reader(input_file)
            csv_writer = csv.writer(temp_file)
            
            for row_num, row in tqdm(enumerate(csv_reader, 1), total=total_rows, desc="Processing books"):
                if len(row) >= 2:
                    title = row[0].strip()
                    author = row[1].strip()
                    
                    logger.info(f"Processing book {row_num}/{total_rows}: '{title}' by {author}")
                    
                    # Get enriched book information
                    enriched_info = get_book_info(title, author)
                    
                    # Write to temp file
                    csv_writer.writerow([enriched_info])
                else:
                    logger.warning(f"Row {row_num} has insufficient data: {row}")
                    csv_writer.writerow(row)  # Write original row
                
                # Small delay to avoid API rate limits
                time.sleep(0.5)
        
        # Replace original file with the updated one
        os.replace(TEMP_FILE, INPUT_FILE)
        logger.info(f"Successfully updated all books in {INPUT_FILE}")
        
    except Exception as e:
        logger.error(f"An error occurred during processing: {str(e)}")
        if os.path.exists(TEMP_FILE):
            logger.info(f"Temp file '{TEMP_FILE}' was not deleted due to an error")

if __name__ == "__main__":
    logger.info("Starting book information enrichment process")
    process_books()
    logger.info("Book information enrichment process completed")
