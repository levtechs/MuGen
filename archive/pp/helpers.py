#helpers.py

import mido
from mido import MidiFile, MidiTrack, MidiFile
import numpy as np
import os
import datetime

from pp import dicts

def split_midi_by_track_named(input_file = None, input_midi: MidiFile = None, to_file=False):
    """
    Splits a MIDI file by track, identifying instruments and grouping notes accordingly.

    This function extracts individual instrument tracks from a MIDI file (excluding metadata),
    separates drum tracks (channel 9), and creates separate MIDI objects per instrument. Optionally,
    it can save each split track to individual MIDI files in a folder named after the original file.

    Parameters:
        input_file (str, optional): Path to the MIDI file to be split.
        input_midi (MidiFile, optional): Pre-loaded `mido.MidiFile` object.
        to_file (bool): If True, saves each resulting MIDI track to a separate file in a folder.

    Returns:
        List[MidiFile]: A list of `mido.MidiFile` objects, each containing one instrument. 
        The last element is always the drum track, or None if there was no drum tack found

    Raises:
        Exception: If neither `input_file` nor `input_midi` is provided.

    Notes:
        - Uses General MIDI instrument families from `dicts.FAMILIES` for naming.
        - Skips channel 9 tracks from the instrument loop and merges them into a single drum track.
        - Copies meta messages (like tempo and key signature) from the original global meta track (track 0).
        - Appends a numeric suffix (e.g., "_1") if multiple tracks use the same instrument name.
    """

    GM_PROGRAMS = dicts.FAMILIES

    if input_file:
        mid = MidiFile(input_file)
    elif input_midi:
        mid = input_midi
    else:
        raise ValueError("no input given")
    
    if to_file:
        # Create output folder
        try:
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            output_folder = os.path.join(".", base_name)
        except:
            base_name = (str)(datetime.datetime.now())
            output_folder = os.path.join(".", "outputs", base_name)

        os.makedirs(output_folder, exist_ok=True)

    global_meta_track = mid.tracks[0]
    instrument_counts = {}
    drum_track = MidiTrack()
    has_drum_data = False

    return_midis = []

    for _, track in enumerate(mid.tracks[1:], start=1):
        instrument_name = "Unknown"
        used_channels = set()

        for msg in track:
            if not msg.is_meta and hasattr(msg, 'channel'):
                used_channels.add(msg.channel)

        if 9 in used_channels:  # Drum track
            for msg in track:
                if not msg.is_meta and hasattr(msg, 'channel') and msg.channel == 9:
                    drum_track.append(msg.copy())
                    has_drum_data = True
            continue  # Skip writing this as a separate track
        else:
            for msg in track:
                if msg.type == 'program_change':
                    instrument_name = GM_PROGRAMS[msg.program] if msg.program < len(GM_PROGRAMS) else f"Program_{msg.program}"
                    break

            count = instrument_counts.get(instrument_name, 0)
            instrument_counts[instrument_name] = count + 1
            name_suffix = f"_{count}" if count > 0 else ""
            filename = f"{instrument_name.replace(' ', '_')}{name_suffix}.mid"
            new_mid = MidiFile(type=1)
            new_mid.ticks_per_beat = mid.ticks_per_beat

            meta_track = MidiTrack()
            for msg in global_meta_track:
                if msg.is_meta:
                    meta_track.append(msg.copy())
            new_mid.tracks.append(meta_track)

            new_track = MidiTrack()
            for msg in track:
                new_track.append(msg.copy())
            new_mid.tracks.append(new_track)

            return_midis.append(new_mid)

            if to_file:
                filepath = os.path.join(output_folder, filename)
                new_mid.save(filepath)
                print(f"Saved: {filepath}")

    # Save combined drum track, if any
    if has_drum_data:
        drum_mid = MidiFile(type=1)
        drum_mid.ticks_per_beat = mid.ticks_per_beat

        meta_track = MidiTrack()
        for msg in global_meta_track:
            if msg.is_meta:
                meta_track.append(msg.copy())
        drum_mid.tracks.append(meta_track)
        drum_mid.tracks.append(drum_track)

        return_midis.append(drum_mid)

        if to_file:
            drum_path = os.path.join(output_folder, "Drums.mid")
            drum_mid.save(drum_path)
            print(f"Saved: {drum_path}")
    else:
        return_midis.append(None)

    return return_midis

def count_measures(input_file=None, input_midi=None) -> int:
    """
    Estimates the lower bound on the number of measures in a MIDI file.

    Parameters:
        input_file (str, optional): Path to the input MIDI file.
        input_midi (MidiFile, optional): A pre-loaded MidiFile object.

    Returns:
        int: Estimated minimum number of measures in the file.

    Notes:
        - If both `input_file` and `input_midi` are provided, `input_file` takes precedence.
        - Time signature is read from track 0. If multiple changes are present, the smallest measure length is used.
        - Tempo is not relevant for measure counting.
        - The returned value is a lower bound; actual number may be higher if longer time signatures are used later.
    """
    if input_file:
        mid = MidiFile(input_file)
    elif input_midi:
        mid = input_midi
    else:
        raise ValueError("no input given")

    ticks_per_beat = mid.ticks_per_beat
    smallest_ticks_per_measure = None
    current_numerator = 4
    current_denominator = 4

    # Track time signature changes
    abs_tick = 0
    for msg in mid.tracks[0]:
        abs_tick += msg.time
        if msg.type == 'time_signature':
            current_numerator = msg.numerator
            current_denominator = msg.denominator
            # Calculate ticks per measure for this time signature
            beats_per_measure = current_numerator
            ticks_per_measure = beats_per_measure * ticks_per_beat
            if smallest_ticks_per_measure is None or ticks_per_measure < smallest_ticks_per_measure:
                smallest_ticks_per_measure = ticks_per_measure

    # If no time signature found, assume default 4/4
    if smallest_ticks_per_measure is None:
        smallest_ticks_per_measure = 4 * ticks_per_beat

    # Find the longest track to estimate total song length
    max_total_ticks = 0
    for track in mid.tracks:
        total_ticks = sum(msg.time for msg in track)
        if total_ticks > max_total_ticks:
            max_total_ticks = total_ticks

    return max_total_ticks // smallest_ticks_per_measure


def extract_measure(measure_num, input_file=None, input_midi=None, output_file=None, to_file=False) -> MidiFile:
    """
    Extracts a single measure from a MIDI file and returns it as a new MidiFile object,
    preserving all relevant musical context (e.g., tempo, time signature, instruments)
    by including meta and program change messages that occurred before the start of the measure.

    Parameters:
        measure_num (int): The measure number to extract (1-indexed).
        input_file (str, optional): Path to the input MIDI file.
        input_midi (MidiFile, optional): A pre-loaded MidiFile object.
        output_file (str, optional): Path to save the extracted measure. Only used if to_file=True.
        to_file (bool): If True, saves the extracted measure to a MIDI file.

    Returns:
        MidiFile: A new MidiFile object containing only the specified measure.

    Notes:
        - If both `input_file` and `input_midi` are provided, `input_file` takes precedence.
        - Tempo and time signature are assumed to be found in track 0. If not found, defaults are used:
            tempo = 500000 microseconds per beat (120 BPM),
            time signature = 4/4.
        - The returned MIDI file retains the same number of tracks as the original,
          with each track clipped to the specified measure and with essential meta/program messages preserved.
    """

    if input_file:
        mid = MidiFile(input_file)
    elif input_midi:
        mid = input_midi
    else:
        raise ValueError("no input given")

    ticks_per_beat = mid.ticks_per_beat

    # Defaults
    tempo = 500000  # microseconds per beat (120 bpm)
    numerator = 4
    denominator = 4

    time_sig_found = False
    tempo_found = False

    # Read global tempo and time signature (assume in track 0)
    abs_time = 0
    for msg in mid.tracks[0]:
        abs_time += msg.time
        if msg.type == 'time_signature' and not time_sig_found:
            numerator = msg.numerator
            denominator = msg.denominator
            time_sig_found = True
        elif msg.type == 'set_tempo' and not tempo_found:
            tempo = msg.tempo
            tempo_found = True
        if time_sig_found and tempo_found:
            break

    beats_per_measure = numerator
    ticks_per_measure = beats_per_measure * ticks_per_beat

    start_tick = (measure_num - 1) * ticks_per_measure
    end_tick = start_tick + ticks_per_measure

    # Prepare new midi file
    new_mid = MidiFile()
    new_mid.ticks_per_beat = ticks_per_beat

    for track in mid.tracks:
        abs_time = 0
        new_track = MidiTrack()
        new_mid.tracks.append(new_track)

        running_tick = 0
        buffered_msgs = []
        last_tick = 0

        for msg in track:
            running_tick += msg.time

            # Store messages before the measure that need to be preserved
            if running_tick < start_tick:
                if msg.is_meta and msg.type in ['track_name', 'set_tempo', 'time_signature', 'key_signature']:
                    buffered_msgs.append((running_tick, msg.copy()))
                elif not msg.is_meta and msg.type in ['program_change', 'control_change']:
                    buffered_msgs.append((running_tick, msg.copy()))
                continue

            if running_tick >= end_tick:
                break

            # If first message in the range, insert buffered messages with adjusted delta times
            if len(new_track) == 0:
                # Insert the preserved messages with correct delta timing
                buffered_msgs.sort(key=lambda x: x[0])
                prev_tick = 0
                for tick, m in buffered_msgs:
                    copy = m.copy()
                    copy.time = tick - prev_tick
                    new_track.append(copy)
                    prev_tick = tick

                # Now set msg.time to be correct relative to start_tick
                msg_copy = msg.copy()
                msg_copy.time = running_tick - start_tick
                new_track.append(msg_copy)
            else:
                new_track.append(msg.copy())

    if to_file:
        # Save output
        if output_file is None:
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            output_file = f"{base_name}_measure_{measure_num}.mid"

        new_mid.save(output_file)
        print(f"Saved: {output_file}")
    
    return new_mid


def midi_to_velocity_matrix(input_file=None, input_midi=None, x=128, fs=1000, to_file=False, output_path=None):
    """
    Converts a MIDI file object to a velocity matrix (piano roll) of size (128, x), where:
    - 128 is the number of MIDI pitches (notes)
    - x is the number of time steps
    """
    if input_file is None and input_midi is None:
        raise ValueError("Either input_file or input_midi must be provided")

    try:
        midi_data = mido.MidiFile(input_file) if input_file else input_midi
    except:
        raise ValueError("Unable to parse to MidiFile")

    notes = []
    is_drum = None
    for track in midi_data.tracks:
        for msg in track:
            if msg.type in ('note_on', 'note_off'):
                if not hasattr(msg, 'channel'):
                    continue
                drum_status = (msg.channel == 9)
                if is_drum is None:
                    is_drum = drum_status
                elif is_drum != drum_status:
                    raise ValueError("MIDI contains both drum and non-drum tracks")
                notes.append((msg.note, msg.velocity, msg.time, msg.type == 'note_on'))

    total_ticks = sum(msg[2] for msg in notes)
    tempo = getattr(midi_data, 'tempo', 500000)  # default 120 BPM
    ticks_per_second = midi_data.ticks_per_beat * (1_000_000 / tempo)
    total_time = total_ticks / ticks_per_second
    num_steps = int(total_time * fs)

    piano_roll_full = np.zeros((128, num_steps), dtype=np.int8)

    current_time = 0
    active_notes = {}

    for note, velocity, delta_time, is_note_on in notes:
        current_time += delta_time
        time_step = int((current_time / ticks_per_second) * fs)

        if is_note_on and velocity > 0:
            active_notes[note] = (time_step, velocity)
        elif note in active_notes:
            start_step, note_velocity = active_notes[note]
            end_step = time_step
            if start_step < end_step and 0 <= note < 128:
                piano_roll_full[note, start_step:end_step] = note_velocity
            del active_notes[note]

    # Final piano roll (shape: 128 x x)
    T = piano_roll_full.shape[1]
    if T >= x:
        piano_roll = piano_roll_full[:, :x]
    else:
        piano_roll = np.zeros((128, x), dtype=np.int8)
        piano_roll[:, :T] = piano_roll_full

    if to_file:
        if output_path is None:
            output_path = "./outputs/" + ('velocity_matrix.npy' if input_file is None else input_file + '_velocity.npy')
        np.save(output_path, piano_roll)

    return piano_roll