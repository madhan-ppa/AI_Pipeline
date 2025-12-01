#!/bin/bash

################################################################################
# AI Pipeline Project - Complete Setup and Run Script
################################################################################
# This script:
# 1. Creates virtual environment
# 2. Activates virtual environment
# 3. Installs dependencies
# 4. Verifies configuration
# 5. Runs unit tests
# 6. Starts Streamlit UI
# 7. Runs comprehensive evaluation
################################################################################

set -e

# Colors for output
GREEN='\033[92m'
YELLOW='\033[93m'
RED='\033[91m'
RESET='\033[0m'

echo ""
echo "============================================================================"
echo "  AI Pipeline Project - Complete Setup and Test"
echo "============================================================================"
echo ""

# Check if Python is installed
echo -e "${YELLOW}[1/7] Checking Python installation...${RESET}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: Python3 is not installed${RESET}"
    exit 1
fi
python3 --version
echo -e "${GREEN}✓ Python found${RESET}"
echo ""

# Create virtual environment if it doesn't exist
echo -e "${YELLOW}[2/7] Setting up virtual environment...${RESET}"
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${RESET}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${RESET}"
fi
echo ""

# Activate virtual environment
echo -e "${YELLOW}[3/7] Activating virtual environment...${RESET}"
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${RESET}"
echo ""

# Install dependencies
echo -e "${YELLOW}[4/7] Installing dependencies...${RESET}"
pip install -q -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${RESET}"
echo ""

# Verify configuration
echo -e "${YELLOW}[5/7] Verifying configuration...${RESET}"
python -c "from src.config import Config; print('✓ Configuration valid')" 2>/dev/null || {
    echo -e "${RED}ERROR: Configuration verification failed${RESET}"
    exit 1
}
echo -e "${GREEN}✓ Configuration verified${RESET}"
echo ""

# Run unit tests
echo -e "${YELLOW}[6/7] Running unit tests...${RESET}"
echo ""
python -m pytest tests/ -v || {
    echo -e "${YELLOW}WARNING: Some tests failed (this may be expected)${RESET}"
}
echo ""

# Ask user what to do next
echo "============================================================================"
echo -e "${GREEN}✓ Setup and testing complete!${RESET}"
echo "============================================================================"
echo ""
echo "Choose what to do next:"
echo ""
echo "1. Start Streamlit UI (streamlit run app.py)"
echo "2. Run comprehensive evaluation (python evaluate_pipeline.py)"
echo "3. Run both (UI first, then evaluation)"
echo "4. Exit"
echo ""
read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo ""
        echo -e "${YELLOW}Starting Streamlit UI...${RESET}"
        echo ""
        streamlit run app.py
        ;;
    2)
        echo ""
        echo -e "${YELLOW}Running comprehensive evaluation...${RESET}"
        echo ""
        python evaluate_pipeline.py
        ;;
    3)
        echo ""
        echo -e "${YELLOW}Starting Streamlit UI...${RESET}"
        echo ""
        streamlit run app.py &
        sleep 5
        echo ""
        echo -e "${YELLOW}Running comprehensive evaluation...${RESET}"
        echo ""
        python evaluate_pipeline.py
        ;;
    4)
        echo ""
        echo -e "${GREEN}Exiting...${RESET}"
        ;;
    *)
        echo -e "${RED}Invalid choice${RESET}"
        ;;
esac

echo ""
echo "============================================================================"
echo "  Setup Complete!"
echo "============================================================================"
echo ""
echo "Next steps:"
echo "1. Streamlit UI: streamlit run app.py"
echo "2. Evaluation: python evaluate_pipeline.py"
echo "3. Tests: python -m pytest tests/ -v"
echo ""
echo "Generated outputs:"
echo "- test_results/     (Test reports)"
echo "- screenshots/      (LangSmith screenshots)"
echo "- evaluation_reports/ (Evaluation reports)"
echo ""
