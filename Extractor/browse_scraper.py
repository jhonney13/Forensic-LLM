import re
import time
import json
import os
import warnings
import sys
from typing import List, Dict
from urllib.parse import quote_plus

import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, WebDriverException

# Suppress cleanup warnings from undetected_chromedriver
warnings.filterwarnings("ignore", category=ResourceWarning)

# Monkey-patch Chrome.__del__ to suppress Windows handle errors during garbage collection
try:
    _original_chrome_del = uc.Chrome.__del__
    
    def _suppressed_chrome_del(self):
        """Suppress OSError during Chrome driver cleanup to prevent 'Exception ignored' messages."""
        try:
            _original_chrome_del(self)
        except OSError:
            # Suppress Windows handle errors - these are harmless cleanup issues
            pass
        except Exception:
            # Suppress all other cleanup errors
            pass
    
    uc.Chrome.__del__ = _suppressed_chrome_del
except (AttributeError, TypeError):
    # If __del__ doesn't exist or can't be patched, that's okay
    pass

# Custom stderr filter to suppress "Exception ignored" messages from Chrome driver cleanup
# These messages are printed directly by Python's garbage collector
_original_stderr_write = sys.stderr.write

def _filtered_stderr_write(text):
    """Filter out Chrome driver cleanup error messages while preserving other output."""
    # Only suppress the specific "Exception ignored" messages from Chrome.__del__
    if isinstance(text, str):
        if "Exception ignored" in text:
            # Check if it's from Chrome.__del__ and involves OSError with invalid handle
            if "Chrome.__del__" in text or "undetected_chromedriver" in text:
                if "OSError" in text and ("WinError 6" in text or "handle is invalid" in text or "The handle is invalid" in text):
                    return  # Suppress this specific cleanup error
    # Write all other messages normally (including Rich console output)
    _original_stderr_write(text)

# Apply the filter to suppress cleanup errors
sys.stderr.write = _filtered_stderr_write

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TaskProgressColumn
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt, IntPrompt, Confirm
from rich import box
from rich.live import Live
from rich.align import Align


# ------------- CONFIG -------------

# Theme configuration
THEMES = {
    "dark": {
        "primary": "cyan",
        "success": "green",
        "warning": "yellow",
        "error": "red",
        "info": "blue",
        "accent": "magenta",
        "panel_style": "cyan",
        "table_style": "bold cyan",
    },
    "light": {
        "primary": "blue",
        "success": "green",
        "warning": "yellow",
        "error": "red",
        "info": "cyan",
        "accent": "magenta",
        "panel_style": "blue",
        "table_style": "bold blue",
    },
    "colorful": {
        "primary": "bright_cyan",
        "success": "bright_green",
        "warning": "bright_yellow",
        "error": "bright_red",
        "info": "bright_blue",
        "accent": "bright_magenta",
        "panel_style": "bright_cyan",
        "table_style": "bold bright_cyan",
    },
    "minimal": {
        "primary": "white",
        "success": "green",
        "warning": "yellow",
        "error": "red",
        "info": "white",
        "accent": "white",
        "panel_style": "white",
        "table_style": "bold white",
    }
}

# Default theme (can be changed)
DEFAULT_THEME = "dark"
current_theme = THEMES[DEFAULT_THEME]

# Initialize Rich console with theme
console = Console()

BASE_BROWSE_URL = "https://indiankanoon.org/browse/"

def set_theme(theme_name: str = None):
    """Set the UI theme. Options: dark, light, colorful, minimal"""
    global current_theme
    if theme_name and theme_name in THEMES:
        current_theme = THEMES[theme_name]
        return True
    return False

def get_style(category: str) -> str:
    """Get style string for a category based on current theme"""
    return current_theme.get(category, "white")

# How many case links to follow from the court page (None = all on first page)
MAX_CASES = 20

# Timing configuration to control speed
PAGE_LOAD_WAIT = 1.0  # seconds to wait after navigation
SHORT_WAIT = 0.3      # small waits for intermediate steps
CF_MAX_WAIT = 15      # max seconds to wait for Cloudflare / intermediate pages


# ------------- BROWSER SETUP -------------

def get_driver() -> uc.Chrome:
    options = uc.ChromeOptions()
    options.headless = True
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")
    driver = uc.Chrome(options=options)
    return driver


def safe_quit_driver(driver) -> None:
    """
    Safely close and cleanup a Chrome driver to prevent cleanup warnings.
    Suppresses all errors during cleanup to avoid 'Exception ignored' messages.
    This helps prevent Windows handle errors during garbage collection.
    """
    if driver is None:
        return
    
    try:
        # Try to close all windows and quit the driver properly
        if hasattr(driver, 'window_handles'):
            try:
                # Close all windows except the main one
                handles = driver.window_handles
                for handle in handles[1:]:
                    try:
                        driver.switch_to.window(handle)
                        driver.close()
                    except:
                        pass
                # Switch back to main window if it exists
                if handles:
                    try:
                        driver.switch_to.window(handles[0])
                    except:
                        pass
            except:
                pass
        
        # Quit the driver
        driver.quit()
    except (OSError, AttributeError, Exception):
        # Suppress all errors - handles may already be invalid
        # This is expected on Windows when handles are cleaned up
        pass
    finally:
        # Give Windows a moment to clean up handles before garbage collection
        time.sleep(0.2)
        # Try to clear service references to help with cleanup
        try:
            if hasattr(driver, 'service') and driver.service:
                try:
                    driver.service.stop()
                except:
                    pass
                try:
                    driver.service = None
                except:
                    pass
        except:
            pass
        # Clear driver reference to help garbage collection
        try:
            if hasattr(driver, '_driver'):
                driver._driver = None
        except:
            pass


def wait_for_cloudflare(driver, max_wait: int = CF_MAX_WAIT, show_status: bool = False) -> bool:
    """Wait for Cloudflare / intermediate challenges to finish.
    Silent by default - no messages unless explicitly requested.
    """
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            title = driver.title.lower()
            if "just a moment" in title or "verifying" in title:
                time.sleep(SHORT_WAIT)
                continue
            # Heuristic: once we see indiankanoon main UI or court names, continue
            if "indiankanoon" in title or "indian kanoon" in title or "browse" in title:
                return True
            time.sleep(SHORT_WAIT)
        except Exception:
            time.sleep(SHORT_WAIT)
            continue

    return False


# ------------- PARSING HELPERS -------------

def extract_case_title(soup: BeautifulSoup) -> str:
    """
    Try to extract a clean case title from a /doc/... page.
    Strategy:
      1. Prefer an <h1> that looks like a case title (not the site header).
      2. Fallback: first text line that looks like "A vs B on <date>" or contains ' vs ' / ' v. '.
    """
    # 1. Try <h1> elements, skipping generic site header like "Indian Kanoon - Search engine for Indian Law"
    for h1 in soup.find_all("h1"):
        title = h1.get_text(strip=True)
        if not title:
            continue
        lower = title.lower()
        if "indian kanoon - search engine for indian law" in lower:
            continue
        # Heuristic: treat this as a case title
        return title

    # 2. Fallback: search in visible text lines for something that looks like a case title
    body_text = soup.get_text(separator="\n")
    candidate = ""
    for line in body_text.splitlines():
        line = line.strip()
        if not line:
            continue
        lower = line.lower()
        # Typical pattern: "<Party A> vs <Party B> on <date>"
        if (" vs " in lower or " v. " in lower) and " on " in lower:
            candidate = line
            break
        # Otherwise, remember the first reasonable 'vs' line as backup
        if not candidate and (" vs " in lower or " v. " in lower):
            candidate = line
    if candidate:
        return candidate

    return ""


def extract_case_date(soup: BeautifulSoup) -> str:
    """
    Try to extract the case date from a /doc/... page.
    Strategy:
      - Look for a line starting with 'Date :' and grab the rest of the line.
    """
    body_text = soup.get_text(separator="\n")

    # Direct search for 'Date :'
    for line in body_text.splitlines():
        if "Date" in line:
            m = re.search(r"Date\s*:\s*([^\n]+)", line)
            if m:
                return m.group(1).strip()

    # Fallback: search anywhere in text
    m2 = re.search(r"Date\s*:\s*([^\n]+)", body_text)
    if m2:
        return m2.group(1).strip()

    return ""


def get_full_judgment_text(driver, case_url: str, show_status: bool = False) -> str:
    """Open a /doc/... case page, click 'View Complete document' if present, and return full body text."""
    try:
        if show_status:
            with console.status(f"[bold cyan]Opening case URL...", spinner="dots"):
                driver.get(case_url)
                time.sleep(PAGE_LOAD_WAIT)
        else:
            driver.get(case_url)
            time.sleep(PAGE_LOAD_WAIT)

        # Try to click "View Complete document" if available
        try:
            view_complete = driver.find_element(By.LINK_TEXT, "View Complete document")
            view_complete.click()
            time.sleep(PAGE_LOAD_WAIT)
        except NoSuchElementException:
            # Some judgments may already be full; that's fine
            pass

        # Scroll to ensure lazy-loaded content is present
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SHORT_WAIT)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        body = soup.find("body")
        if not body:
            return ""

        # Use separator to preserve paragraph breaks
        text = body.get_text(strip=True, separator="\n")
        return text
    except (WebDriverException, Exception) as e:
        console.print(f"[red]✗ Error while fetching full judgment from {case_url}: {e}[/red]")
        return ""


# ------------- MAIN SCRAPING LOGIC -------------

def select_court(driver, court_name: str) -> None:
    """From the browse page, click on the given court link."""
    with console.status(f"[bold cyan]Loading browse page...", spinner="dots"):
        driver.get(BASE_BROWSE_URL)

    if not wait_for_cloudflare(driver):
        raise RuntimeError("Could not bypass Cloudflare / intermediate page at browse URL")

    time.sleep(PAGE_LOAD_WAIT)

    try:
        court_link = driver.find_element(By.LINK_TEXT, court_name)
        console.print(f"[{get_style('success')}]✓[/{get_style('success')}] Clicking court link: [bold]{court_name}[/bold]")
        court_link.click()
    except NoSuchElementException:
        raise RuntimeError(f"Could not find court link with text '{court_name}' on browse page")

    time.sleep(3)


def discover_years(driver) -> List[Dict[str, str]]:
    """
    After clicking a court, discover all available years from the page.
    Returns a list of dicts: [{"year": "2024", "text": "2024 (70579)", "href": "/browse/..."}, ...]
    """
    soup = BeautifulSoup(driver.page_source, "html.parser")
    anchors = soup.find_all("a", href=True)
    
    years: List[Dict[str, str]] = []
    seen_years = set()
    
    for a in anchors:
        text = a.get_text(strip=True)
        href = a.get("href", "")
        
        # Look for year patterns like "2024 (70579)" or just "2024"
        # Year should be 4 digits, possibly followed by space and count in parentheses
        year_match = re.match(r"^(\d{4})\s*(?:\([^)]+\))?$", text)
        if year_match:
            year = year_match.group(1)
            # Only consider years from 1900 to 2100 (reasonable range)
            try:
                year_int = int(year)
                if 1900 <= year_int <= 2100 and year not in seen_years:
                    seen_years.add(year)
                    years.append({
                        "year": year,
                        "text": text,
                        "href": href
                    })
            except ValueError:
                continue
    
    # Sort by year descending (newest first)
    years.sort(key=lambda x: int(x["year"]), reverse=True)
    
    console.print(f"[{get_style('success')}]✓[/{get_style('success')}] Discovered [bold {get_style('primary')}]{len(years)}[/bold {get_style('primary')}] years for this court")
    return years


def select_year(driver, year_text: str) -> None:
    """Click on a year link from the court page."""
    try:
        year_link = driver.find_element(By.LINK_TEXT, year_text)
        console.print(f"[{get_style('success')}]✓[/{get_style('success')}] Clicking year link: [bold]{year_text}[/bold]")
        year_link.click()
        time.sleep(PAGE_LOAD_WAIT)
    except NoSuchElementException:
        raise RuntimeError(f"Could not find year link with text '{year_text}' on court page")


def discover_periods(driver) -> List[str]:
    """
    On a selected year page, discover period filters like:
      - Entire Year, January, February, ..., December
    Returns a list of visible link texts.
    """
    soup = BeautifulSoup(driver.page_source, "html.parser")
    anchors = soup.find_all("a")

    candidates = []
    valid_labels = {
        "entire year",
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    }

    seen = set()
    for a in anchors:
        raw_text = a.get_text(strip=True)
        if not raw_text:
            continue

        # Allow patterns like "January" or "January (1234)"
        m = re.match(r"^([A-Za-z ]+?)(?:\s*\([^)]+\))?$", raw_text)
        if not m:
            continue

        label = m.group(1).strip()
        lower = label.lower()
        if lower in valid_labels and label not in seen:
            seen.add(label)
            candidates.append(label)

    # Preserve natural order as it appears on the page (already built that way)
    console.print(f"[{get_style('success')}]✓[/{get_style('success')}] Discovered [bold {get_style('primary')}]{len(candidates)}[/bold {get_style('primary')}] period filters for this year")
    return candidates


def select_period(driver, period_text: str) -> None:
    """Click on a period (month/entire year) link on the year page."""
    try:
        link = driver.find_element(By.LINK_TEXT, period_text)
        console.print(f"[{get_style('success')}]✓[/{get_style('success')}] Clicking period link: [bold]{period_text}[/bold]")
        link.click()
        time.sleep(PAGE_LOAD_WAIT)
    except NoSuchElementException:
        raise RuntimeError(f"Could not find period link with text '{period_text}' on year page")


def court_to_doctype_token(court_name: str) -> str:
    """
    Best-effort mapping from a court name to the doctypes token used in Indian Kanoon search.
    Examples:
      'Gujarat High Court'   -> 'gujarat'
      'Jharkhand High Court' -> 'jharkhand'
    """
    name = court_name.lower().strip()
    # High Courts: take part before 'high court'
    if "high court" in name:
        prefix = name.split("high court")[0].strip()
        token = prefix.replace(" ", "")
        return token or "highcourt"
    # Fallback: remove spaces
    return name.replace(" ", "")


def collect_case_links_from_court_page(driver) -> List[str]:
    """
    Collect /doc/... links from the court's listing page (or year page).
    We restrict to unique hrefs that contain '/doc/' (full judgments).
    """
    soup = BeautifulSoup(driver.page_source, "html.parser")
    anchors = soup.find_all("a", href=True)

    links: List[str] = []
    seen = set()
    for a in anchors:
        href = a["href"]
        if "/doc/" not in href:
            continue
        # Normalize to full URL
        full_url = "https://indiankanoon.org" + href if href.startswith("/") else href
        if full_url in seen:
            continue
        seen.add(full_url)
        links.append(full_url)

    console.print(f"[{get_style('success')}]✓[/{get_style('success')}] Found [bold {get_style('primary')}]{len(links)}[/bold {get_style('primary')}] unique /doc/ links on page")

    if MAX_CASES is not None:
        links = links[:MAX_CASES]
        console.print(f"[{get_style('warning')}]⚠[/{get_style('warning')}] Limiting to first [bold]{len(links)}[/bold] cases (MAX_CASES={MAX_CASES})")

    return links


def discover_courts(driver) -> Dict[str, List[str]]:
    """
    Parse the browse page and automatically discover courts.

    Returns a dict:
      {
        "supreme": [list of court names containing 'Supreme Court'],
        "high": [list of court names containing 'High Court'],
        "other": [all other court names],
      }
    """
    with console.status("[bold cyan]Discovering courts from browse page...", spinner="dots"):
        driver.get(BASE_BROWSE_URL)
        time.sleep(PAGE_LOAD_WAIT)
    
    # Silently wait for Cloudflare (no warnings needed)
    wait_for_cloudflare(driver)
    
    time.sleep(PAGE_LOAD_WAIT)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    supreme: List[str] = []
    high: List[str] = []
    other: List[str] = []

    for a in soup.find_all("a"):
        name = a.get_text(strip=True)
        if not name:
            continue

        lowered = name.lower()
        if "supreme court" in lowered:
            if name not in supreme:
                supreme.append(name)
        elif "high court" in lowered:
            if name not in high:
                high.append(name)
        else:
            if name not in other:
                other.append(name)

    # Sort for stable ordering
    supreme.sort()
    high.sort()
    other.sort()

    console.print(f"[{get_style('success')}]✓[/{get_style('success')}] Discovered [bold {get_style('primary')}]{len(supreme)}[/bold {get_style('primary')}] Supreme Court entries, [bold {get_style('primary')}]{len(high)}[/bold {get_style('primary')}] High Courts.")

    return {"supreme": supreme, "high": high, "other": other}


def scrape_court_cases(court_name: str, year: str = None, period: str = None) -> List[Dict]:
    """
    High-level function:
      - Open browse page
      - Click selected court
      - If year provided, click selected year
      - Collect /doc/... links
      - For each link, fetch title, date, full judgment text
    """
    driver = None
    results: List[Dict] = []

    try:
        driver = get_driver()
        select_court(driver, court_name)

        # If year is provided, select it
        if year:
            select_year(driver, year)

        # If period (month/entire year) is provided, select it
        if period:
            select_period(driver, period)

        case_links = collect_case_links_from_court_page(driver)
        if not case_links:
            print("No case links found for this court/year.")
            return []

        for idx, url in enumerate(case_links, start=1):
            try:
                # Load case page
                driver.get(url)
                time.sleep(PAGE_LOAD_WAIT)

                soup = BeautifulSoup(driver.page_source, "html.parser")

                title = extract_case_title(soup)
                date = extract_case_date(soup)

                # Ensure we capture full text (may click 'View Complete document')
                content = get_full_judgment_text(driver, url)

                console.print(f"[{get_style('success')}]✓[/{get_style('success')}] [{idx}/{len(case_links)}] Scraped case: [bold]{title[:80]}[/bold]")

                result_dict = {
                    "court": court_name,
                    "case_title": title,
                    "case_date": date,
                    "case_link": url,
                    "case_content": content,
                }
                if year:
                    result_dict["year"] = year.split()[0] if year else None
                if period:
                    result_dict["period"] = period
                results.append(result_dict)

                # Be polite; short delay between cases
                time.sleep(2)
            except Exception as e:
                console.print(f"[{get_style('error')}]✗[/{get_style('error')}] Error scraping case {idx} at {url}: {e}")
                continue
    finally:
        safe_quit_driver(driver)
        driver = None  # Help garbage collection

    return results


def save_cases_to_json(cases: List[Dict], output_path: str) -> None:
    # Ensure the directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    with console.status(f"[bold cyan]Saving {len(cases)} cases to file...", spinner="dots"):
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(cases, f, ensure_ascii=False, indent=2)
    console.print(f"[{get_style('success')}]✓[/{get_style('success')}] Saved [bold {get_style('primary')}]{len(cases)}[/bold {get_style('primary')}] cases to [bold]{output_path}[/bold]")


def slugify_court_name(name: str) -> str:
    """Create a safe slug from court name for filenames."""
    # Lowercase, replace non-alphanumeric with underscore
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower())
    slug = slug.strip("_")
    return slug or "court"


def extract_case_links_from_search_page(driver) -> List[str]:
    """
    Extract case links from a search results page.
    Looks for links containing '/doc/' which are the full case document links.
    """
    soup = BeautifulSoup(driver.page_source, "html.parser")
    anchors = soup.find_all("a", href=True)
    
    case_links = []
    seen = set()
    
    for a in anchors:
        href = a.get("href", "")
        if "/doc/" not in href:
            continue
        
        # Normalize to full URL
        full_url = "https://indiankanoon.org" + href if href.startswith("/") else href
        
        # Remove query parameters and fragments to get unique case IDs
        base_url = full_url.split("?")[0].split("#")[0]
        
        if base_url not in seen:
            seen.add(base_url)
            case_links.append(base_url)
    
    return case_links


def get_next_page_url(driver) -> str:
    """
    Check if there's a 'Next' pagination link and return its URL.
    Returns empty string if no next page found.
    """
    try:
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # 1) Preferred: explicit "Next" text (allows surrounding whitespace)
        next_link = soup.find("a", text=re.compile(r"\bNext\b", re.I))
        if next_link and next_link.get("href"):
            href = next_link["href"]
            return "https://indiankanoon.org" + href if href.startswith("/") else href

        # 2) Fallback: any link with 'pagenum=' in href (Indian Kanoon style)
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "pagenum=" in href:
                # Skip links that don't look like forward navigation if needed,
                # but for now, we assume any pagenum link after current page is okay.
                return "https://indiankanoon.org" + href if href.startswith("/") else href
    except Exception:
        pass

    return ""


def get_search_pagination_info(driver) -> Dict[str, int]:
    """
    Parse the search results header like:
      '1 - 10 of 467 (0.02 seconds)'
    and return a dict with total_cases, per_page, total_pages.
    """
    info = {"total_cases": 0, "per_page": 0, "total_pages": 0}
    try:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        # Find the text block that contains "of N"
        text = soup.get_text(separator="\n")
        m = re.search(r"(\d+)\s*-\s*(\d+)\s*of\s*(\d+)", text)
        if not m:
            return info
        start = int(m.group(1))
        end = int(m.group(2))
        total = int(m.group(3))
        per_page = end - start + 1 if end >= start else 0
        if per_page <= 0:
            return info
        total_pages = (total + per_page - 1) // per_page
        info["total_cases"] = total
        info["per_page"] = per_page
        info["total_pages"] = total_pages
        return info
    except Exception:
        return info


def scrape_search_results(
    driver,
    search_url: str,
    max_pages: int,
    court_name: str,
    year: str = None,
    period: str = None,
    keyword: str = None
) -> List[Dict]:
    """
    Scrape cases from search results pages.
    
    Args:
        driver: Selenium WebDriver instance
        search_url: Initial search URL
        max_pages: Maximum number of result pages to scrape
        court_name: Court name for metadata
        year: Year filter (optional)
        period: Period filter (optional)
        keyword: Search keyword (optional)
    
    Returns:
        List of case dictionaries with title, date, link, and content
    """
    console.print(f"\n[bold cyan]Loading search results page...[/bold cyan]")
    driver.get(search_url)
    
    # Silently wait for Cloudflare (no warnings needed)
    wait_for_cloudflare(driver)
    
    time.sleep(PAGE_LOAD_WAIT)
    
    all_cases = []
    current_page = 1
    current_search_url = search_url  # Track current search results page URL
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task(f"[cyan]Scraping pages...", total=max_pages)
        
        while current_page <= max_pages:
            progress.update(task, description=f"[cyan]Scraping page {current_page} of {max_pages}...")
            
            # Make sure we're on the search results page
            driver.get(current_search_url)
            time.sleep(PAGE_LOAD_WAIT)
            
            # Extract case links from current search results page
            case_links = extract_case_links_from_search_page(driver)
            console.print(f"[{get_style('success')}]✓[/{get_style('success')}] Found [bold {get_style('primary')}]{len(case_links)}[/bold {get_style('primary')}] case links on page {current_page}")
            
            if not case_links:
                console.print(f"[{get_style('warning')}]⚠[/{get_style('warning')}] No case links found on page {current_page}. Stopping.")
                break
            
            # Scrape each case one by one
            case_task = progress.add_task(f"[yellow]Processing cases on page {current_page}...", total=len(case_links))
            
            for idx, case_url in enumerate(case_links, start=1):
                try:
                    progress.update(case_task, description=f"[yellow]Scraping case {idx}/{len(case_links)}...")
                    
                    # Step 1: Go inside the case page
                    driver.get(case_url)
                    time.sleep(PAGE_LOAD_WAIT)
                    
                    # Step 2: Try to click "View Complete document" if available
                    try:
                        view_complete = driver.find_element(By.LINK_TEXT, "View Complete document")
                        view_complete.click()
                        time.sleep(SHORT_WAIT)
                    except NoSuchElementException:
                        pass
                    
                    # Step 3: Scroll to load lazy content
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(SHORT_WAIT)
                    
                    # Step 4: Parse and extract all content
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    
                    title = extract_case_title(soup)
                    date = extract_case_date(soup)

                    # Get full judgment text (select all content)
                    body = soup.find("body")
                    content = body.get_text(strip=True, separator="\n") if body else ""

                    # Step 5: Verify this case belongs to the selected court
                    page_text_lower = content.lower()
                    expected_court_lower = court_name.lower()
                    if expected_court_lower not in page_text_lower:
                        console.print(f"    [{get_style('warning')}]↷[/{get_style('warning')}] Skipping case (court name not found in document body).")
                        # Go back to search results before continuing
                        driver.get(current_search_url)
                        time.sleep(SHORT_WAIT)
                        progress.update(case_task, advance=1)
                        continue

                    # Step 6: Save case data
                    case_dict = {
                        "court": court_name,
                        "case_title": title,
                        "case_date": date,
                        "case_link": case_url,
                        "case_content": content,
                    }
                    
                    if year:
                        case_dict["year"] = year.split()[0] if isinstance(year, str) else year
                    if period:
                        case_dict["period"] = period
                    if keyword:
                        case_dict["keyword"] = keyword
                    
                    all_cases.append(case_dict)
                    console.print(f"    [{get_style('success')}]✓[/{get_style('success')}] Scraped and saved: [bold]{title[:60]}...[/bold]")
                    
                    # Step 7: Go back to search results page before next case
                    driver.get(current_search_url)
                    time.sleep(SHORT_WAIT)
                    
                    progress.update(case_task, advance=1)
                    
                except Exception as e:
                    console.print(f"    [{get_style('error')}]✗[/{get_style('error')}] Error scraping case {idx}: {e}")
                    # Try to go back to search results even on error
                    try:
                        driver.get(current_search_url)
                        time.sleep(SHORT_WAIT)
                    except:
                        pass
                    progress.update(case_task, advance=1)
                    continue
            
            progress.remove_task(case_task)
            
            # Step 8: After all cases on current page are done, move to next page
            if current_page < max_pages:
                # Make sure we're on search results page to find "Next" link
                driver.get(current_search_url)
                time.sleep(SHORT_WAIT)
                
                next_url = get_next_page_url(driver)
                if next_url:
                    console.print(f"\n[green]✓[/green] All cases on page {current_page} completed. Moving to next page...")
                    current_search_url = next_url  # Update tracked URL
                    current_page += 1
                    progress.update(task, advance=1)
                else:
                    console.print(f"\n[yellow]⚠[/yellow] No more pages found. Scraped {current_page} page(s).")
                    break
            else:
                progress.update(task, advance=1)
                break
    
    return all_cases


def main():
    # Use default theme (dark) - no selection needed
    set_theme(DEFAULT_THEME)
    
    # Show welcome banner
    welcome_panel = Panel(
        "[bold]Forensic-LLM[/bold]\n"
        "A tool for scraping legal cases from Indian Kanoon and extracting evidence using AI.",
        title="[bold]Welcome[/bold]",
        border_style=get_style("panel_style"),
        box=box.ROUNDED,
        padding=(1, 2)
    )
    console.print()
    console.print(welcome_panel)
    console.print()
    
    # Use a temporary browser instance just to discover courts for menu
    temp_driver = None
    try:
        temp_driver = get_driver()
        courts = discover_courts(temp_driver)
    finally:
        safe_quit_driver(temp_driver)
        temp_driver = None  # Help garbage collection

    supreme = courts.get("supreme", [])
    high = courts.get("high", [])

    # Build menu of courts (Supreme + High Courts)
    menu_items: List[str] = supreme + high

    # Create a beautiful table for court selection
    table = Table(
        title=f"[bold {get_style('table_style')}]Select a Court to Scrape[/bold {get_style('table_style')}]",
        box=box.ROUNDED,
        show_header=True,
        header_style=f"bold {get_style('accent')}"
    )
    table.add_column("No.", style=get_style("primary"), width=5)
    table.add_column("Court Name", style=get_style("success"))
    table.add_column("Type", style=get_style("warning"))

    if supreme:
        for idx, name in enumerate(supreme, start=1):
            table.add_row(str(idx), name, "Supreme Court")

    offset = len(supreme)
    if high:
        for i, name in enumerate(high, start=1):
            table.add_row(str(offset + i), name, "High Court")

    console.print()
    console.print(table)

    total = len(menu_items)
    if total == 0:
        console.print(f"[{get_style('error')}]✗ No courts discovered on browse page. Exiting.[/{get_style('error')}]")
        return

    # Simple input loop
    while True:
        choice = IntPrompt.ask(f"\n[bold {get_style('primary')}]Enter the number of the court[/bold {get_style('primary')}] (1-{total})", default=1)
        if 1 <= choice <= total:
            break
        console.print(f"[{get_style('error')}]Please enter a number between 1 and {total}.[/{get_style('error')}]")

    selected_court = menu_items[choice - 1]
    console.print(f"\n[{get_style('success')}]✓[/{get_style('success')}] You selected: [bold {get_style('primary')}]{selected_court}[/bold {get_style('primary')}]")

    # Now discover years for this court, and optionally periods (months)
    temp_driver2 = None
    selected_year = None
    selected_period = None
    try:
        temp_driver2 = get_driver()
        select_court(temp_driver2, selected_court)
        years = discover_years(temp_driver2)
        
        if years:
            year_table = Table(
                title=f"[bold {get_style('table_style')}]Available Years[/bold {get_style('table_style')}]",
                box=box.ROUNDED,
                show_header=True,
                header_style=f"bold {get_style('accent')}"
            )
            year_table.add_column("No.", style=get_style("primary"), width=5)
            year_table.add_column("Year", style=get_style("success"))
            
            for idx, year_info in enumerate(years, start=1):
                year_table.add_row(str(idx), year_info['text'])
            
            console.print()
            console.print(year_table)
            
            total_years = len(years)
            while True:
                year_choice_str = Prompt.ask(f"\n[bold cyan]Enter the number of the year[/bold cyan] (1-{total_years}), or press Enter to skip", default="")
                
                if not year_choice_str:
                    console.print("[yellow]⚠[/yellow] Skipping year selection, will scrape all cases from court page.")
                    break
                
                try:
                    year_choice = int(year_choice_str)
                except ValueError:
                    console.print("[red]Please enter a valid number.[/red]")
                    continue
                
                if 1 <= year_choice <= total_years:
                    selected_year = years[year_choice - 1]["text"]
                    console.print(f"[green]✓[/green] You selected year: [bold cyan]{selected_year}[/bold cyan]")
                    # Click into that year so we can discover periods
                    select_year(temp_driver2, selected_year)
                    # Discover periods (Entire Year, January, ..., December)
                    periods = discover_periods(temp_driver2)
                    if periods:
                        period_table = Table(
                            title=f"[bold {get_style('table_style')}]Available Periods[/bold {get_style('table_style')}]",
                            box=box.ROUNDED,
                            show_header=True,
                            header_style=f"bold {get_style('accent')}"
                        )
                        period_table.add_column("No.", style=get_style("primary"), width=5)
                        period_table.add_column("Period", style=get_style("success"))
                        
                        for p_idx, p_text in enumerate(periods, start=1):
                            period_table.add_row(str(p_idx), p_text)
                        
                        console.print()
                        console.print(period_table)
                        
                        total_periods = len(periods)
                        while True:
                            period_choice_str = Prompt.ask(f"\n[bold cyan]Enter the number of the period[/bold cyan] (1-{total_periods}), or press Enter to skip", default="")
                            if not period_choice_str:
                                console.print("[yellow]⚠[/yellow] Skipping period selection, will scrape all cases for the selected year.")
                                break
                            try:
                                period_choice = int(period_choice_str)
                            except ValueError:
                                console.print("[red]Please enter a valid number.[/red]")
                                continue
                            if 1 <= period_choice <= total_periods:
                                selected_period = periods[period_choice - 1]
                                console.print(f"[green]✓[/green] You selected period: [bold cyan]{selected_period}[/bold cyan]")
                                break
                            console.print(f"[{get_style('error')}]Please enter a number between 1 and {total_periods}.[/{get_style('error')}]")
                    else:
                        console.print("[yellow]⚠[/yellow] No period filters found for this year. Proceeding without period filter.")
                    break
                console.print(f"[{get_style('error')}]Please enter a number between 1 and {total_years}.[/{get_style('error')}]")
        else:
            console.print("[yellow]⚠[/yellow] No years found on court page. Proceeding without year/period filter.")
    finally:
        safe_quit_driver(temp_driver2)
        temp_driver2 = None  # Help garbage collection

    # At this point we STOP before scraping and just show the final selection
    summary_table = Table(
        title=f"[bold {get_style('table_style')}]Navigation Summary[/bold {get_style('table_style')}]",
        box=box.ROUNDED,
        show_header=False
    )
    summary_table.add_column("Field", style=get_style("primary"), width=15)
    summary_table.add_column("Value", style=get_style("success"))
    
    summary_table.add_row("Court", selected_court)
    summary_table.add_row("Year", selected_year if selected_year else "(none selected)")
    summary_table.add_row("Period", selected_period if selected_period else "(none selected)")
    
    console.print()
    console.print(summary_table)

    # Ask user for target keyword to build a search URL
    keyword = Prompt.ask(
        f"\n[bold {get_style('primary')}]Enter target keyword for search[/bold {get_style('primary')}] (e.g. murder, rape, robbery), or press Enter to finish",
        default=""
    ).strip()

    if not keyword:
        console.print("[yellow]⚠[/yellow] No keyword entered. Exiting without opening search page.")
        return

    # Build a search query similar to: 'murder doctypes:gujarat year:2016'
    year_token = selected_year.split()[0] if selected_year else ""
    doctypes_token = court_to_doctype_token(selected_court)

    query_parts = [keyword]
    if doctypes_token:
        query_parts.append(f"doctypes:{doctypes_token}")
    if year_token:
        query_parts.append(f"year:{year_token}")

    search_query = " ".join(query_parts)
    encoded_query = quote_plus(search_query)
    search_url = f"https://indiankanoon.org/search/?formInput={encoded_query}"

    search_info = Table(
        title=f"[bold {get_style('table_style')}]Search Configuration[/bold {get_style('table_style')}]",
        box=box.ROUNDED,
        show_header=False
    )
    search_info.add_column("Field", style=get_style("primary"), width=10)
    search_info.add_column("Value", style=get_style("success"))
    search_info.add_row("Query", search_query)
    search_info.add_row("URL", search_url)
    
    console.print()
    console.print(search_info)

    # Quickly inspect the search results to show total pages/cases
    temp_driver3 = None
    total_pages_hint = None
    total_cases_hint = None
    try:
        with console.status("[bold cyan]Inspecting search results...", spinner="dots"):
            temp_driver3 = get_driver()
            temp_driver3.get(search_url)
            time.sleep(PAGE_LOAD_WAIT)
            page_info = get_search_pagination_info(temp_driver3)
            total_cases_hint = page_info.get("total_cases") or 0
            total_pages_hint = page_info.get("total_pages") or 0
        
        # Silently wait for Cloudflare (no warnings needed)
        wait_for_cloudflare(temp_driver3, show_status=False)
        if total_pages_hint and total_cases_hint:
            console.print(
                f"\n[green]✓[/green] Search results show approximately [bold cyan]{total_cases_hint}[/bold cyan] cases "
                f"across [bold cyan]{total_pages_hint}[/bold cyan] page(s) (~{page_info.get('per_page', 0)} cases per page)."
            )
        else:
            console.print("[yellow]⚠[/yellow] Could not automatically determine total pages/cases from search results.")
    finally:
        safe_quit_driver(temp_driver3)
        temp_driver3 = None  # Help garbage collection

    # Ask user how many pages to scrape, using the detected total pages as a hint
    if total_pages_hint and total_pages_hint > 0:
        max_pages = IntPrompt.ask(
            f"\n[bold {get_style('primary')}]How many pages of results to scrape?[/bold {get_style('primary')}] (Detected up to {total_pages_hint} pages)",
            default=1
        )
    else:
        max_pages = IntPrompt.ask(
            f"\n[bold {get_style('primary')}]How many pages of results to scrape?[/bold {get_style('primary')}]",
            default=1
        )

    # Scrape cases from search results
    driver = None
    all_cases = []
    try:
        driver = get_driver()
        all_cases = scrape_search_results(driver, search_url, max_pages, selected_court, selected_year, selected_period, keyword)
    finally:
        safe_quit_driver(driver)
        driver = None  # Help garbage collection

    # Save results
    if all_cases:
        # Ensure "raw output" folder exists
        output_folder = "raw output"
        os.makedirs(output_folder, exist_ok=True)
        
        slug = slugify_court_name(selected_court)
        year_suffix = f"_{selected_year.split()[0]}" if selected_year else ""
        period_suffix = f"_{selected_period.lower().replace(' ', '_')}" if selected_period else ""
        keyword_suffix = f"_{keyword.lower().replace(' ', '_')}" if keyword else ""
        output_file = os.path.join(output_folder, f"search_cases_{slug}{year_suffix}{period_suffix}{keyword_suffix}.json")
        save_cases_to_json(all_cases, output_file)
        
        success_panel = Panel(
            f"[bold {get_style('success')}]✓ Scraping completed![/bold {get_style('success')}]\n\n"
            f"Saved [bold {get_style('primary')}]{len(all_cases)}[/bold {get_style('primary')}] cases to:\n"
            f"[bold]{output_file}[/bold]",
            title=f"[bold {get_style('success')}]Success[/bold {get_style('success')}]",
            border_style=get_style("success"),
            box=box.ROUNDED
        )
        console.print()
        console.print(success_panel)
        
        # Ask if user wants to extract evidence
        console.print()
        extract_evidence = Confirm.ask(
            f"\n[bold {get_style('primary')}]Do you want to extract evidence from these cases?[/bold {get_style('primary')}]",
            default=True
        )
        
        if extract_evidence:
            console.print(f"\n[bold {get_style('primary')}]Starting evidence extraction...[/bold {get_style('primary')}]")
            try:
                # Import the evidence extractor
                import sys
                from pathlib import Path
                
                # Get the path to evidence_extractor.py
                script_dir = Path(__file__).parent.absolute()
                workspace_root = script_dir.parent
                evidence_extractor_path = workspace_root / "Analysis" / "evidence_extractor.py"
                
                # Add Analysis directory to path to import the module
                analysis_dir = workspace_root / "Analysis"
                if str(analysis_dir) not in sys.path:
                    sys.path.insert(0, str(analysis_dir))
                
                # Import and use the evidence extractor
                from evidence_extractor import WorkingEvidenceExtractor
                
                # Create extractor instance
                extractor = WorkingEvidenceExtractor()
                
                # Process the JSON file that was just created
                # Convert to absolute path to ensure it's found
                abs_output_file = os.path.abspath(output_file)
                extractor.process_json(
                    json_file=abs_output_file,
                    output_file=None,  # Use default output location
                    max_cases=None,  # Process all cases
                    start_index=0
                )
                
                console.print("\n[bold green]✓ Evidence extraction completed![/bold green]")
                
            except ImportError as e:
                console.print(f"[red]✗[/red] Could not import evidence extractor: {e}")
                console.print("[yellow]⚠[/yellow] Make sure evidence_extractor.py is in the Analysis folder")
            except Exception as e:
                console.print(f"[red]✗[/red] Error during evidence extraction: {e}")
                import traceback
                console.print(f"[red]Traceback:[/red]")
                console.print(traceback.format_exc())
    else:
        console.print("\n[yellow]⚠[/yellow] No cases were scraped.")


if __name__ == "__main__":
    main()


