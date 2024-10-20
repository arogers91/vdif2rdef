#!/bin/bash
#--------------------------------------------------------------------------------------
# Configuration Variables

SPACECRAFT_ID='None'    #4 letters [GAIA, for gaia spacecraft]
EGRS_ID='S028H'         #n letter [S0000, the name of the quasar]
STATION_ID='Wa'         #2 letters, e.g., ME87 for Medicina station
RECEIVER_N='00'         #2-digit receiver number

TRANSMITTER_TYPE='S'    # Default transmitter type for each file (S or Q)
RECORDING_NUMBER='001'  # Default recording number for each file
CHANNELS_FREQUENCY=( '8000000000.00' '8001000000.00' '8002000000.00' '8003000000.00' '8004000000.00' '8005000000.00' '8006000000.00' '8007000000.00' )
DOR_TONES_OFFSET=( '0.00' '-5000000.00' '5000000.00' '0.00' )

VLBI_FREQUENCY_OFFSET='1000000.00'
CARRIER_FREQUENCY='8000000000.00'

# Set TRANSLATOR_PATH to the vdif2rdef/ directory
TRANSLATOR_PATH=${PWD}

#--------------------------------------------------------------------------------------
# Check if the directory argument is provided
if [ -z "$1" ]; then
    echo "Error: No directory provided. Usage: ./sidefile_creator.sh /path/to/files/"
    exit 1
fi

# Get the directory from the first argument
FILE_PATH="$1"

# Ensure directory exists and move to it
if [ ! -d "${FILE_PATH}" ]; then
    echo "Error: Directory ${FILE_PATH} does not exist."
    exit 1
fi

# Enable nullglob option to handle empty directories gracefully
shopt -s nullglob

# Create auxiliary directory for sidefiles
AUX_DIR="${FILE_PATH}/aux_files"
mkdir -p "${AUX_DIR}"

# Iterate over each file in the provided directory
for FILE in "${FILE_PATH}"/*; do
    # Only process if it's a regular file (skip directories)
    if [ -f "$FILE" ]; then
        # Extract the filename without extension to use as sidefile base name
        BASENAME=$(basename "${FILE}")
        SIDEFILE="${AUX_DIR}/${BASENAME}.aux"  # Save sidefiles in the auxiliary directory
        PRD_NAME="${SPACECRAFT_ID}n${RECORDING_NUMBER}t${TRANSMITTER_TYPE}s${STATION_ID}r${RECEIVER_N}"

        # Format frequency values for the sidefile
        FREQUENCIES=$(IFS=,; echo "${CHANNELS_FREQUENCY[*]}")
        FREQUENCIES_DOR_OFFSET=$(IFS=,; echo "${DOR_TONES_OFFSET[*]}")

        # Generate the sidefile
        cat << EOF > "${SIDEFILE}"
SPACECRAFT_ID         = '${SPACECRAFT_ID}'
EGRS_ID               = '${EGRS_ID}'
RECORDING_NUMBER      = '${RECORDING_NUMBER}'
TRANSMITTER_TYPE      = '${TRANSMITTER_TYPE}'
STATION_ID            = '${STATION_ID}'
RECEIVER_N            = '${RECEIVER_N}'
PRD_NAME              = '${PRD_NAME}'
NUMBER_CHANNELS       = ${#CHANNELS_FREQUENCY[@]}
CHANNELS_FREQUENCY    = [ ${FREQUENCIES} ]
VLBI_FREQUENCY_OFFSET = ${VLBI_FREQUENCY_OFFSET}
CARRIER_FREQUENCY     = ${CARRIER_FREQUENCY}
DOR_TONES_OFFSET      = [ ${FREQUENCIES_DOR_OFFSET} ]
EOF

        echo "Generated sidefile: ${SIDEFILE}"
    fi
done

echo "End of script."
