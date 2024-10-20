# vdif2rdef

**vdif2rdef** is a tool for converting VLBI Data Interchange Format (VDIF) files into Delta-DOR Raw Data Exchange Format (RDEF) files, following the recommended standards of the Consultative Committee for Space Data Systems (CCSDS).

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)

## Overview
This tool is designed to assist in converting data collected in the VLBI Data Interchange Format (VDIF) into the Delta-DOR Raw Data Exchange Format (RDEF) as defined by CCSDS. Delta-DOR (Delta Differential One-way Ranging) is used for spacecraft navigation, and this tool aids in preparing data for space agency operations or research.

## Features
- Converts VDIF files to RDEF format.
- Compliant with CCSDS standards for data exchange.
- Lightweight and easy to integrate into existing workflows.

## Installation
To install and use **vdif2rdef**, follow the steps below:

### Prerequisites
Ensure you have the following installed:
- Python 3.x

### Steps
1. Clone the repository:
    ```bash
    git clone https://github.com/yourusername/vdif2rdef.git
    cd vdif2rdef
    ```

## Usage
Once installed, you will need to update certain configuration variables inside the 'sidefile_creator.sh' and 'vdif2rdef.sh' scripts to match your specific setup. You can then use **vdif2rdef** to convert VDIF files to RDEF with the following commands:
```bash
./sidefile_creator.sh /path/to/vdif/files/
./vdif2rdef.sh /path/to/vdif/files
```

If you wish to auto-correlate the RDEF files, you can do so with the following command:
```bash
python auto_correlation_rdef.py /path/to/rdef/files
```
