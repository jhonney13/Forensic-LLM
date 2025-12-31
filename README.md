# Forensic-LLM

A tool for scraping legal cases from Indian Kanoon and extracting evidence using AI.

## What This Project Does

This project has two main parts:

1. **Case Scraper** - Downloads legal cases from Indian Kanoon website
2. **Evidence Extractor** - Analyzes the cases and finds evidence using AI

## Project Structure

```
Forensic LLM Working/
├── Extractor/
│   ├── browse_scraper.py          # Scrapes cases from Indian Kanoon
│   └── raw output/                # Scraped case data (JSON files)
├── Analysis/
│   ├── evidence_extractor.py       # Extracts evidence from cases using AI
│   └── Output/                    # Extracted evidence (JSON files)
└── requirements.txt               # Python packages needed
```

## Setup Instructions

### Prerequisites

Before installing Forensic-LLM, make sure you have:

1. **Python 3.7 or higher**
   - Download from https://www.python.org/downloads/
   - During installation, check "Add Python to PATH"
   - Verify installation: `python --version`

2. **Google Chrome Browser**
   - Download from https://www.google.com/chrome/
   - Required for web scraping

3. **Ollama (for AI evidence extraction)**
   - Download from https://ollama.ai
   - Install and start the Ollama service
   - Pull the required model:
     ```bash
     ollama pull gemma3:4b
     ```

### Installation Steps

#### Step 1: Download/Clone the Project

Download the project folder to your PC, for example:
```
C:\Forensic LLM\Forensic LLM Working
```

#### Step 2: Install Python Dependencies

Open a terminal/command prompt in the project folder and run:

```bash
cd "C:\Forensic LLM\Forensic LLM Working"
pip install -r requirements.txt
```

This will install:
- `rich` - For beautiful terminal UI
- `undetected-chromedriver` - For web scraping
- `beautifulsoup4` - For HTML parsing
- `selenium` - For browser automation
- `requests` - For API calls
- `tqdm` - For progress bars

#### Step 3: Install Forensic-LLM as a Command

Install the package in editable mode:

```bash
python -m pip install -e .
```

This creates the `forensic-llm` command that you can run from anywhere.

**Note:** If you get "Access is denied" error:
- Use `python -m pip` instead of just `pip`
- Or run PowerShell/Command Prompt as Administrator

#### Step 4: Verify Installation

Test that the command works:

```bash
forensic-llm
```

You should see the welcome banner and the script should start.

### Alternative: Manual Setup (Without Command)

If you prefer not to install the command, you can run it manually:

```bash
cd "C:\Forensic LLM\Forensic LLM Working\Extractor"
python browse_scraper.py
```

### Troubleshooting

**Problem: `forensic-llm` command not found**
- Solution: Make sure you ran `pip install -e .` from the project root folder
- Verify: Check if `forensic-llm.exe` exists in `%APPDATA%\Python\Python313\Scripts\` (or similar)

**Problem: ModuleNotFoundError**
- Solution: Reinstall the package: `python -m pip install -e . --force-reinstall`

**Problem: Chrome/ChromeDriver errors**
- Solution: Make sure Chrome browser is installed and up to date
- The script uses `undetected-chromedriver` which should handle Chrome automatically

**Problem: Ollama connection error**
- Solution: Make sure Ollama is running: `ollama serve`
- Verify the model is installed: `ollama list`
- Install the model if missing: `ollama pull gemma3:4b`

**Problem: Permission/Access denied errors**
- Solution: Run terminal as Administrator, or use `python -m pip` instead of `pip`

## How to Use

### Quick Start (Recommended)

After setup, you can run the tool from anywhere:

```bash
forensic-llm
```

### Manual Method

If you prefer to run it manually:

```bash
cd Extractor
python browse_scraper.py
```

### Step 1: Scrape Cases

Run the scraper to download cases from Indian Kanoon:

The script will:
- Show you a list of courts to choose from
- Let you pick a year and month (optional)
- Ask for a keyword to search (like "murder", "rape", etc.)
- Scrape matching cases and save them to `raw output/` folder

### Step 2: Extract Evidence

After scraping cases, analyze them to extract evidence:

```bash
cd Analysis
python evidence_extractor.py
```

The script will:
- Automatically find the latest scraped JSON file
- Use AI to analyze each case
- Extract different types of evidence (physical, digital, witness testimony, etc.)
- Save results to `Output/` folder

You can also specify a file manually:
```bash
python evidence_extractor.py --json "Extractor/raw output/your_file.json"
```

## Command Line Options

### Evidence Extractor Options

When running the evidence extractor manually, you can use these options:

```bash
python evidence_extractor.py [OPTIONS]
```

**Options:**
- `--json` - Specify a JSON file to process (from scraper)
- `--csv` - Specify a CSV file to process (alternative format)
- `--output` - Set custom output file path (default: auto-generated with timestamp)
- `--model` - Change AI model (default: gemma3:4b)
- `--max-cases` - Limit number of cases to process
- `--start` - Start from a specific case number (useful for resuming)

**Examples:**
```bash
# Process specific file with limit
python evidence_extractor.py --json "Extractor/raw output/cases.json" --max-cases 10

# Resume from case 50
python evidence_extractor.py --json "cases.json" --start 50

# Use different AI model
python evidence_extractor.py --json "cases.json" --model "llama2:7b"
```

## Output Format

### Scraped Cases (JSON)
Each case includes:
- `court` - Court name
- `case_title` - Title of the case
- `case_date` - Date of judgment
- `case_link` - URL to the case
- `case_content` - Full text of the judgment
- `year`, `period`, `keyword` - Search filters used

### Extracted Evidence (JSON)
Each case analysis includes:
- `case_title` - Case title
- `evidence_found` - List of evidence items with details
- `physical_evidence` - Physical items found
- `digital_evidence` - Digital items found
- `witness_testimony` - Witness accounts
- `forensic_evidence` - Forensic analysis results
- `documentary_evidence` - Documents mentioned
- `key_facts` - Important facts
- `legal_issues` - Legal questions raised
- `outcome` - Court decision
- `summary` - Brief summary

## System Requirements

### Minimum Requirements
- **Operating System**: Windows 10/11, macOS, or Linux
- **Python**: 3.7 or higher
- **RAM**: 4GB minimum (8GB recommended)
- **Storage**: 500MB free space
- **Internet**: Stable connection for scraping

### Required Software
1. **Python 3.7+** - [Download](https://www.python.org/downloads/)
2. **Google Chrome** - [Download](https://www.google.com/chrome/)
3. **Ollama** - [Download](https://ollama.ai)
   - Required model: `gemma3:4b` (install with: `ollama pull gemma3:4b`)

### Python Packages (Auto-installed)
All required packages are listed in `requirements.txt` and will be installed automatically:
- `rich>=13.0.0` - Terminal UI
- `undetected-chromedriver` - Web scraping
- `beautifulsoup4` - HTML parsing
- `selenium` - Browser automation
- `requests` - HTTP requests
- `tqdm` - Progress bars

## Important Notes

- **Website Delays**: The scraper includes delays to respect the website and avoid overloading servers
- **Progress Saving**: Evidence extraction saves progress every 5 cases, so you can stop and resume
- **File Naming**: All output files include timestamps in their names for easy tracking
- **Ollama Required**: Evidence extraction requires Ollama to be running locally (not needed for scraping)
- **Headless Mode**: The browser runs in headless mode (no visible window) for faster operation

## File Structure

After running the tool, your project will have:

```
Forensic LLM Working/
├── Extractor/
│   ├── browse_scraper.py          # Main scraper script
│   ├── raw output/                # Scraped case data (JSON files)
│   │   └── search_cases_*.json
│   └── Output/                     # Evidence extraction results (if run from Extractor)
│       └── evidence_*.json
├── Analysis/
│   ├── evidence_extractor.py       # Evidence extraction script
│   └── Output/                     # Evidence extraction results
│       └── evidence_*.json
├── forensic_llm_cli.py            # Command-line wrapper
├── setup.py                       # Package installation script
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

## Advanced Usage

### Running on Different PCs

To set up on a new PC:

1. Copy the entire project folder
2. Install Python 3.7+ and add to PATH
3. Install Chrome browser
4. Install Ollama and pull the model: `ollama pull gemma3:4b`
5. Run: `pip install -r requirements.txt`
6. Run: `python -m pip install -e .`
7. Test: `forensic-llm`

### Using Different AI Models

You can use any Ollama model for evidence extraction:

```bash
# List available models
ollama list

# Pull a different model
ollama pull llama2:7b

# Use it in evidence extraction
python evidence_extractor.py --json "cases.json" --model "llama2:7b"
```

### Batch Processing

Process multiple files:

```bash
# Process all JSON files in raw output folder
for file in Extractor/raw\ output/*.json; do
    python Analysis/evidence_extractor.py --json "$file"
done
```

## Troubleshooting

### Common Issues

**`forensic-llm` command not found**
- Make sure you ran `pip install -e .` from the project root
- Verify installation: Check `%APPDATA%\Python\Python313\Scripts\` for `forensic-llm.exe`
- Reinstall: `python -m pip install -e . --force-reinstall`

**Ollama connection error**
- Start Ollama: `ollama serve` (or start the Ollama service)
- Check model: `ollama list` (should show `gemma3:4b`)
- Install model: `ollama pull gemma3:4b`
- Check connection: `curl http://localhost:11434/api/tags`

**Chrome/ChromeDriver errors**
- Update Chrome to the latest version
- The script uses `undetected-chromedriver` which should auto-update
- If issues persist, try running Chrome manually first

**Scraper not finding cases**
- Try different keywords (be specific: "murder", "homicide", etc.)
- Check if the court/year combination has cases available
- Some courts may have limited historical data
- Try broader search terms

**Module import errors**
- Make sure you're in the correct directory
- Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`
- Check Python version: `python --version` (should be 3.7+)

**Permission/Access denied errors**
- Run terminal as Administrator
- Use `python -m pip` instead of just `pip`
- Check file/folder permissions

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify all prerequisites are installed
3. Check that Ollama is running and the model is installed
4. Ensure Chrome browser is up to date

