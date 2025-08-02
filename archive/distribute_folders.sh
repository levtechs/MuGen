#!/bin/bash

# A script to evenly distribute the contents (files/folders) of a source directory
# into a specified number of new subdirectories.

# This was used to split clean_midi into smaller subdirectories to break down the preprocessing task. 

# --- Function to display usage information ---
usage() {
  echo "Usage: $0 <source_directory> <num_splits> [output_directory_name] [split_prefix]"
  echo
  echo "Arguments:"
  echo "  <source_directory>      Path to the folder whose contents will be distributed."
  echo "  <num_splits>            The number of new folders to create."
  echo "  [output_directory_name] (Optional) Name for the main output folder. Defaults to 'split_output'."
  echo "  [split_prefix]          (Optional) Prefix for the new numbered folders. Defaults to 'split'."
  echo
  echo "Example (based on your request):"
  echo "  $0 midi_clean 100 mc_split mc"
  exit 1
}

# --- 1. Argument Validation ---

# Check for the two mandatory arguments
if [[ $# -lt 2 ]]; then
  echo "Error: Missing required arguments."
  usage
fi

SOURCE_DIR="$1"
NUM_SPLITS="$2"
# Set default values for optional arguments if they are not provided
OUTPUT_DIR="${3:-split_output}"
SPLIT_PREFIX="${4:-split}"

# Verify that the source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
  echo "Error: Source directory '$SOURCE_DIR' not found."
  exit 1
fi

# Verify that the number of splits is a positive integer
if ! [[ "$NUM_SPLITS" =~ ^[1-9][0-9]*$ ]]; then
  echo "Error: Number of splits must be a positive integer."
  exit 1
fi

# --- 2. Preparation ---

echo "--- Starting Distribution ---"
echo "Source:           $SOURCE_DIR"
echo "Number of splits: $NUM_SPLITS"
echo "Output folder:    $OUTPUT_DIR"
echo "Split prefix:     $SPLIT_PREFIX"
echo "-----------------------------"

# Create the main output directory. The -p flag prevents errors if it already exists.
mkdir -p "$OUTPUT_DIR"

# Get a list of all files and folders directly inside the source directory.
# Using 'mapfile' is safer than a simple 'for loop' for filenames with spaces.
# 'find ... -maxdepth 1' ensures we only get the direct children.
# 'find ... -mindepth 1' excludes the source directory itself from the list.
echo "Scanning contents of '$SOURCE_DIR'..."
mapfile -t items < <(find "$SOURCE_DIR" -maxdepth 1 -mindepth 1)

total_items=${#items[@]}

if (( total_items == 0 )); then
  echo "Warning: Source directory '$SOURCE_DIR' is empty. Nothing to do."
  exit 0
fi

echo "Found $total_items items to distribute."

# --- 3. Calculation for Even Distribution ---

# Perform integer division to find the base number of items per folder
items_per_folder=$(( total_items / NUM_SPLITS ))
# Find the remainder to distribute one-by-one to the first few folders
remainder=$(( total_items % NUM_SPLITS ))

echo "Base distribution: $items_per_folder items per folder."
if (( remainder > 0 )); then
  echo "The first $remainder folders will receive one extra item to ensure evenness."
fi

# --- 4. The Distribution Loop ---

current_item_index=0
for (( i=1; i<=NUM_SPLITS; i++ )); do
  # Define the name of the new subfolder (e.g., mc_1, mc_2)
  dest_subfolder="$OUTPUT_DIR/${SPLIT_PREFIX}_${i}"
  mkdir -p "$dest_subfolder"

  # Determine how many items to move into this specific folder
  num_to_move=$items_per_folder
  if (( i <= remainder )); then
    num_to_move=$(( items_per_folder + 1 ))
  fi

  # If there are no items to move to this folder, just continue
  if (( num_to_move == 0 )); then
    echo "Skipping empty folder: $dest_subfolder"
    continue
  fi

  # Get the specific slice of items from our main list to be moved
  items_to_move=("${items[@]:current_item_index:num_to_move}")

  echo "Moving $num_to_move items into '$dest_subfolder'..."

  # Move the items. 'mv -t' is efficient as it specifies the target directory first.
  # This moves the items from their original location into the new folder.
  # NOTE: To COPY instead of MOVE, change `mv` to `cp -r`.
  cp -r -t "$dest_subfolder" "${items_to_move[@]}"

  # Update our position in the main item list
  current_item_index=$(( current_item_index + num_to_move ))
done

echo "-----------------------------"
echo "✅ Distribution complete!"
echo "All items have been moved to subfolders inside the '$OUTPUT_DIR' directory."