#!/bin/python3

import numpy as np
import struct
import sys

def ibits(value, position, length):
    return (value >> position) & ~(-1 << length)

def reverse_bit(value):
    result = 0
    while value:
        result = (result << 1) + (value & 1)
        value >>= 1
    return result

def set_bit(value, bit):
    return value | (1 << bit)

def clear_bit(value, bit):
    return value & ~(1 << bit)

def get_bit(value, bit):
    return (value & (1 << bit)) != 0

def vdif_frame_reader(file, skip_data=True):
    # Read HEADER
    word0 = struct.unpack('<I', file.read(4))[0]
    word1 = struct.unpack('<I', file.read(4))[0]
    word2 = struct.unpack('<I', file.read(4))[0]
    word3 = struct.unpack('<I', file.read(4))[0]

    # WORD0
    legacy_mode = get_bit(word0, 30)  # Bool
    invalid_data = get_bit(word0, 31)  # Bool
    seconds_from_epoch = ibits(word0, 0, 30)  # int

    # WORD1
    data_frame_n = ibits(word1, 0, 24)  # int
    reference_epoch = ibits(word1, 24, 6)  # int

    # WORD2
    data_frame_len_8bytes = ibits(word2, 0, 24)  # int
    log2nchann = ibits(word2, 24, 5)  # int
    vdif_version = ibits(word2, 29, 3)  # int

    # WORD3
    stationID = chr(ibits(word3, 0, 8)) + chr(ibits(word3, 8, 16))  # string
    threadID = ibits(word3, 16, 10)
    bit_sample_min1 = ibits(word3, 26, 5)
    data_type = get_bit(word3, 31)  # 0 real, 1 complex

    header_size_bytes = 16
    if not legacy_mode:
        word4 = struct.unpack('<I', file.read(4))[0]
        word5 = struct.unpack('<I', file.read(4))[0]
        word6 = struct.unpack('<I', file.read(4))[0]
        word7 = struct.unpack('<I', file.read(4))[0]
        header_size_bytes = 32

    data_frame_len_bytes = data_frame_len_8bytes * 8
    nchann = 2 ** log2nchann
    bit_sample = bit_sample_min1 + 1

    # DATA EXTRACTION
    n32bitwords = (data_frame_len_bytes - header_size_bytes) // 4  # each read word is 4 bytes
    total_samples_bits = (data_frame_len_bytes - header_size_bytes) * 8
    total_samples_perchann = total_samples_bits // bit_sample  # 4000 samples with 2bit/sample, 8chann, 8000bytes data frame

    # bit_sample= 2 [bit/sample] specific:
    samples_per_32bitword = 32 // bit_sample  # 16 samples of 2bit in a word

    channels_sample = [None] * nchann
    samples = [None] * total_samples_perchann * nchann
    index = 0

    for counter in range(n32bitwords):  # Main cycle on all the sample data field
        iword32 = struct.unpack('<I', file.read(4))[0]
        if not skip_data:
            for jj in range(samples_per_32bitword):  # 0-15
                i_magn = ibits(iword32, jj * bit_sample, bit_sample - 1)
                i_sign = ibits(iword32, ((jj + 1) * bit_sample) - 1, 1)  # magn (bit0) sign(bit1) | magn(bit2) sign ... we encounter firstly the magn bit
                if bit_sample != 2:
                    print('*** DECODING IMPOSSIBLE, WRONG SAMPLING RATE: ', bit_sample)
                    sys.exit()
                if i_sign == 1:  # !coding: -3 -1 1 3 -> signmagn 00 01 10 11
                    samples[index] = i_magn * 2 + 1
                else:
                    samples[index] = i_magn * 2 - 3
                index += 1
            # Extract
            for i in range(nchann):
                channels_sample[i] = samples[i::nchann]  # one element every nchann elements

    FRAME_HEADER = {'legacy_mode': legacy_mode,
                    'invalid_data': invalid_data,
                    'seconds_from_epoch': seconds_from_epoch,
                    'data_frame_n': data_frame_n,
                    'reference_epoch': reference_epoch,
                    'data_frame_len_bytes': data_frame_len_bytes,
                    'nchann': nchann,
                    'vdif_version': vdif_version,
                    'stationID': stationID,
                    'threadID': threadID,
                    'bit_sample': bit_sample,
                    'data_type': data_type,
                    'header_size_bytes': header_size_bytes}

    FRAME_DATA = channels_sample

    FRAME = {"HEADER": FRAME_HEADER,
             "DATA": FRAME_DATA}
    return FRAME

def vdif_integ_sec_align(file):
    # file -> in main, "with open() as file:"
    frames_read = 0
    while True:
        offset_position = file.tell()
        # READ HEADER AND DATA FIELDS
        word0 = struct.unpack('<I', file.read(4))[0]
        word1 = struct.unpack('<I', file.read(4))[0]
        word2 = struct.unpack('<I', file.read(4))[0]
        word3 = struct.unpack('<I', file.read(4))[0]

        legacy_mode = get_bit(word0, 30)  # Bool
        data_frame_n = ibits(word1, 0, 24)  # int
        data_frame_len_8bytes = ibits(word2, 0, 24)  # int

        header_size_bytes = 16
        if not legacy_mode:
            word4 = struct.unpack('<I', file.read(4))[0]
            word5 = struct.unpack('<I', file.read(4))[0]
            word6 = struct.unpack('<I', file.read(4))[0]
            word7 = struct.unpack('<I', file.read(4))[0]
            header_size_bytes = 32

        data_frame_len_bytes = data_frame_len_8bytes * 8
        n32bitwords = (data_frame_len_bytes - header_size_bytes) // 4  # each read word is 4 bytes

        for i in range(n32bitwords):
            temp = struct.unpack('<I', file.read(4))[0]

        frames_read += 1

        if data_frame_n == 0:
            file.seek(offset_position)
            frames_read -= 1
            return frames_read

def vdif_samplerate_extractor(file):
    file_position = file.tell()

    print('Sample rate extraction:')
    vdif_integ_sec_align(file)
    vdif_frame_reader(file)
    frames_in_sec = vdif_integ_sec_align(file)
    frames_in_sec += 1
    print('Computed frames per second: ', frames_in_sec)

    file.seek(file_position)
    return frames_in_sec

def vdif_timedecode(FRAME, frames_in_sec):
    mjdepoch = [51544, 51726, 51910, 52091, 52275, 52456, 52640, 52821, \
                53005, 53187, 53371, 53552, 53736, 53917, 54101, 54282, \
                54466, 54648, 54832, 55013, 55197, 55378, 55562, 55743, \
                55927, 56109, 56293, 56474, 56658, 56839, 57023, 57204, \
                57388, 57570, 57754, 57935, 58119, 58300, 58484, 58665, \
                58849, 59031, 59215, 59396, 59580, 59761, 59945, 60126, \
                60310, 60492, 60676, 60857, 61041, 61222, 61406, 61587, \
                61771, 61953, 62137, 62318, 62502, 62683, 62867, 63048]

    year = 2000 + int(FRAME['HEADER']['reference_epoch'] / 2)

    doy = int(FRAME['HEADER']['seconds_from_epoch'] / 86400) + 1  # "+1" to start from DOY=001
    mjd = mjdepoch[FRAME['HEADER']['reference_epoch'] + 1] + doy - 1  # "-1" since DOY starts from 1 instead of 0

    leap_year = (year % 4) == 0

    if (FRAME['HEADER']['reference_epoch'] % 2) == 1:
        doy += 181  # first semester without 29 February
        if leap_year:
            doy += 1  # add 1 day to account for 29 February in doy

    sod_integer = FRAME['HEADER']['seconds_from_epoch'] - int(FRAME['HEADER']['seconds_from_epoch'] / 86400.0) * 86400  # integer second of day

    fractional_part = FRAME['HEADER']['data_frame_n'] / float(frames_in_sec)
    sod = sod_integer + fractional_part  # real second of day

    hh = int(sod / 3600.0)
    diff = sod - 3600.0 * hh
    mm = int(diff / 60.0)
    diff2 = diff - 60.0 * mm
    ss = int(np.rint(diff2))
    return year, doy, sod, hh, mm, ss

def vdif_info_timetag_extractor(file, frames_in_sec):
    print('Timetag extraction:')
    file_position = file.tell()
    FRAME = vdif_frame_reader(file)
    file.seek(file_position)
    year, doy, sod, hh, mm, ss = vdif_timedecode(FRAME, frames_in_sec)
    print('{:04} {:03} {}'.format(year, doy, sod), '{:02}:{:02}:{:02}'.format(hh, mm, ss))
    return year, doy, sod, hh, mm, ss, FRAME

def vdif_skip_seconds(file, skip):
    for i in range(skip):
        FRAME = vdif_frame_reader(file)
        vdif_integ_sec_align(file)
        print('Skipped second {}'.format(i + 1))

def vdif_second_reader(file, frames_in_sec):
    # file -> in main, "with open() as file:"

    for k in range(frames_in_sec):
        if k == 0:
            # HEADER
            word0 = struct.unpack('<I', file.read(4))[0]
            word1 = struct.unpack('<I', file.read(4))[0]
            word2 = struct.unpack('<I', file.read(4))[0]
            word3 = struct.unpack('<I', file.read(4))[0]

            legacy_mode = get_bit(word0, 30)  # Bool
            invalid_data = get_bit(word0, 31)  # Bool
            seconds_from_epoch = ibits(word0, 0, 30)  # int
            data_frame_n = ibits(word1, 0, 24)  # int
            reference_epoch = ibits(word1, 24, 6)  # int
            data_frame_len_8bytes = ibits(word2, 0, 24)  # int
            log2nchann = ibits(word2, 24, 5)  # int
            vdif_version = ibits(word2, 29, 3)  # int
            stationID = chr(ibits(word3, 0, 8)) + chr(ibits(word3, 8, 16))  # string
            threadID = ibits(word3, 16, 10)
            bit_sample_min1 = ibits(word3, 26, 5)
            data_type = get_bit(word3, 31)  # 0 real, 1 complex
            header_size_bytes = 16
            if not legacy_mode:
                word4 = struct.unpack('<I', file.read(4))[0]
                word5 = struct.unpack('<I', file.read(4))[0]
                word6 = struct.unpack('<I', file.read(4))[0]
                word7 = struct.unpack('<I', file.read(4))[0]
                header_size_bytes = 32

            data_frame_len_bytes = data_frame_len_8bytes * 8
            nchann = 2 ** log2nchann
            bit_sample = bit_sample_min1 + 1

            FRAME_HEADER = {'legacy_mode': legacy_mode,
                            'invalid_data': invalid_data,
                            'seconds_from_epoch': seconds_from_epoch,
                            'data_frame_n': data_frame_n,
                            'reference_epoch': reference_epoch,
                            'data_frame_len_bytes': data_frame_len_bytes,
                            'nchann': nchann,
                            'vdif_version': vdif_version,
                            'stationID': stationID,
                            'threadID': threadID,
                            'bit_sample': bit_sample,
                            'data_type': data_type,
                            'header_size_bytes': header_size_bytes}

            n32bitwords = (FRAME_HEADER['data_frame_len_bytes'] - FRAME_HEADER['header_size_bytes']) // 4  # each read word is 4 bytes

            total_samples_bits = (FRAME_HEADER['data_frame_len_bytes'] - FRAME_HEADER['header_size_bytes']) * 8
            total_samples = total_samples_bits // FRAME_HEADER['bit_sample']
            total_samples_perchann = total_samples // nchann  # 4000 samples with 2bit in a word, 8chann, 8000bytes data frame

            samples_per_32bitword = 32 // FRAME_HEADER['bit_sample']  # 16 samples of 2bit in a word

            index = 0  # counter for all the samples and channels in one second of data
            channels_sample = [None] * nchann
            samples = [None] * total_samples * frames_in_sec  # all samples of all channels for one second of data

        else:
            # Skip header
            offset_position = file.tell()
            file.seek(offset_position + FRAME_HEADER['header_size_bytes'])

        # Read data
        for counter in range(n32bitwords):  # Main cycle on all the sample data field
            iword32 = struct.unpack('<I', file.read(4))[0]
            for jj in range(samples_per_32bitword):  # 0-15
                if get_bit(iword32, (jj * 2) + 1):  # !coding: -3 -1 1 3 -> signmagn 00 01 10 11
                    samples[index] = get_bit(iword32, jj * 2) * 2 + 1
                else:
                    samples[index] = get_bit(iword32, jj * 2) * 2 - 3
                index += 1
    # Extract
    for i in range(nchann):
        channels_sample[i] = samples[i::nchann]  # one element every nchann elements

    FRAME_SEC = {"HEADER": FRAME_HEADER,
                 "DATA": channels_sample}
    return FRAME_SEC
