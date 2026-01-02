# Forensic-LLM

<img src="https://raw.githubusercontent.com/jhonney13/Forensic-LLM/refs/heads/main/img/ForensicLLM-Open-Source.png" />


**An AI-powered CLI tool for scraping legal cases from Indian Kanoon and extracting evidence using local LLMs.**

Forensic-LLM combines web scraping with AI-powered analysis to help legal researchers, lawyers, and forensic analysts efficiently extract and analyze evidence from Indian court judgments.


##  What This Project Does

Forensic-LLM is a comprehensive tool with two integrated components:

1. **Case Scraper** - Intelligently scrapes legal cases from Indian Kanoon website with interactive court/year/keyword selection
2. **AI Evidence Extractor** - Uses local LLM (Ollama) to analyze cases and extract structured evidence automatically


##  Project Structure

```
Forensic LLM Working/
├── Extractor/
│   ├── browse_scraper.py          # Main interactive scraper (CLI entry point)
│   ├── raw output/                # Scraped case data (JSON files)
│   │   └── search_cases_*.json
│   └── evidence_extraction.log    # Log file for evidence extraction
├── Analysis/
│   ├── evidence_extractor.py      # AI-powered evidence extraction
│   └── Output/                    # Extracted evidence (JSON files)
│       └── evidence_*.json
├── forensic_llm_cli.py            # CLI wrapper (creates 'forensic-llm' command)
├── setup.py                       # Package installation script
├── requirements.txt               # Python dependencies
├── forensic-llm.bat              # Windows batch file launcher
├── forensic-llm.ps1              # PowerShell launcher
└── README.md                      # This file
```



##  CLI Workflow Flowchart

![CLI Workflow Flowchart](https://raw.githubusercontent.com/jhonney13/Forensic-LLM/refs/heads/main/img/diagram-export-1-2-2026-12_15_40-PM.jpg)

### Interactive Workflow
When you run `forensic-llm`, you'll be guided through an interactive process:


##  Prerequisites

Before installing Forensic-LLM, ensure you have:

### 1. Python 3.7 or Higher
- Download from [python.org](https://www.python.org/downloads/)
- **Important**: Check "Add Python to PATH" during installation
- Verify: `python --version`

### 2. Google Chrome Browser
- Download from [chrome.google.com](https://www.google.com/chrome/)
- Required for web scraping (runs in headless mode)

### 3. Ollama (for AI Evidence Extraction)
- Download from [ollama.ai](https://ollama.ai)
- Install and start the Ollama service
- Pull the required model:
  ```bash
  ollama pull gemma3:4b
  ```
- **Note**: Ollama is only needed for evidence extraction, not for scraping



##  Installation

### Step 1: Download/Clone the Project

Download or clone the project folder to your PC:
```
C:\Forensic LLM\Forensic LLM Working
```

### Step 2: Install Python Dependencies

Open a terminal/command prompt in the project folder:

```bash
cd "C:\Forensic LLM\Forensic LLM Working"
pip install -r requirements.txt
```

**Installed packages:**
- `rich>=13.0.0` - Beautiful terminal UI with tables, panels, and progress bars
- `undetected-chromedriver` - Web scraping (handles Chrome automatically)
- `beautifulsoup4` - HTML parsing
- `selenium` - Browser automation
- `requests` - HTTP requests (for Ollama API)
- `tqdm` - Progress bars (used by some components)

### Step 3: Install Forensic-LLM as a Command

Install the package in editable mode:

```bash
python -m pip install -e .
```

This creates the `forensic-llm` command that you can run from anywhere.

**Note:** If you get "Access is denied" error:
- Use `python -m pip` instead of just `pip`
- Or run PowerShell/Command Prompt as Administrator

### Step 4: Verify Installation

Test that the command works:

```bash
forensic-llm
```

You should see a welcome banner and the interactive menu should start.



##  Quick Start

### Method 1: Using the CLI Command (Recommended)

After installation, run from anywhere:

```bash
forensic-llm
```

### Method 2: Manual Execution

If you prefer not to install the command:

```bash
cd "C:\Forensic LLM\Forensic LLM Working\Extractor"
python browse_scraper.py
```


##  Usage Guide

### Interactive Workflow


When you run `forensic-llm`, you'll be guided through an interactive process:

![Forensic LLM](https://raw.githubusercontent.com/jhonney13/Forensic-LLM/refs/heads/main/img/forensic-llm%20(1).jpg)



#### Step 1: Select a Court
- The tool automatically discovers all available courts from Indian Kanoon
- Choose from Supreme Court or High Courts
- A beautiful table displays all options with numbers

![Select a Court](https://raw.githubusercontent.com/jhonney13/Forensic-LLM/refs/heads/main/img/Select%20a%20Court.jpg)

#### Step 2: Select Year (Optional)
- Browse available years for the selected court
- Press Enter to skip and scrape all years
- Years are displayed in a formatted table

![Select Year](https://raw.githubusercontent.com/jhonney13/Forensic-LLM/refs/heads/main/img/Select%20Year.jpg)

#### Step 3: Select Period (Optional)
- If a year is selected, choose a specific month or "Entire Year"
- Press Enter to skip and scrape the entire year
- Useful for targeted searches

![Select Period](https://raw.githubusercontent.com/jhonney13/Forensic-LLM/refs/heads/main/img/Select%20Period.jpg)

#### Step 4: Enter Search Keyword
- Enter a keyword to search for (e.g., "murder", "rape", "robbery")
- The tool builds a search query automatically
- Shows you the search URL before proceeding

![Enter Search Keyword](https://raw.githubusercontent.com/jhonney13/Forensic-LLM/refs/heads/main/img/Enter%20Search%20Keyword.jpg)

#### Step 5: Choose Pages to Scrape
- The tool inspects search results and shows total pages/cases
- Enter how many pages you want to scrape
- Progress is tracked with a live progress bar

![Choose Pages to Scrape](https://raw.githubusercontent.com/jhonney13/Forensic-LLM/refs/heads/main/img/Choose%20Pages%20to%20Scrape.jpg)

#### Step 6: Automatic Evidence Extraction (Optional)
- After scraping completes, you'll be asked if you want to extract evidence
- If yes, the AI analysis starts automatically
- No need to run a separate command!

![Automatic Evidence Extraction](https://raw.githubusercontent.com/jhonney13/Forensic-LLM/refs/heads/main/img/Automatic%20Evidence%20Extraction.jpg)


### Manual Evidence Extraction

If you want to extract evidence separately or from existing files:

```bash
cd Analysis
python evidence_extractor.py
```

The script will:
- Automatically find the latest scraped JSON file
- Use AI (Ollama) to analyze each case
- Extract different types of evidence (physical, digital, witness testimony, etc.)
- Save results to `Output/` folder with timestamp

**Specify a file manually:**
```bash
python evidence_extractor.py --json "Extractor/raw output/your_file.json"
```



##  Command Line Options

### Evidence Extractor Options

When running the evidence extractor manually:

```bash
python evidence_extractor.py [OPTIONS]
```

**Available Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--json` | Specify a JSON file to process (from scraper) | Auto-detect latest |
| `--csv` | Specify a CSV file to process (alternative format) | Auto-detect latest |
| `--output` | Set custom output file path | Auto-generated with timestamp |
| `--model` | Change AI model (default: gemma3:4b) | `gemma3:4b` |
| `--max-cases` | Limit number of cases to process | All cases |
| `--start` | Start from a specific case number (useful for resuming) | `0` |

**Examples:**

```bash
# Process specific file with limit
python evidence_extractor.py --json "Extractor/raw output/cases.json" --max-cases 10

# Resume from case 50
python evidence_extractor.py --json "cases.json" --start 50

# Use different AI model
python evidence_extractor.py --json "cases.json" --model "llama2:7b"

# Process CSV file
python evidence_extractor.py --csv "cases.csv" --max-cases 20
```



##  Output Format

### Scraped Cases (JSON)

Each case in the scraped JSON file includes:

```json
{
  "court": "Madhya Pradesh High Court",
  "case_title": "State vs. John Doe",
  "case_date": "2020-01-15",
  "case_link": "https://indiankanoon.org/doc/...",
  "case_content": "Full judgment text...",
  "year": "2020",
  "period": "January",
  "keyword": "murder"
}
```

**Fields:**
- `court` - Court name
- `case_title` - Title of the case
- `case_date` - Date of judgment
- `case_link` - URL to the case on Indian Kanoon
- `case_content` - Full text of the judgment
- `year`, `period`, `keyword` - Search filters used


### Extracted Evidence (JSON)

Each case analysis includes structured evidence:

```json
{
  "case_title": "State vs. John Doe",
  "case_index": 0,
  "case_link": "https://indiankanoon.org/doc/...",
  "court": "Madhya Pradesh High Court",
  "case_date": "2020-01-15",
  "evidence_found": [
    {
      "evidence": "Detailed description",
      "type": "physical/digital/witness/document/forensic/circumstantial/other",
      "strength": "strong/moderate/weak",
      "relevance": "high/medium/low",
      "source": "where the evidence came from"
    }
  ],
  "physical_evidence": ["weapons", "documents", "clothing"],
  "digital_evidence": ["emails", "texts", "camera footage"],
  "witness_testimony": ["eyewitness accounts", "expert testimony"],
  "forensic_evidence": ["DNA", "fingerprints", "ballistics"],
  "documentary_evidence": ["contracts", "records", "certificates"],
  "circumstantial_evidence": ["motive", "opportunity"],
  "key_facts": ["fact1", "fact2"],
  "legal_issues": ["issue1", "issue2"],
  "outcome": "Court decision",
  "summary": "Brief summary"
}
```



##  System Requirements

### Minimum Requirements

- **Operating System**: Windows 10/11, macOS, or Linux
- **Python**: 3.7 or higher
- **RAM**: 4GB minimum (8GB recommended for AI processing)
- **Storage**: 500MB free space
- **Internet**: Stable connection for scraping

### Required Software

1. **Python 3.7+** - [Download](https://www.python.org/downloads/)
2. **Google Chrome** - [Download](https://www.google.com/chrome/)
3. **Ollama** - [Download](https://ollama.ai)
   - Required model: `gemma3:4b` (install with: `ollama pull gemma3:4b`)
   - **Note**: Only needed for evidence extraction, not scraping

### Python Packages

All required packages are listed in `requirements.txt` and installed automatically:
- `rich>=13.0.0` - Terminal UI with tables, panels, progress bars
- `undetected-chromedriver` - Web scraping (auto-handles Chrome)
- `beautifulsoup4` - HTML parsing
- `selenium` - Browser automation
- `requests` - HTTP requests (for Ollama API)
- `tqdm` - Progress bars



##  Advanced Usage

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

# Pull a different model (larger models = better quality, slower)
ollama pull llama2:7b
ollama pull mistral:7b
ollama pull codellama:7b

# Use it in evidence extraction
python evidence_extractor.py --json "cases.json" --model "llama2:7b"
```

**Model Recommendations:**
- `gemma3:4b` - Fast, good quality (default)
- `llama2:7b` - Better quality, slower
- `mistral:7b` - Balanced quality/speed

### Batch Processing

Process multiple files:

**Windows (PowerShell):**
```powershell
Get-ChildItem "Extractor\raw output\*.json" | ForEach-Object {
    python Analysis\evidence_extractor.py --json $_.FullName
}
```

**Linux/macOS:**
```bash
for file in Extractor/raw\ output/*.json; do
    python Analysis/evidence_extractor.py --json "$file"
done
```

### Resuming Interrupted Extraction

If evidence extraction is interrupted, you can resume:

```bash
# Resume from case 50 (if extraction stopped at case 49)
python evidence_extractor.py --json "cases.json" --start 50
```

Progress is auto-saved every 5 cases, so you won't lose much work.



##  Troubleshooting

### Common Issues

#### `forensic-llm` command not found

**Solutions:**
- Make sure you ran `pip install -e .` from the project root folder
- Verify installation: Check `%APPDATA%\Python\Python313\Scripts\` (or similar) for `forensic-llm.exe`
- Reinstall: `python -m pip install -e . --force-reinstall`
- Add Python Scripts to PATH if needed

#### Ollama connection error

**Solutions:**
- Start Ollama: `ollama serve` (or start the Ollama service)
- Check model: `ollama list` (should show `gemma3:4b`)
- Install model if missing: `ollama pull gemma3:4b`
- Check connection: `curl http://localhost:11434/api/tags` (or visit in browser)
- Verify Ollama is running: Check Task Manager (Windows) or `ps aux | grep ollama` (Linux/macOS)

#### Chrome/ChromeDriver errors

**Solutions:**
- Update Chrome to the latest version
- The script uses `undetected-chromedriver` which should auto-update
- If issues persist, try running Chrome manually first
- Check Chrome version: `chrome://version/`
- Restart your computer if Chrome processes are stuck

#### Scraper not finding cases

**Solutions:**
- Try different keywords (be specific: "murder", "homicide", "assault")
- Check if the court/year combination has cases available
- Some courts may have limited historical data
- Try broader search terms
- Verify the search URL works in a browser
- Check if Indian Kanoon website is accessible

#### Module import errors

**Solutions:**
- Make sure you're in the correct directory
- Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`
- Check Python version: `python --version` (should be 3.7+)
- Use virtual environment: `python -m venv venv` then activate it
- Verify all packages installed: `pip list`

#### Permission/Access denied errors

**Solutions:**
- Run terminal as Administrator (Windows) or use `sudo` (Linux/macOS)
- Use `python -m pip` instead of just `pip`
- Check file/folder permissions
- Ensure you have write access to the project directory

#### Browser runs but no cases found

**Solutions:**
- Check if Cloudflare protection is blocking (wait longer)
- Verify the search query returns results in a browser
- Try a different keyword or court
- Check network connection
- Some courts may require different search syntax

#### Evidence extraction returns empty results

**Solutions:**
- Verify Ollama is running: `ollama list`
- Check model is installed: `ollama pull gemma3:4b`
- Try a different model: `--model llama2:7b`
- Check case content is not empty in JSON file
- Verify JSON file format is correct

---

##  Important Notes

- **Website Delays**: The scraper includes delays to respect the website and avoid overloading servers
- **Progress Saving**: Evidence extraction saves progress every 5 cases, so you can stop and resume
- **File Naming**: All output files include timestamps in their names for easy tracking
- **Ollama Required**: Evidence extraction requires Ollama to be running locally (not needed for scraping)
- **Headless Mode**: The browser runs in headless mode (no visible window) for faster operation
- **Cloudflare Protection**: The scraper automatically waits for Cloudflare protection to pass
- **Rate Limiting**: Built-in delays prevent overwhelming the Indian Kanoon servers



##  Support

For issues or questions:

1. Check the troubleshooting section above
2. Verify all prerequisites are installed correctly
3. Check that Ollama is running and the model is installed
4. Ensure Chrome browser is up to date
5. Review log files: `Extractor/evidence_extraction.log`



##  License

This project is provided as-is for educational and research purposes. Please respect the terms of service of Indian Kanoon when using this tool.



##  Acknowledgments

- **Indian Kanoon** - For providing access to legal case data
- **Ollama** - For providing local LLM capabilities
- **Rich** - For the beautiful terminal UI library
- **Selenium & BeautifulSoup** - For web scraping capabilities



**Made with ❤️ for legal researchers and forensic analysts**
