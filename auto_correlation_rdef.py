#!/bin/python3

import numpy as np
import scipy.fftpack as fft
import argparse
import time

def read_rdef_file_in_chunks(filename, chunk_size=256*1024):
    """Reads an RDEF file in chunks and yields sample data as numpy arrays."""
    print(f"Reading file: {filename}...", end='', flush=True)
    start_time = time.time()
    try:
        with open(filename, "rb") as f:
            f.seek(176)
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                samples = np.frombuffer(data, dtype=np.int16).copy()
                yield samples
    except Exception as e:
        print(f"Error reading file {filename}: {e}")
    print(f" done. ({time.time() - start_time:.2f} seconds)")

def compute_autocorrelation_fft(data, fft_size=2048):
    """Compute the auto-correlation of the data using FFT."""
    print("Starting FFT-based auto-correlation computation...", end='', flush=True)
    start_time = time.time()
    try:
        data = data[:fft_size]
        data = data - np.mean(data)
        n = len(data)

        f_data = np.fft.fft(data, n=fft_size)
        psd = f_data * np.conjugate(f_data)
        autocorrelation = np.fft.ifft(psd).real[:n]
        autocorrelation /= autocorrelation[0]
    except Exception as e:
        print(f"Error during auto-correlation computation: {e}")
        return None
    print(f" done. ({time.time() - start_time:.2f} seconds)")
    return autocorrelation

def compute_frequency_spectrum(correlation, sample_rate):
    """Compute the one-sided frequency spectrum from the auto-correlation."""
    print("Computing frequency spectrum...", end='', flush=True)
    start_time = time.time()
    try:
        fft_size = len(correlation)
        spectrum = fft.fft(correlation)
        freq = fft.fftfreq(fft_size, d=1/sample_rate)

        positive_freq_indices = freq >= 0
        freq = freq[positive_freq_indices] / 1e6 # Convert to MHz
        spectrum = np.abs(spectrum[positive_freq_indices])
    except Exception as e:
        print(f"Error during frequency spectrum computation: {e}")
        return None, None
    print(f" done. ({time.time() - start_time:.2f} seconds)")
    return freq, spectrum

def save_spectrum_to_file(frequencies, amplitudes, filename):
    """Save the frequency spectrum to a file."""
    output_filename = f"{filename}_spectrum.txt"
    print(f"Saving spectrum to {output_filename}...", end='', flush=True)
    try:
        with open(output_filename, "w") as f:
            for freq, amp in zip(frequencies, amplitudes):
                f.write(f"{freq} {amp}\n")
    except Exception as e:
        print(f"Error saving file {output_filename}: {e}")
    print(f" done.")

def pad_autocorrelations(correlations):
    """Pad autocorrelations to the same length."""
    max_length = max(len(ac) for ac in correlations)
    padded_correlations = []
    for ac in correlations:
        if len(ac) < max_length:
            padded_ac = np.pad(ac, (0, max_length - len(ac)), 'constant')
        else:
            padded_ac = ac
        padded_correlations.append(padded_ac)
    return np.array(padded_correlations)

def process_rdef_files(files, sample_rate, chunk_size=256*1024):
    for i, filename in enumerate(files):
        print(f"\nProcessing file {filename} ({i + 1}/{len(files)})...")

        all_autocorrelations = []
        chunk_count = 0

        total_chunks = sum(1 for _ in read_rdef_file_in_chunks(filename, chunk_size))
        print(f"Total chunks to process: {total_chunks}")

        for chunk in read_rdef_file_in_chunks(filename, chunk_size):
            chunk_count += 1
            print(f"Processing chunk {chunk_count}/{total_chunks}...", end='', flush=True)
            autocorrelation = compute_autocorrelation_fft(chunk, fft_size=2048)
            if autocorrelation is None:
                print("Skipping chunk due to auto-correlation error.")
                continue
            all_autocorrelations.append(autocorrelation)
            print(" done.")

        if not all_autocorrelations:
            print(f"Skipping file {filename} due to errors.")
            continue

        padded_autocorrelations = pad_autocorrelations(all_autocorrelations)
        combined_autocorrelation = np.mean(padded_autocorrelations, axis=0)

        frequencies, amplitudes = compute_frequency_spectrum(combined_autocorrelation, sample_rate)
        if frequencies is None or amplitudes is None:
            print(f"Skipping file {filename} due to frequency spectrum computation error.")
            continue

        save_spectrum_to_file(frequencies, amplitudes, filename)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Compute auto-correlation and frequency spectrum of RDEF PRD files.')
    parser.add_argument('files', nargs='+', help='RDEF PRD files to process.')
    parser.add_argument('-sample_rate', type=int, default=64000000, help='Sample rate in Hz (default: 128 MHz)')
    parser.add_argument('-chunk_size', type=int, default=256*1024, help='Size of chunks to read from file (default: 256 KB)')
    args = parser.parse_args()
    process_rdef_files(args.files, args.sample_rate, args.chunk_size)
