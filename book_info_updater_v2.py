#!/usr/bin/env python3
import os
import csv
import time
import logging
import argparse
from tqdm import tqdm
from openai import OpenAI
import chardet
import re

# Configure logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/book_updater_v2.log'),
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
    parser.add_argument('--encoding', '-e', default=None,
                        help='Force a specific encoding (e.g., latin-1, cp1252)')
    return parser.parse_args()

def detect_encoding(file_path):
    """Detect the encoding of a file using chardet."""
    with open(file_path, 'rb') as f:
        raw_data = f.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        confidence = result['confidence']
        logger.info(f"Detected encoding: {encoding} with confidence: {confidence:.2f}")
        return encoding

def clean_text(text):
    """Clean the API response text"""
    # Remove any brackets if they're present
    text = text.replace('[', '').replace(']', '')
    
    # Split by commas
    parts = text.split(',')
    
    # Clean each part individually (keeping spaces)
    cleaned_parts = [re.sub(r'[^a-zA-Z0-9 ]', '', part) for part in parts]
    
    # Rejoin with commas
    return ','.join(cleaned_parts)

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
        
        # Handle encoding
        self.encoding = args.encoding
        if not self.encoding:
            try:
                # Try to detect the encoding
                self.encoding = detect_encoding(self.input_file)
            except Exception as e:
                logger.warning(f"Error detecting encoding: {str(e)}. Falling back to latin-1")
                self.encoding = 'latin-1'  # Fallback to a permissive encoding
        
        logger.info(f"Using encoding: {self.encoding}")
        
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
You must respond with one single line only in the following comma-separated format without brackets:
Publication Date,Genre,Literary Form,Reading Level,Word Count

Example response format: "1925,Fiction,Novel,College or Adult General,95000"

Follow these rules exactly:
- Do not include any extra text, notes, or explanations.
- Do not add line breaks or labels.
- Use only one line of plain text.
- Do not include brackets in your response.
- Use only English alphanumeric characters in each field (commas are allowed as separators).
- Make your best reasonable guess for all fields, especially word count.

For Literary Form, choose ONLY ONE of the following:
Allegory, Autobiography, Biography, Epic, Essay, Fable, Fairy tale, Frame story, 
Graphic novel, Memoir, Novel, Novella, Philosophical dialogue, Play, Poem, 
Prose Poetry, Satire, Short Story, Treatise

For Reading Level, choose ONLY ONE of the following:
Early Elementary, Upper Elementary, Middle School, High School, 
College or Adult General, College or Adult Advanced, Academic or Scholarly
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
            api_response = response.choices[0].message.content.strip()
            
            # Display the raw API response in the console
            print(f"\n[API Response] {title} by {author}: {api_response}")
            logger.info(f"API returned: {api_response}")
            
            # Clean the response
            cleaned_response = clean_text(api_response)
            
            return cleaned_response
        
        except Exception as e:
            logger.error(f"Error processing '{title}' by {author}: {str(e)}")
            
            if retry_count < self.max_retries:
                retry_seconds = self.retry_delay * (2 ** retry_count)  # Exponential backoff
                logger.info(f"Retrying in {retry_seconds} seconds... (Attempt {retry_count + 1}/{self.max_retries})")
                time.sleep(retry_seconds)
                return self.get_book_info(title, author, retry_count + 1)
            else:
                logger.error(f"Failed to process '{title}' after {self.max_retries} retries")
                return "Unknown,Unknown,Novel,College or Adult General,Unknown"

    def process_books(self):
        """Process each book in the CSV file and update it with enriched information."""
        try:
            # Count total number of rows for progress bar
            row_count = 0
            try:
                with open(self.input_file, 'r', encoding=self.encoding, errors='replace') as f:
                    row_count = sum(1 for _ in f)
            except Exception as e:
                logger.error(f"Error counting rows: {str(e)}")
                row_count = 1318  # Default to the known number of rows
            
            logger.info(f"Found {row_count} books to process")
            
            # Create backup if requested
            if self.create_backup:
                import shutil
                shutil.copy2(self.input_file, self.backup_file)
                logger.info(f"Created backup at {self.backup_file}")
            
            # Process file line by line
            with open(self.input_file, 'r', encoding=self.encoding, errors='replace') as input_file, \
                 open(self.temp_file, 'w', encoding='utf-8', newline='') as temp_file:
                
                csv_reader = csv.reader(input_file)
                csv_writer = csv.writer(temp_file)
                
                # Create a progress bar that starts from the specified row
                progress_bar = tqdm(
                    enumerate(csv_reader, 1), 
                    total=row_count, 
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
                        
                        logger.info(f"Processing book {row_num}/{row_count}: '{title}' by {author}")
                        
                        # Display the processing status with more detail
                        print(f"\n[Processing {row_num}/{row_count}] '{title}' by {author}")
                        
                        # Get enriched book information
                        api_response = self.get_book_info(title, author)
                        
                        # Combine original title and author with API response
                        combined_row = [title, author] + api_response.split(',')
                        
                        # Display the final result
                        print(f"[Updated] {','.join(combined_row)}")
                        
                        # Write the combined row
                        csv_writer.writerow(combined_row)
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
    
    logger.info("Starting book information enrichment process")
    logger.info(f"Using model: {args.model}")
    logger.info(f"Input file: {args.input}")
    logger.info(f"Starting from row: {args.start}")
    
    updater = BookInfoUpdater(args)
    updater.process_books()
    
    logger.info("Book information enrichment process completed")

if __name__ == "__main__":
    main()
