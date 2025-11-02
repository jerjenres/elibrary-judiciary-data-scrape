#!/usr/bin/env python3
"""
Link Scraper for Philippine Judiciary eLibrary

A simple script to extract all unique absolute links from a given webpage.

Usage:
    python link_scraper.py [--all] [--filter REGEX] [--timeout SECONDS]

Arguments:
    --all: Return all links (default: only case links like showdocs/*)
    --filter REGEX: Optional regex pattern to filter links (overrides default filtering if provided)
    --timeout SECONDS: Request timeout in seconds (default: 15)

Examples:
    # Run the script - returns only case links by default
    python link_scraper.py

    # Scrape all links on the page
    python link_scraper.py --all

    # Scrape only PDF links
    python link_scraper.py --filter '\\.pdf$'

    # Scrape links containing 'thebookshelf'
    python link_scraper.py --filter 'thebookshelf'
"""

import argparse
import re
import sys
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


def fetch_page_with_retries(url, max_retries=3, timeout=15):
    """Fetch webpage with retries on transient errors."""
    delay = 1
    last_exception = None

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            last_exception = e
            if attempt < max_retries:
                print(f"Request failed (attempt {attempt}/{max_retries}): {e}. Retrying in {delay}s...",
                      file=sys.stderr)
                time.sleep(delay)
                delay *= 2
            else:
                raise last_exception


def extract_links(url, response, filter_regex=None):
    """Extract unique absolute links from the response content."""
    soup = BeautifulSoup(response.content, "html.parser")
    base_url = url.rstrip('/')

    seen = set()
    ordered_links = []

    for a_tag in soup.find_all("a", href=True):
        href = a_tag['href'].strip()

        # Skip empty, fragment-only, or invalid relative links
        if not href or href.startswith('#') or not href:
            continue

        # Convert to absolute URL
        abs_url = urljoin(base_url + '/', href)  # Add trailing slash to handle relative correctly

        # Ensure it's a valid URL (has scheme)
        parsed = urlparse(abs_url)
        if not parsed.scheme or not parsed.netloc:
            continue

        # Apply regex filter if provided
        if filter_regex and not re.search(filter_regex, abs_url, re.IGNORECASE):
            continue

        # Add only if not already seen to preserve order
        if abs_url not in seen:
            seen.add(abs_url)
            ordered_links.append(abs_url)

    return ordered_links


def main():
    parser = argparse.ArgumentParser(
        description="Extract all unique absolute links from a webpage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python link_scraper.py
  python link_scraper.py --filter "\\.pdf$"
  python link_scraper.py --filter "thebookshelf" --timeout 30
        """
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Return all links (default: only case links like showdocs/*)"
    )
    parser.add_argument(
        "--filter",
        help="Optional regex pattern to filter links (case-insensitive) - overrides default filtering if provided"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=15,
        help="Request timeout in seconds (default: 15)"
    )

    args = parser.parse_args()

    # Determine filter pattern
    if args.filter:
        filter_pattern = args.filter
    elif not args.all:  # default to case-only unless --all
        filter_pattern = r"^https?://elibrary\.judiciary\.gov\.ph/thebookshelf/showdocs/\d+/\d+$"
    else:
        filter_pattern = None

    # Prompt for URL instead of taking as argument
    print('\nEnter the link to scrape the case URLs from the specific year and month like this "https://elibrary.judiciary.gov.ph/thebookshelf/docmonth/May/2021/1"\n')
    url = input("Enter URL to scrape: ").strip()

    if not url:
        print("No URL provided. Exiting.", file=sys.stderr)
        sys.exit(1)

    try:
        print(f"Fetching links from: {url}", file=sys.stderr)

        if filter_pattern:
            print(f"Filter pattern: {filter_pattern}", file=sys.stderr)

        response = fetch_page_with_retries(url, timeout=args.timeout)

        links = extract_links(url, response, filter_pattern)

        print(f"Found {len(links)} unique link(s):", file=sys.stderr)
        print(file=sys.stderr)  # Blank line

        # Print each link on its own line (stdout for copying/piping)
        for link in links:
            print(link)

    except requests.RequestException as e:
        print(f"Error fetching page: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
