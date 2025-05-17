#!/usr/bin/env python3
import re
import csv
import sys
import os
from datetime import datetime

def clean_text(text):
    """Remove all non-alphanumeric characters from text"""
    # Remove quotes and trim whitespace
    text = text.strip().replace('"', '')
    # Replace all non-alphanumeric characters (except spaces) with empty string
    return re.sub(r'[^a-zA-Z0-9 ]', '', text)

def process_author(author):
    """Process author names, removing first name if in LastName, FirstName format"""
    # Remove quotes
    author = author.replace('"', '')
    
    # Check if author is in "LastName, FirstName" format
    if ',' in author:
        # Split by comma and take only the first part (last name)
        parts = [part.strip() for part in author.split(',')]
        if len(parts) >= 1:
            # Return only the last name (before the comma)
            author = parts[0]
    
    # Clean the result
    return clean_text(author)

def process_csv(input_file, output_file):
    """Process the CSV file according to the requirements"""
    # List of encodings to try
    encodings = ['utf-8', 'latin-1', 'windows-1252', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            with open(input_file, 'r', encoding=encoding) as infile, \
                 open(output_file, 'w', encoding='utf-8', newline='') as outfile:
                
                print(f"Trying with encoding: {encoding}")
                writer = csv.writer(outfile)
                
                # Process each line
                for line in infile:
                    # Skip empty lines
                    if not line.strip():
                        continue
                    
                    # Split the line by the first comma
                    parts = line.split(',', 1)
                    
                    if len(parts) < 2:
                        # If there's no comma, just clean and write the line
                        cleaned_line = clean_text(line)
                        if cleaned_line:
                            writer.writerow([cleaned_line])
                    else:
                        title, author = parts
                        
                        # Clean title and author
                        cleaned_title = clean_text(title)
                        cleaned_author = process_author(author)
                        
                        # Write the cleaned data
                        writer.writerow([cleaned_title, cleaned_author])
            
            # If we get here, the file was successfully processed
            print(f"Successfully processed with encoding: {encoding}")
            return True
            
        except UnicodeDecodeError:
            # Try the next encoding
            continue
        except Exception as e:
            print(f"Error processing CSV with encoding {encoding}: {e}")
            # Try the next encoding
            continue
    
    # If we get here, none of the encodings worked
    print("Failed to process the file with any of the attempted encodings.")
    return False

def main():
    # File paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, "Arumiyomis_1001_Books_v7.csv")
    
    # Create timestamp for the output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(script_dir, f"Arumiyomis_1001_Books_clean_{timestamp}.csv")
    
    # Create a backup if it doesn't exist yet
    backup_file = os.path.join(script_dir, "Arumiyomis_1001_Books_v7.csv.bak")
    if not os.path.exists(backup_file):
        try:
            import shutil
            shutil.copy2(input_file, backup_file)
            print(f"Backup created at {backup_file}")
        except Exception as e:
            print(f"Warning: Could not create backup: {e}")
    
    # Process the file
    print(f"Processing {input_file}...")
    if process_csv(input_file, output_file):
        print(f"CSV processing complete. Output saved to {output_file}")
        
        # Option to replace the original file
        choice = input("Would you like to replace the original file with the cleaned version? (y/n): ")
        if choice.lower() == 'y':
            try:
                os.replace(output_file, input_file)
                print(f"Original file replaced with cleaned version.")
            except Exception as e:
                print(f"Error replacing file: {e}")
    else:
        print("CSV processing failed.")

if __name__ == "__main__":
    main()
