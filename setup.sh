#!/usr/bin/env bash

# Create required directories
mkdir -p logs gitignore

# Install dependencies
echo "Installing required Python packages..."
sudo pip install openai tqdm chardet --break-system-packages

# Check for OpenAI API key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Warning: OPENAI_API_KEY environment variable is not set."
    echo "Please set it in your ~/.bashrc file with the following command:"
    echo "echo 'export OPENAI_API_KEY=\"your-api-key\"' >> ~/.bashrc && source ~/.bashrc"
fi

# Make scripts executable
chmod +x book_info_updater_v2.py

echo "Setup complete!"
echo "You can now run the script with: ./book_info_updater_v2.py"
