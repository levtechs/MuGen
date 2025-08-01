#!/bin/bash

# This script processes a directory of artist subfolders.
# It iterates through each subfolder, and for each one, it calls a Python script
# to generate a processed output file.

# 'set -e': Exit immediately if a command exits with a non-zero status.
# 'set -u': Treat unset variables as an error.
# 'set -o pipefail': The return value of a pipeline is the status of the last command to exit with a non-zero status.
set -euo pipefail

# --- Function to display usage information ---
usage() {
  echo "Usage: $0 <input_directory> [output_directory]"
  echo
  echo "Arguments:"
  echo "  <input_directory>   Path to the parent folder containing artist subfolders (e.g., ./cm_split)."
  echo "  [output_directory]  (Optional) Path to the folder where output files will be saved. Defaults to './outputs'."
  echo
  echo "Example:"
  echo "  $0 ./cm_split ./processed_files"
  exit 1
}

# --- 1. Argument Validation ---

# Check if the mandatory first argument is provided
if [[ $# -lt 1 ]]; then
  echo "Error: Missing required input directory argument."
  usage
fi

# Assign arguments to variables for clarity
# $1 is the first argument (input directory)
# $2 is the second argument (output directory). If it's not provided, default to "./outputs".
INPUT_DIR="$1"
OUTPUT_DIR="${2:-./outputs}"

# Check if the provided input directory actually exists
if [[ ! -d "$INPUT_DIR" ]]; then
  echo "Error: Input directory '$INPUT_DIR' not found."
  exit 1
fi

echo "--- Starting Artist Processing ---"
echo "Input Directory:   $INPUT_DIR"
echo "Output Directory:  $OUTPUT_DIR"
echo "--------------------------------"


# --- 2. Setup ---

echo "Activating venv..."
# This assumes the 'venv' is in the same directory you run the script from.
source "venv/bin/activate"

echo "Ensuring output directory '$OUTPUT_DIR' exists..."
# The -p flag creates the directory and any parent directories if they don't exist.
# It doesn't throw an error if the directory already exists.
mkdir -p "$OUTPUT_DIR"


# --- 3. Main Processing Loop ---

# Loop through all items in the specified INPUT_DIR
for folder in "$INPUT_DIR"/*; do
    # Process only if the item is a directory
    if [[ -d "$folder" ]]; then
        # Get just the name of the folder (e.g., "mc_1") from the full path
        artist_name=$(basename "$folder")
        
        # Construct the full path for the output file in the specified OUTPUT_DIR
        output_file="$OUTPUT_DIR/artist_${artist_name}.pt"
        
        echo ""
        echo "Processing artist folder: $artist_name"
        
        # Call the python script with the correct directory and file paths
        python3 process_artist.py --artist-dir "$folder" --output-file "$output_file"
        
        echo "Finished processing: $artist_name"
    fi
done

echo ""
echo "--------------------------------"
echo "✅ All artists processed successfully."