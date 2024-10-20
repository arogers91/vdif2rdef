#!/bin/bash

#--------------------------------------------------------------------------------------
# Configuration Variables

# SKIP_SECONDS
# Number of seconds to skip from the beginning of the file.
# Allowed values:   integer
# Default:          SKIP_SECONDS=0
SKIP_SECONDS=0

# MAX_SECONDS
# Maximum number of seconds to analyze.
# Allowed values:   integer
# Default:          MAX_SECONDS=1
MAX_SECONDS=1

# CHANNELS_TO_EXTRACT
# List of channels to extract. First channel is channel 1.
# Allowed values:   list of integers, as string
# Default:          CHANNELS_TO_EXTRACT='1 2 3 4 5 6 7 8'
CHANNELS_TO_EXTRACT='1 2 3 4 5 6 7 8'

# TRANSLATOR_PATH
# Path containing the python script
# Allowed values:   "%path%"
# Default:          TRANSLATOR_PATH=${PWD}
TRANSLATOR_PATH=${PWD}


#--------------------------------------------------------------------------------------
# Check if the directory argument is provided
if [ -z "$1" ]; then
    echo "Error: No directory provided. Usage: ./translator.sh /path/to/files/"
    exit 1
fi

# Get the directory from the first argument
FILE_PATH="$1"

# Ensure directory exists
if [ ! -d "${FILE_PATH}" ]; then
    echo "Error: Directory ${FILE_PATH} does not exist."
    exit 1
fi

# Enable nullglob option to handle empty directories gracefully
shopt -s nullglob

# Change to the specified directory
cd "${FILE_PATH}" || exit 1

# Update FILE_PATH to remove any leading or trailing spaces or slashes
FILE_PATH=${PWD}

# Set AUX_DIR with location of aux files
AUX_DIR="${FILE_PATH}/aux_files/"

# Iterate over each file in the directory
for FILE in "${FILE_PATH}"/*; do
    if [ -f "${FILE}" ]; then
        # Extract the filename without extension to use as auxiliary file base name
        BASENAME=$(basename "${FILE}")
        AUX_FILE="${AUX_DIR}/${BASENAME}.aux"

        # Execute the translation script with the specified parameters
        echo "Running ${TRANSLATOR_PATH}/vdif2rdef.py ${FILE} -auxfile ${AUX_FILE} -skip ${SKIP_SECONDS} -maxseconds ${MAX_SECONDS} -channels ${CHANNELS_TO_EXTRACT} || exit 1"
        ${TRANSLATOR_PATH}/vdif2rdef.py "${FILE}" -auxfile "${AUX_FILE}" -skip "${SKIP_SECONDS}" -maxseconds "${MAX_SECONDS}" -channels "${CHANNELS_TO_EXTRACT}" || exit 1

        echo "... done for ${FILE}."
    fi
done

echo "End of script."
