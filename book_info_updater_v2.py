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
import sys
import colorama
from colorama import Fore, Style

# Initialize colorama for cross-platform colored terminal output
colorama.init()

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
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Minimal console output (hide detailed processing info)')
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

def print_header():
    """Print a formatted header for the application."""
    print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'Book Information Enrichment Tool':^80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")

def clear_current_line():
    """Clear the current line in the terminal."""
    sys.stdout.write('\r' + ' ' * 100)
    sys.stdout.write('\r')
    sys.stdout.flush()

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
        self.quiet_mode = args.quiet
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
You are a literary classifier. I will give you a book title and author. 
Respond with ONE SINGLE LINE in comma-separated format:
Publication Date,Literary Form,Reading Level,Word Count

Example for Animal Farm by Orwell: "1945,Novella,High School,29966"

Rules:
- Use ONLY English alphanumeric characters and spaces (no special characters)
- Use commas ONLY as field separators
- Choose ONE Literary Form from this list:
  Autobiography, Biography, Epic Poem, Folk Tale, Graphic Novel, Memoir, Novel, 
  Novella, NonFiction Novel, NonFiction Novella, Play, Poem, Satire, Short Story, Treatise
- Only use "Other Fiction" or "Other NonFiction" if the work truly doesn't fit any other category
- Choose ONE Reading Level from this list:
  Early Elementary, Upper Elementary, Middle School, High School, 
  College or Adult General, College or Adult Advanced, Academic or Scholarly
- For Word Count, provide the exact word count based on your training or an estimate if the exact count is unknown
"""
            },
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
            
            # Display the raw API response in the console if not in quiet mode
            if not self.quiet_mode:
                clear_current_line()
                print(f"{Fore.GREEN}[API Response]{Style.RESET_ALL} {api_response}")
            
            logger.info(f"API returned: {api_response}")
            
            # Clean the response
            cleaned_response = clean_text(api_response)
            
            return cleaned_response
        
        except Exception as e:
            logger.error(f"Error processing '{title}' by {author}: {str(e)}")
            
            if not self.quiet_mode:
                clear_current_line()
                print(f"{Fore.RED}[Error]{Style.RESET_ALL} {str(e)}")
            
            if retry_count < self.max_retries:
                retry_seconds = self.retry_delay * (2 ** retry_count)  # Exponential backoff
                logger.info(f"Retrying in {retry_seconds} seconds... (Attempt {retry_count + 1}/{self.max_retries})")
                
                if not self.quiet_mode:
                    print(f"{Fore.YELLOW}[Retry]{Style.RESET_ALL} Waiting {retry_seconds}s... ({retry_count + 1}/{self.max_retries})")
                
                time.sleep(retry_seconds)
                return self.get_book_info(title, author, retry_count + 1)
            else:
                logger.error(f"Failed to process '{title}' after {self.max_retries} retries")
                return "Unknown,Novel,College or Adult General,Unknown"

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
                print(f"{Fore.BLUE}[Info]{Style.RESET_ALL} Created backup at {self.backup_file}")
            
            # Process file line by line
            with open(self.input_file, 'r', encoding=self.encoding, errors='replace') as input_file, \
                 open(self.temp_file, 'w', encoding='utf-8', newline='') as temp_file:
                
                csv_reader = csv.reader(input_file)
                csv_writer = csv.writer(temp_file)
                
                # Create a progress bar that starts from the specified row
                progress_bar = tqdm(
                    enumerate(csv_reader, 1), 
                    total=row_count, 
                    desc=f"{Fore.CYAN}Processing{Style.RESET_ALL}",
                    initial=self.start_row - 1 if self.start_row > 1 else 0,
                    bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
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
                        
                        # Display the processing status with more detail if not in quiet mode
                        if not self.quiet_mode:
                            # Update progress bar description
                            progress_bar.set_description(f"{Fore.CYAN}Processing{Style.RESET_ALL} '{title}' by {author}")
                            
                            # Save cursor position
                            clear_current_line()
                            print(f"{Fore.BLUE}[Book {row_num}/{row_count}]{Style.RESET_ALL} '{title}' by {author}")
                        
                        # Get enriched book information
                        api_response = self.get_book_info(title, author)
                        
                        # Combine original title and author with API response
                        combined_row = [title, author] + api_response.split(',')
                        
                        # Display the final result if not in quiet mode
                        if not self.quiet_mode:
                            clear_current_line()
                            print(f"{Fore.GREEN}[Updated]{Style.RESET_ALL} {title},{author},{api_response}")
                        
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
            
            # Print completion message
            print(f"\n{Fore.GREEN}Success!{Style.RESET_ALL} Updated all books in {self.input_file}")
            
        except Exception as e:
            logger.error(f"An error occurred during processing: {str(e)}")
            print(f"\n{Fore.RED}Error:{Style.RESET_ALL} {str(e)}")
            
            if os.path.exists(self.temp_file):
                logger.info(f"Temp file '{self.temp_file}' was not deleted due to an error")
                print(f"{Fore.YELLOW}Note:{Style.RESET_ALL} Temp file '{self.temp_file}' was preserved for recovery")

def main():
    """Main entry point for the script."""
    args = parse_arguments()
    
    # Print header
    print_header()
    
    # Display configuration
    print(f"{Fore.BLUE}Configuration:{Style.RESET_ALL}")
    print(f"  Input file:  {args.input}")
    print(f"  Model:       {args.model}")
    print(f"  Starting at: Row {args.start}")
    print(f"  Delay:       {args.delay}s between API calls")
    print(f"  Backup:      {'Yes' if args.backup else 'No'}")
    print(f"  Mode:        {'Quiet' if args.quiet else 'Verbose'}\n")
    
    logger.info("Starting book information enrichment process")
    logger.info(f"Using model: {args.model}")
    logger.info(f"Input file: {args.input}")
    logger.info(f"Starting from row: {args.start}")
    
    updater = BookInfoUpdater(args)
    updater.process_books()
    
    logger.info("Book information enrichment process completed")
    print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Process completed successfully!{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Process interrupted by user.{Style.RESET_ALL}")
        logger.info("Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n{Fore.RED}Fatal error: {str(e)}{Style.RESET_ALL}")
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)
