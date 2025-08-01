# --- START OF FILE process_artist.py ---

# Does midi processing on a single artist (subdirectory)
# Converts subdirectory including a list of midi files into a .pt dataset 
# Dataset consists of inputs (non drum track) and outputs (drum track)
# Each input/output is a numpy matrix corresponding to one measure of one instrument of one track
# If there are multiple non drum instruments in one midi track, there will be one pair for each one
# This script is called from run_pipeline.sh orchestrator script

import argparse
import gc
import os

import sys
sys.stdout.reconfigure(line_buffering=True)

import numpy as np
import torch

# Assuming your helper functions are in a 'pp' package
from pp.helpers import count_measures, extract_measure, midi_to_velocity_matrix, split_midi_by_track_named

# The data_from_song_pipeline function remains unchanged.
# I'm including it here for completeness.

def data_from_song_pipeline(input_file=None, input_midi=None, to_file=False):
    """Processes a MIDI file into paired velocity matrices."""
    try:
        num_measures = count_measures(input_file=input_file, input_midi=input_midi)
    except Exception:
        return []

    all_data_pairs = []
    for measure_num in range(1, num_measures + 1):
        try:
            measure_midi = extract_measure(measure_num, input_file=input_file, input_midi=input_midi, to_file=False)
            split_tracks = split_midi_by_track_named(input_file=None, input_midi=measure_midi, to_file=False)
            if not split_tracks or split_tracks[-1] is None: continue
            
            drum_track = split_tracks[-1]
            drum_matrix = midi_to_velocity_matrix(input_midi=drum_track, x=64, to_file=False)

            for instrument_track in split_tracks[:-1]:
                if instrument_track is None: continue
                inst_matrix = midi_to_velocity_matrix(input_midi=instrument_track, x=64, to_file=False)
                if inst_matrix is None or inst_matrix.size == 0: continue
                all_data_pairs.append((inst_matrix, drum_matrix))
        except Exception:
            continue
    return all_data_pairs


def process_and_save_artist_incrementally(artist_folder_path: str, output_file_path: str):
    """
    Processes all MIDI files for an artist and saves the results incrementally
    to keep memory usage low.
    """
    artist_name = os.path.basename(artist_folder_path)
    midi_files = [f for f in os.listdir(artist_folder_path) if f.lower().endswith(('.mid', '.midi'))]
    
    if not midi_files:
        print(f"No MIDI files found for artist: {artist_name}")
        return

    print(f"Processing {len(midi_files)} songs for artist: {artist_name}")
    
    # This flag tracks if we've created the initial output file yet.
    file_created = False
    total_pairs = 0

    for i, filename in enumerate(midi_files):
        print(f"  - Song {i+1}/{len(midi_files)}: {filename}")
        file_path = os.path.join(artist_folder_path, filename)
        if not os.path.isfile(file_path):
            continue

        try:
            # 1. Process one song to get its data
            song_data = data_from_song_pipeline(input_file=file_path)
            
            if not song_data:
                print(f"    -> No valid pairs found.")
                continue

            # 2. Load, Extend, Save cycle
            if not file_created:
                # This is the first song with data, create the file.
                torch.save(song_data, output_file_path)
                file_created = True
                print(f"    -> Found {len(song_data)} pairs. Created new file.")
            else:
                # File already exists, perform the load-extend-save cycle.
                
                existing_data = torch.load(output_file_path, weights_only=False)
                existing_data.extend(song_data)
                torch.save(existing_data, output_file_path)
                
                # Explicitly free memory
                del existing_data
                print(f"    -> Found {len(song_data)} pairs. Appended to existing file.")

            total_pairs += len(song_data)
            del song_data
            gc.collect()

        except Exception as e:
            print(f"    -> CRITICAL ERROR processing song {filename}: {e}")
            # Continue to the next song to make the process resilient
            continue

    if total_pairs > 0:
        print(f"Finished artist {artist_name}. Total pairs extracted: {total_pairs}")
    else:
        print(f"Finished artist {artist_name}. No valid data was extracted.")


def main():
    parser = argparse.ArgumentParser(description="Process MIDI files for one artist with low memory usage.")
    parser.add_argument("--artist-dir", type=str, required=True, help="Path to the artist's MIDI directory.")
    parser.add_argument("--output-file", type=str, required=True, help="Path for the final .pt output file.")
    args = parser.parse_args()

    artist_name = os.path.basename(args.artist_dir)
    print(f"\n--- Starting processing for artist: {artist_name} ---")

    try:
        process_and_save_artist_incrementally(args.artist_dir, args.output_file)
    except Exception as e:
        print(f"!!! A fatal error occurred for artist {artist_name}: {e}")
        exit(1)

    print(f"--- Finished processing for artist: {artist_name} ---\n")

if __name__ == "__main__":
    main()