#!/bin/python3

import numpy as np
import struct
import argparse
from time import time
from scipy.signal import hilbert, welch
from vdif_utilities import *

def process_chunk(data_chunk):
    """Apply Hilbert transform to the data chunk."""
    return hilbert(data_chunk)

def calculate_psd(transformed_data, fs, nperseg=1024):
    """Calculate the Power Spectral Density (PSD) using the Welch method."""
    freqs, psd = welch(transformed_data, fs=fs, nperseg=nperseg, return_onesided=False)
    return psd

def extract_samples(f, frames_in_sec, skip):
    """Extract the sample information including timetag and frame structure."""
    vdif_integ_sec_align(f)
    vdif_skip_seconds(f, skip)
    year_beg, doy_beg, sod_beg, hh_beg, mm_beg, ss_beg, FRAME = vdif_info_timetag_extractor(f, frames_in_sec)
    return year_beg, doy_beg, sod_beg, hh_beg, mm_beg, ss_beg, FRAME

def calculate_total_seconds(f, frame, frames_in_sec):
    """Calculate total seconds available in the VDIF file."""
    file_begin = f.tell()
    f.seek(0, 2)
    file_end = f.tell()
    f.seek(file_begin)
    total_size = float(file_end - file_begin)
    total_integer_seconds = int((total_size // frame['HEADER']['data_frame_len_bytes']) // frames_in_sec)
    return total_integer_seconds

def write_rdef_header(out_f, frame, year_beg, doy_beg, sod_beg, channel, total_samples_perchann, carrier_frequency, channel_frequency_offset):
    """Write the RDEF header to the output file."""
    RECORD_LABEL = 'RDEF'
    RECORD_VERSION_ID = 0
    STATION_ID = 'Wa'.encode()
    SPACECRAFT_ID = 0
    SAMPLE_SIZE = 16  # 16 bits per sample for complex numbers (2 * 8 bits)
    SAMPLE_RATE = int(total_samples_perchann)
    VALIDITY_FLAG = 0
    AGENCY_FLAG = 0
    RF_TO_IF_DOWNCONV = 0.0
    IF_TO_CHANNEL_DOWNCONV = float(carrier_frequency)  # Use single carrier frequency here
    TIMETAG_PICOSECOND = 0.0
    CHANN_ACCUM_PHASE = 0.0
    CHANN_PHASE_C0 = 0.0
    CHANN_PHASE_C1 = float(channel_frequency_offset)
    CHANN_PHASE_C2 = 0.0
    CHANN_PHASE_C3 = 0.0
    END_LABEL = -99999

    RECORD_LENGTH = int(176 + (total_samples_perchann * 4) / 8)  # 4 bits per sample (2 bits real + 2 bits imaginary)

    # Writing header information
    out_f.write(RECORD_LABEL.encode())
    out_f.write(struct.pack('<I', RECORD_LENGTH))
    out_f.write(struct.pack('<H', RECORD_VERSION_ID))
    out_f.write(STATION_ID.ljust(2, b'\x00'))
    out_f.write(struct.pack('<H', SPACECRAFT_ID))
    out_f.write(struct.pack('<H', SAMPLE_SIZE))
    out_f.write(struct.pack('<I', SAMPLE_RATE))
    out_f.write(struct.pack('<H', VALIDITY_FLAG))
    out_f.write(struct.pack('<H', AGENCY_FLAG))
    out_f.write(struct.pack('<d', RF_TO_IF_DOWNCONV))
    out_f.write(struct.pack('<d', IF_TO_CHANNEL_DOWNCONV))
    out_f.write(struct.pack('<H', year_beg))
    out_f.write(struct.pack('<H', doy_beg))
    out_f.write(struct.pack('<I', int(sod_beg)))
    out_f.write(struct.pack('<d', TIMETAG_PICOSECOND))
    out_f.write(struct.pack('<d', CHANN_ACCUM_PHASE))
    out_f.write(struct.pack('<d', CHANN_PHASE_C0))
    out_f.write(struct.pack('<d', CHANN_PHASE_C1))
    out_f.write(struct.pack('<d', CHANN_PHASE_C2))
    out_f.write(struct.pack('<d', CHANN_PHASE_C3))
    out_f.write(struct.pack('<d', 0) * 5)
    out_f.write(struct.pack('<I', 0) * 9)
    out_f.write(struct.pack('<i', END_LABEL))  # Write END_LABEL here

def write_interleaved_data(out_f, transformed_data):
    """Convert complex data to interleaved format and write it to the file."""
    real_part = (transformed_data.real * 32767).astype(np.int16)
    imag_part = (transformed_data.imag * 32767).astype(np.int16)
    interleaved_data = np.empty((len(real_part) + len(imag_part)), dtype=np.int16)
    interleaved_data[0::2] = real_part
    interleaved_data[1::2] = imag_part
    out_f.write(interleaved_data.tobytes())

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('filenames', nargs='+', help='Name of the file(s) to be processed.')
    parser.add_argument('-auxfile', type=str, help='Name of the auxiliary side file.')
    parser.add_argument('-skip', type=int, help='Seconds to skip from the beginning of the file.')
    parser.add_argument('-maxseconds', type=int, help='Max number of seconds to decode.')
    parser.add_argument('-channels', nargs='+', type=int, help='Channels to extract (first channel is "1").')

    args = parser.parse_args()

    filenames = args.filenames
    auxfile = args.auxfile
    skip = args.skip if args.skip is not None else 0
    maxseconds = args.maxseconds if args.maxseconds is not None else 1
    channels = args.channels

    print()
    print('--- vdif2rdef ---')
    print('Files to process:', filenames)

    # Load auxiliary file
    with open(auxfile, 'r') as aux_f:
        lines = aux_f.readlines()
        exec('\n'.join(lines))  # This will execute the code in the auxiliary file

    # Ensure CARRIER_FREQUENCY is a float and CHANNELS_FREQUENCY is a list
    if not isinstance(CARRIER_FREQUENCY, (int, float)) or not isinstance(CHANNELS_FREQUENCY, list):
        print("Error: CARRIER_FREQUENCY should be a float and CHANNELS_FREQUENCY should be a list.")
        exit(1)

    # Define CHANNEL_FREQUENCY_OFFSET if not already defined
    if 'CHANNEL_FREQUENCY_OFFSET' not in globals():
        CHANNEL_FREQUENCY_OFFSET = [0.0] * NUMBER_CHANNELS

    # Channels to extract
    channels_to_extract = range(FRAME['HEADER']['nchann']) if channels is None else [(int(k) - 1) for k in channels]

    for filename in filenames:
        with open(filename, "rb") as f:
            # Extract sample rate
            frames_in_sec = vdif_samplerate_extractor(f)

            # Extract timetag and header info
            year_beg, doy_beg, sod_beg, hh_beg, mm_beg, ss_beg, FRAME = extract_samples(f, frames_in_sec, skip)

            # Create empty binary file for each channel
            for i in channels_to_extract:
                outname_prd = '{}{:02}-{:02}{:03}{:02}{:02}{:02}.prd'.format(
                    PRD_NAME[:16], i + 1, int(str(year_beg)[-2:]), doy_beg, hh_beg, mm_beg, ss_beg)
                print(f'Creating {outname_prd} ...')
                with open(outname_prd, "wb") as outfile:
                    pass  # Create empty file

            # Total seconds in file (after manually skipped seconds)
            total_integer_seconds = calculate_total_seconds(f, FRAME, frames_in_sec)
            print(f'Total seconds in file (after skipping): {total_integer_seconds}')
            maxseconds = min(maxseconds, total_integer_seconds)

            # Check if auxfile has consistent number of channels with respect to vdif file
            print(f'Number of channels in VDIF file: {FRAME["HEADER"]["nchann"]}')
            if FRAME['HEADER']['nchann'] != NUMBER_CHANNELS:
                print(f'*** Error: Number of channels in auxiliary file {auxfile} does not match VDIF file.')
                exit()

            # Read data and extract samples
            for relative_sec in range(maxseconds):
                print(f'Reading second {relative_sec} of data...')
                mytime = time()
                FRAME_SEC = vdif_second_reader(f, frames_in_sec)
                channels_sample = FRAME_SEC['DATA']
                print(f'{time() - mytime} seconds to read one second of data.')

                # Apply Hilbert transform and Welch method to each channel
                for i in channels_to_extract:
                    print(f'Processing channel {i + 1} ...')
                    chunk_size = 1000000  # Adjust chunk size as needed
                    num_chunks = len(channels_sample[i]) // chunk_size
                    transformed_data = np.empty(len(channels_sample[i]), dtype=np.complex64)

                    for j in range(num_chunks):
                        start = j * chunk_size
                        end = start + chunk_size
                        transformed_data[start:end] = process_chunk(channels_sample[i][start:end])

                    # Handle any remaining data
                    start = num_chunks * chunk_size
                    if start < len(channels_sample[i]):
                        transformed_data[start:] = process_chunk(channels_sample[i][start:])

                    # Calculate Power Spectral Density (PSD) for the channel
                    print(f'Calculating PSD for channel {i + 1} ...')
                    psd = calculate_psd(transformed_data, fs=frames_in_sec)
                    # You might save or further process the PSD as needed.

                    channels_sample[i] = transformed_data

                # Write RDEF header and interleaved data for each channel
                for i in channels_to_extract:
                    outname_prd = '{}{:02}-{:02}{:03}{:02}{:02}{:02}.prd'.format(
                        PRD_NAME[:16], i + 1, int(str(year_beg)[-2:]), doy_beg, hh_beg, mm_beg, ss_beg)
                    with open(outname_prd, "ab") as out_f:
                        print(f'Writing second {relative_sec} of channel {i + 1} to {outname_prd} ...')
                        total_samples_perchann = len(channels_sample[i])
                        write_rdef_header(out_f, FRAME, year_beg, doy_beg, sod_beg, i + 1, total_samples_perchann, CARRIER_FREQUENCY, CHANNEL_FREQUENCY_OFFSET[i])
                        write_interleaved_data(out_f, channels_sample[i])
    print('Processing completed.')
