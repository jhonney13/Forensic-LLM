#!/usr/bin/env python3
"""
Working Evidence Extractor - Simplified version that works with Gemma 3:4b
"""

import csv
import json
import requests
import time
import logging
import os
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
import argparse

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TaskProgressColumn, MofNCompleteColumn
from rich.panel import Panel
from rich.table import Table
from rich.logging import RichHandler
from rich import box

# Initialize Rich console
console = Console()

# Configure logging with Rich handler
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    datefmt='[%X]',
    handlers=[
        logging.FileHandler('evidence_extraction.log'),
        RichHandler(console=console, rich_tracebacks=True, show_path=False)
    ]
)
logger = logging.getLogger(__name__)

def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Best-effort JSON extraction from LLM text.
    - Strips markdown code fences
    - Attempts full parse, then object-slice parse
    Returns a dict on success, None on failure.
    """
    cleaned = text.strip()
    # Handle markdown code blocks
    if '```json' in cleaned:
        start = cleaned.find('```json') + 7
        end = cleaned.find('```', start)
        if end > start:
            cleaned = cleaned[start:end].strip()
    elif '```' in cleaned:
        start = cleaned.find('```') + 3
        end = cleaned.find('```', start)
        if end > start:
            cleaned = cleaned[start:end].strip()

    # Try direct JSON
    try:
        if cleaned.startswith('{') and cleaned.endswith('}'):
            return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try slicing from first { to last }
    try:
        start_idx = cleaned.find('{')
        end_idx = cleaned.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return json.loads(cleaned[start_idx:end_idx+1])
    except json.JSONDecodeError:
        pass

    return None

class WorkingEvidenceExtractor:
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "gemma3:4b"):
        self.ollama_url = ollama_url
        self.model = model
        self.session = requests.Session()
        
    def check_ollama_connection(self) -> bool:
        """Check if Ollama server is running and model is available"""
        with console.status("[bold cyan]Checking Ollama connection...", spinner="dots"):
            try:
                response = self.session.get(f"{self.ollama_url}/api/tags")
                if response.status_code != 200:
                    console.print("[red]✗[/red] Ollama server is not running or not accessible")
                    return False
                    
                models = response.json().get('models', [])
                model_names = [model['name'] for model in models]
                
                if self.model not in model_names:
                    console.print(f"[yellow]⚠[/yellow] Model [bold]{self.model}[/bold] not found. Available models: {', '.join(model_names)}")
                    return False
                    
                console.print(f"[green]✓[/green] Successfully connected to Ollama with model: [bold cyan]{self.model}[/bold cyan]")
                return True
                
            except Exception as e:
                console.print(f"[red]✗[/red] Failed to connect to Ollama: {e}")
                return False
    
    def extract_evidence(self, case_title: str, case_content: str) -> Dict[str, Any]:
        """Extract evidence from a single case using Ollama"""
        
        # Enhanced prompt for comprehensive evidence identification
        prompt = f"""Analyze this legal case and identify ALL types of evidence mentioned. Look for physical evidence, digital evidence, witness testimony, documents, forensic evidence, circumstantial evidence, and any other evidence types.

Case: {case_title[:200]}

Content: {case_content}

Return JSON with this structure:
{{
    "case_title": "Case title",
    "evidence_found": [
        {{
            "evidence": "detailed description of the evidence",
            "type": "physical/digital/witness/document/forensic/circumstantial/other",
            "strength": "strong/moderate/weak",
            "relevance": "high/medium/low",
            "source": "where the evidence came from"
        }}
    ],
    "physical_evidence": ["weapons", "documents", "clothing", "biological samples", "etc"],
    "digital_evidence": ["emails", "texts", "camera footage", "computer files", "etc"],
    "witness_testimony": ["eyewitness accounts", "expert testimony", "character witnesses", "etc"],
    "forensic_evidence": ["DNA", "fingerprints", "ballistics", "toxicology", "etc"],
    "documentary_evidence": ["contracts", "records", "certificates", "photographs", "etc"],
    "circumstantial_evidence": ["motive", "opportunity", "behavior patterns", "etc"],
    "key_facts": ["fact1", "fact2"],
    "legal_issues": ["issue1", "issue2"],
    "outcome": "decision",
    "summary": "brief summary"
}}"""

        try:
            response = self.session.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "max_tokens": 1000
                    }
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '').strip()
                
                # Debug: log the response
                if len(response_text) < 50:
                    console.print(f"[yellow]⚠[/yellow] Short response received: {response_text[:100]}")
                
                # Parse JSON using helper
                evidence_data = _extract_json_from_text(response_text)
                if evidence_data is not None:
                    return evidence_data
                console.print("[yellow]⚠[/yellow] JSON parsing failed. Returning raw response snippet.")
                return {
                    "case_title": case_title,
                    "raw_response": response_text,
                    "error": "JSON parsing failed"
                }
            else:
                console.print(f"[red]✗[/red] API request failed with status {response.status_code}")
                return {
                    "case_title": case_title,
                    "error": f"API request failed: {response.status_code}"
                }
                
        except Exception as e:
            console.print(f"[red]✗[/red] Error processing case {case_title[:50]}: {e}")
            return {
                "case_title": case_title,
                "error": str(e)
            }
    
    def process_csv(self, csv_file: str, output_file: str = None,
                   max_cases: Optional[int] = None, start_index: int = 0,
                   on_progress: Optional[Callable[[int, Optional[int]], None]] = None,
                   expected_total: Optional[int] = None):
        """Process the CSV file and extract evidence from each case.
        Streams rows instead of loading entire CSV into memory.
        """
        if not self.check_ollama_connection():
            console.print("[red]✗[/red] Cannot proceed without Ollama connection")
            return

        # Set default output file if not provided
        if output_file is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"../output/evidence_{timestamp}.json"
        
        # Ensure output directory exists
        import os
        output_dir = os.path.dirname(output_file)
        os.makedirs(output_dir, exist_ok=True)

        all_evidence: List[Dict[str, Any]] = []
        processed_count = 0
        started = False

        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                total_rows = sum(1 for _ in reader)
                file.seek(0)
                reader = csv.DictReader(file)

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    MofNCompleteColumn(),
                    TaskProgressColumn(),
                    TimeElapsedColumn(),
                    console=console
                ) as progress:
                    task = progress.add_task("[cyan]Processing cases...", total=min(total_rows - start_index, max_cases if max_cases else total_rows))
                    
                    for idx, row in enumerate(reader):
                        if idx < start_index:
                            continue
                        if max_cases is not None and processed_count >= max_cases:
                            break

                        case_title = str(row.get('Case Title', 'Unknown')).strip()
                        case_content = str(row.get('Case Content', '')).strip()

                        if not case_content or case_content == 'nan':
                            continue

                        if not started:
                            console.print("[green]✓[/green] Starting processing...")
                            started = True

                        progress.update(task, description=f"[cyan]Processing case {idx+1}: {case_title[:50]}...")

                        evidence = self.extract_evidence(case_title, case_content)
                        evidence['case_index'] = idx
                        evidence['case_link'] = row.get('Case Link', '')

                        all_evidence.append(evidence)
                        processed_count += 1
                        progress.update(task, advance=1)

                        # Invoke progress callback
                        if on_progress is not None:
                            try:
                                on_progress(processed_count, expected_total)
                            except Exception:
                                pass

                        # Save progress every 5 cases
                        if processed_count % 5 == 0:
                            self.save_progress(all_evidence, output_file)
                            console.print(f"[green]✓[/green] Saved progress: [bold cyan]{processed_count}[/bold cyan] cases processed")
                            time.sleep(1)

                # Save final results
                self.save_progress(all_evidence, output_file)
                success_panel = Panel(
                    f"[bold green]✓ Processing complete![/bold green]\n\n"
                    f"Processed [bold cyan]{processed_count}[/bold cyan] cases\n"
                    f"Results saved to: [bold]{output_file}[/bold]",
                    title="[bold green]Success[/bold green]",
                    border_style="green",
                    box=box.ROUNDED
                )
                console.print()
                console.print(success_panel)

        except Exception as e:
            console.print(f"[red]✗[/red] Error processing CSV file: {e}")
            if all_evidence:
                self.save_progress(all_evidence, output_file)
    
    def process_json(self, json_file: str, output_file: str = None,
                    max_cases: Optional[int] = None, start_index: int = 0,
                    on_progress: Optional[Callable[[int, Optional[int]], None]] = None,
                    expected_total: Optional[int] = None):
        """Process a JSON file from browse_scraper.py and extract evidence from each case."""
        if not self.check_ollama_connection():
            console.print("[red]✗[/red] Cannot proceed without Ollama connection")
            return

        # Set default output file if not provided
        if output_file is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Create output folder if it doesn't exist
            output_dir = "Output"
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"evidence_{timestamp}.json")
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        all_evidence: List[Dict[str, Any]] = []
        processed_count = 0
        started = False

        try:
            with console.status(f"[bold cyan]Loading JSON file: {json_file}...", spinner="dots"):
                with open(json_file, 'r', encoding='utf-8') as f:
                    cases = json.load(f)
            
            if not isinstance(cases, list):
                console.print("[red]✗[/red] JSON file must contain a list of cases")
                return
            
            total_cases = len(cases)
            console.print(f"[green]✓[/green] Found [bold cyan]{total_cases}[/bold cyan] cases in JSON file")
            
            total_to_process = min(total_cases - start_index, max_cases if max_cases else total_cases)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                task = progress.add_task("[cyan]Processing cases...", total=total_to_process)
                
                for idx, case in enumerate(cases):
                    if idx < start_index:
                        continue
                    if max_cases is not None and processed_count >= max_cases:
                        break

                    case_title = str(case.get('case_title', 'Unknown')).strip()
                    case_content = str(case.get('case_content', '')).strip()

                    if not case_content or case_content == 'nan' or not case_content:
                        console.print(f"[yellow]⚠[/yellow] Skipping case {idx+1}: No content available")
                        continue

                    if not started:
                        console.print("[green]✓[/green] Starting processing...")
                        started = True

                    progress.update(task, description=f"[cyan]Processing case {idx+1}/{total_cases}: {case_title[:50]}...")

                    evidence = self.extract_evidence(case_title, case_content)
                    evidence['case_index'] = idx
                    evidence['case_link'] = case.get('case_link', '')
                    evidence['court'] = case.get('court', '')
                    evidence['case_date'] = case.get('case_date', '')
                    # Preserve other metadata from original case
                    if 'year' in case:
                        evidence['year'] = case['year']
                    if 'period' in case:
                        evidence['period'] = case['period']
                    if 'keyword' in case:
                        evidence['keyword'] = case['keyword']

                    all_evidence.append(evidence)
                    processed_count += 1
                    progress.update(task, advance=1)

                    # Invoke progress callback
                    if on_progress is not None:
                        try:
                            on_progress(processed_count, expected_total or total_cases)
                        except Exception:
                            pass

                    # Save progress every 5 cases
                    if processed_count % 5 == 0:
                        self.save_progress(all_evidence, output_file)
                        console.print(f"[green]✓[/green] Saved progress: [bold cyan]{processed_count}[/bold cyan] cases processed")
                        time.sleep(1)

            # Save final results
            self.save_progress(all_evidence, output_file)
            success_panel = Panel(
                f"[bold green]✓ Processing complete![/bold green]\n\n"
                f"Processed [bold cyan]{processed_count}[/bold cyan] cases\n"
                f"Results saved to: [bold]{output_file}[/bold]",
                title="[bold green]Success[/bold green]",
                border_style="green",
                box=box.ROUNDED
            )
            console.print()
            console.print(success_panel)

        except FileNotFoundError:
            console.print(f"[red]✗[/red] JSON file not found: {json_file}")
        except json.JSONDecodeError as e:
            console.print(f"[red]✗[/red] Error parsing JSON file: {e}")
        except Exception as e:
            console.print(f"[red]✗[/red] Error processing JSON file: {e}")
            if all_evidence:
                self.save_progress(all_evidence, output_file)
    
    def save_progress(self, data: List[Dict], output_file: str):
        """Save current progress to file"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            console.print(f"[red]✗[/red] Error saving progress: {e}")

def resolve_path(path: str) -> str:
    """Resolve a path relative to the workspace root (parent of Analysis directory)."""
    script_dir = Path(__file__).parent.absolute()
    workspace_root = script_dir.parent
    
    # If path is absolute, return as-is
    if os.path.isabs(path):
        return path
    
    # Try relative to current working directory first
    if os.path.exists(path):
        return os.path.abspath(path)
    
    # Try relative to workspace root
    workspace_path = workspace_root / path
    if os.path.exists(workspace_path):
        return str(workspace_path)
    
    # Try relative to script directory
    script_path = script_dir / path
    if os.path.exists(script_path):
        return str(script_path)
    
    # Return original path if nothing found (will be handled by caller)
    return path

def find_latest_json_file() -> Optional[str]:
    """Find the most recent JSON file in Extractor/raw output directory."""
    import glob
    
    script_dir = Path(__file__).parent.absolute()
    workspace_root = script_dir.parent
    
    # Search patterns relative to workspace root
    search_paths = [
        workspace_root / "Extractor" / "raw output",
        workspace_root / "raw output",
        script_dir / "raw output",
        Path("Extractor/raw output"),
        Path("raw output"),
        Path("../Extractor/raw output"),
        Path("../raw output")
    ]
    
    json_files = []
    for search_path in search_paths:
        if search_path.exists() and search_path.is_dir():
            pattern = str(search_path / "*.json")
            found = glob.glob(pattern)
            json_files.extend(found)
    
    if json_files:
        # Get the most recent JSON file by modification time
        latest_json = max(json_files, key=os.path.getmtime)
        return os.path.abspath(latest_json)
    
    return None

def main():
    parser = argparse.ArgumentParser(description="Working Evidence Extractor - Supports CSV and JSON input")
    parser.add_argument("--csv", help="Input CSV file path")
    parser.add_argument("--json", help="Input JSON file path (from browse_scraper.py)")
    parser.add_argument("--output", help="Output JSON file path (default: Output folder with timestamp)")
    parser.add_argument("--model", default="gemma3:4b", help="Ollama model to use")
    parser.add_argument("--max-cases", type=int, help="Maximum number of cases to process")
    parser.add_argument("--start", type=int, default=0, help="Starting index")
    
    args = parser.parse_args()
    
    extractor = WorkingEvidenceExtractor(model=args.model)
    
    # Determine input type and file
    if args.json:
        # Process JSON file from browse_scraper.py
        resolved_json = resolve_path(args.json)
        if not os.path.exists(resolved_json):
            console.print(f"[red]✗[/red] JSON file not found: {args.json}")
            console.print(f"  Tried: {resolved_json}")
            return
        extractor.process_json(
            json_file=resolved_json,
            output_file=args.output,
            max_cases=args.max_cases,
            start_index=args.start
        )
    elif args.csv:
        # Process CSV file (original functionality)
        resolved_csv = resolve_path(args.csv)
        if not os.path.exists(resolved_csv):
            console.print(f"[red]✗[/red] CSV file not found: {args.csv}")
            console.print(f"  Tried: {resolved_csv}")
            return
        extractor.process_csv(
            csv_file=resolved_csv,
            output_file=args.output,
            max_cases=args.max_cases,
            start_index=args.start
        )
    else:
        # Auto-detect: look for JSON files in "raw output" folder first, then CSV
        with console.status("[bold cyan]Auto-detecting input file...", spinner="dots"):
            json_file = find_latest_json_file()
        
        if json_file:
            console.print(f"[green]✓[/green] Auto-detected JSON file: [bold]{json_file}[/bold]")
            extractor.process_json(
                json_file=json_file,
                output_file=args.output,
                max_cases=args.max_cases,
                start_index=args.start
            )
            return
        
        # Fallback to CSV search (original behavior)
        import glob
        script_dir = Path(__file__).parent.absolute()
        workspace_root = script_dir.parent
        
        csv_search_paths = [
            workspace_root / "raw",
            script_dir / "raw",
            Path("../raw")
        ]
        
        for csv_path in csv_search_paths:
            if csv_path.exists():
                csv_files = glob.glob(str(csv_path / "cases_*.csv"))
                if csv_files:
                    latest_csv = max(csv_files, key=os.path.getmtime)
                    console.print(f"[green]✓[/green] Auto-detected CSV file: [bold]{latest_csv}[/bold]")
                    extractor.process_csv(
                        csv_file=latest_csv,
                        output_file=args.output,
                        max_cases=args.max_cases,
                        start_index=args.start
                    )
                    return
        
        error_panel = Panel(
            "[bold red]No input file found![/bold red]\n\n"
            "Please specify --json or --csv, or place files in 'Extractor/raw output' folder.\n\n"
            "[bold]Usage examples:[/bold]\n"
            "  python evidence_extractor.py --json 'Extractor/raw output/search_cases_*.json'\n"
            "  python evidence_extractor.py --csv cases.csv\n"
            "  python evidence_extractor.py  (auto-detects latest JSON file)",
            title="[bold red]Error[/bold red]",
            border_style="red",
            box=box.ROUNDED
        )
        console.print()
        console.print(error_panel)
        return

if __name__ == "__main__":
    main()
