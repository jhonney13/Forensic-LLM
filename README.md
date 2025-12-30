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

## Setup

1. Install Python (3.7 or higher)

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Install Ollama (for AI analysis):
   - Download from https://ollama.ai
   - Install the Gemma 3:4b model:
     ```bash
     ollama pull gemma3:4b
     ```

4. Make sure Chrome browser is installed (needed for web scraping)

## How to Use

### Step 1: Scrape Cases

Run the scraper to download cases from Indian Kanoon:

```bash
cd Extractor
python browse_scraper.py
```

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

- `--json` - Specify a JSON file to process
- `--csv` - Specify a CSV file to process
- `--output` - Set output file path
- `--model` - Change AI model (default: gemma3:4b)
- `--max-cases` - Limit number of cases to process
- `--start` - Start from a specific case number

Example:
```bash
python evidence_extractor.py --json "Extractor/raw output/cases.json" --max-cases 10
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

## Requirements

- Python 3.7+
- Chrome browser
- Ollama with Gemma 3:4b model
- Internet connection (for scraping)

## Notes

- The scraper respects website delays to avoid overloading servers
- Evidence extraction requires Ollama to be running locally
- Progress is saved every 5 cases, so you can stop and resume
- All output files include timestamps in their names

## Troubleshooting

**Ollama connection error:**
- Make sure Ollama is running: `ollama serve`
- Check if the model is installed: `ollama list`

**Scraper not working:**
- Make sure Chrome is installed
- Check your internet connection
- The website may have changed - the scraper may need updates

**No cases found:**
- Try different keywords
- Check if the court/year combination has cases
- Some searches may return no results

