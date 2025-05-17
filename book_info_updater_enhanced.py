#!/usr/bin/env python3
import os
import csv
import time
import logging
import argparse
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

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Enrich book data using OpenAI API')
    parser.add_argument('--input', '-i', default="Arumiyomis_1001_Books_v7.csv",
                        help='Input CSV file (default: Arumiyomis_1001_Books_v7.csv)')
    parser.add_argument('--model', '-m', default="gpt-4o",
                        help='OpenAI model to use (default: gpt-4o)')
    parser.add_argument('--start', '-s', type=int, default=1,
                        help='Start processing from this row number (default: 1)')
    parser.add_argument('--delay', '-d', type=float, default=0.5,
                        help='Delay between API calls in seconds (default: 0.5)')
    parser.add_argument('--backup', '-b', action='store_true',
                        help='Create a backup of the original file')
    return parser.parse_args()

class BookInfoUpdater:
    """Class to update book information using OpenAI API."""
    
    def __init__(self, args):
        """Initialize the updater with specified arguments."""
        self.input_file = args.input
        self.temp_file = f"temp_{self.input_file}"
        self.backup_file = f"{self.input_file}.bak"
        self.model = args.model
        self.start_row = args.start
        self.delay = args.delay
        self.create_backup = args.backup
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        
        # Initialize OpenAI client
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        self.client = OpenAI(api_key=api_key)
    
    def create_prompt(self, title, author):
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

    def get_book_info(self, title, author, retry_count=0):
        """Query the OpenAI API for book information with retry logic."""
        try:
            messages = self.create_prompt(title, author)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,  # Lower temperature for more consistent responses
                max_tokens=150    # Limit response length
            )
            
            # Extract the response content
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            logger.error(f"Error processing '{title}' by {author}: {str(e)}")
            
            if retry_count < self.max_retries:
                retry_seconds = self.retry_delay * (2 ** retry_count)  # Exponential backoff
                logger.info(f"Retrying in {retry_seconds} seconds... (Attempt {retry_count + 1}/{self.max_retries})")
                time.sleep(retry_seconds)
                return self.get_book_info(title, author, retry_count + 1)
            else:
                logger.error(f"Failed to process '{title}' after {self.max_retries} retries")
                return f"{title},{author},Unknown,Unknown,Unknown,Unknown"

    def process_books(self):
        """Process each book in the CSV file and update it with enriched information."""
        try:
            # Count total number of rows for progress bar
            with open(self.input_file, 'r', encoding='utf-8') as f:
                total_rows = sum(1 for _ in f)
            
            logger.info(f"Found {total_rows} books to process")
            
            # Create backup if requested
            if self.create_backup:
                import shutil
                shutil.copy2(self.input_file, self.backup_file)
                logger.info(f"Created backup at {self.backup_file}")
            
            # Process file line by line
            with open(self.input_file, 'r', encoding='utf-8') as input_file, \
                 open(self.temp_file, 'w', encoding='utf-8', newline='') as temp_file:
                
                csv_reader = csv.reader(input_file)
                csv_writer = csv.writer(temp_file)
                
                # Create a progress bar that starts from the specified row
                progress_bar = tqdm(
                    enumerate(csv_reader, 1), 
                    total=total_rows, 
                    desc="Processing books",
                    initial=self.start_row - 1 if self.start_row > 1 else 0
                )
                
                for row_num, row in progress_bar:
                    # Copy original rows until we reach the start row
                    if row_num < self.start_row:
                        csv_writer.writerow(row)
                        continue
                    
                    if len(row) >= 2:
                        title = row[0].strip()
                        author = row[1].strip()
                        
                        logger.info(f"Processing book {row_num}/{total_rows}: '{title}' by {author}")
                        
                        # Get enriched book information
                        enriched_info = self.get_book_info(title, author)
                        
                        # Parse enriched info and write as a CSV row
                        enriched_row = next(csv.reader([enriched_info]))
                        csv_writer.writerow(enriched_row)
                    else:
                        logger.warning(f"Row {row_num} has insufficient data: {row}")
                        csv_writer.writerow(row)  # Write original row
                    
                    # Small delay to avoid API rate limits
                    time.sleep(self.delay)
            
            # Replace original file with the updated one
            os.replace(self.temp_file, self.input_file)
            logger.info(f"Successfully updated all books in {self.input_file}")
            
        except Exception as e:
            logger.error(f"An error occurred during processing: {str(e)}")
            if os.path.exists(self.temp_file):
                logger.info(f"Temp file '{self.temp_file}' was not deleted due to an error")

def main():
    """Main entry point for the script."""
    args = parse_arguments()
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    logger.info("Starting book information enrichment process")
    logger.info(f"Using model: {args.model}")
    logger.info(f"Input file: {args.input}")
    logger.info(f"Starting from row: {args.start}")
    
    updater = BookInfoUpdater(args)
    updater.process_books()
    
    logger.info("Book information enrichment process completed")

if __name__ == "__main__":
    main()
