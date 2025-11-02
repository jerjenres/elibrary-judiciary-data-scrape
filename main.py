import os
import json
import pandas as pd
from google import genai
from google.genai import types

# New import for .env file support
from dotenv import load_dotenv

# Add imports for web scraping
import requests
from bs4 import BeautifulSoup

# Add import for regex
import re

# Add imports for retries
import time

# Add import for JSON repair
import json_repair

# --- Load the .env file at the very start ---
load_dotenv()
# ---------------------------------------------


def load_links(path="links.txt"):
    if not os.path.exists(path):
        print(f"Warning: Links file '{path}' not found. Using empty list.")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def call_model_with_retries(client, model, contents, config, max_retries=4, initial_delay=2):
    delay = initial_delay
    TRANSIENT_STATUS = {429, 500, 502, 503, 504}
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.models.generate_content(model=model, contents=contents, config=config)
            return resp
        except Exception as e:
            status = None
            try:
                if hasattr(e, 'code'):
                    status = int(e.code)
                elif isinstance(e.args, (list, tuple)) and len(e.args) > 0:
                    if isinstance(e.args[0], dict) and 'error' in e.args[0]:
                        status = int(e.args[0]['error'].get('code', 0))
            except Exception:
                status = None
            is_transient = status in TRANSIENT_STATUS
            if not is_transient or attempt == max_retries:
                raise
            print(f"Transient error (attempt {attempt}/{max_retries}): {e}. Retrying in {delay}s...")
            time.sleep(delay)
            delay *= 2


def fetch_page_with_retries(url, max_retries=4, timeout=30):
    delay = 2
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp
        except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
            if attempt == max_retries:
                raise
            print(f"Request error (attempt {attempt}/{max_retries}): {e}. Retrying in {delay}s...")
            time.sleep(delay)
            delay *= 2

# ---------------------------------------------


def generate_and_append_to_excel():
    # --- CONFIGURATION START ---

    # 1. Load links from file
    LINKS_TO_PROCESS = load_links("links.txt")

    if not LINKS_TO_PROCESS:
        print("No links to process. Check links.txt file.")
        return

    # 2. Define the output filename and expected columns
    print("\nNote: If the excel file does not exist, it will be created. If it exists, new data will be appended to it.\n")
    print("Be sure to close the specified excel file (if exist) before proceeding.\n")
    filename_input = input("Enter Excel filename (without .xlsx, example 'march_data' or 'april'): ").strip()
    EXCEL_FILENAME = os.path.join("excel_files", filename_input + ".xlsx")

    expected_columns = ["Case Number", "Case Title", "Facts", "Decision", "Ruling", "Verdict"]

    # Check if existing file is writable (open in another app)
    if os.path.exists(EXCEL_FILENAME):
        try:
            with open(EXCEL_FILENAME, 'a'):
                pass
        except PermissionError:
            print(f"Error: The file '{EXCEL_FILENAME}' is currently open in another application. Please close it before proceeding.")
            return

    # 3. Model and API Client setup
    MODEL = "gemini-flash-latest" # Use a fast model for this task
    
    # The API key is now loaded from the .env file using load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found. Please ensure it is set in your .env file or system environment.")
        return

    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print("Error: Could not initialize Gemini Client.")
        print(f"Details: {e}")
        return

    # --- CONFIGURATION END ---

    SYSTEM_INSTRUCTION = """
    Your task is to act as a legal document parser.
    The user will provide text from multiple legal documents, each labeled as PAGE 1, PAGE 2, etc.
    For EACH page, extract the following data fields for its case:
    1. Case Number
    2. Case Title
    3. Facts
    4. Decision
    5. Ruling
    6. Verdict

    Crucially, you must adhere to the following:
    - Do NOT change or summarize the data; get the NECESSARY RAW data from each page's content.
    - Output the result as a JSON array of objects.
    - The array must contain exactly one object per PAGE, in the SAME ORDER as the pages (first object for PAGE 1, second for PAGE 2, etc.).
    - Each object must have the exact keys: "Case Number", "Case Title", "Facts", "Decision", "Ruling", and "Verdict".
    - OUTPUT ONLY THE JSON ARRAY. No explanations or extra text.
    """

    all_new_data = []

    for link in LINKS_TO_PROCESS:
        print(f"--- Processing link: {link} ---")

        try:
            # Fetch the webpage content with retries
            page = fetch_page_with_retries(link)
            soup = BeautifulSoup(page.content, "html.parser")
            page_text = soup.get_text(separator="\n", strip=True)[:285000]  # Limit to prevent token overflow

            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=f"Here is the page text to extract from:\n\n{page_text}\n\nExtract the case data as JSON per system instruction.")],
                ),
            ]

            generate_content_config = types.GenerateContentConfig(
                system_instruction=[types.Part.from_text(text="""
                Your task is to act as a legal document parser.
                Extract the following data fields for ONE case:
                1. Case Number
                2. Case Title
                3. Facts
                4. Decision
                5. Ruling
                6. Verdict

                Crucially, you must adhere to the following:
                - Do NOT change or summarize the data; get the NECESSARY RAW data from the webpage content.
                - Output the result as a single, valid JSON array of objects.
                - The JSON array must contain exactly ONE object.
                - The object must have the exact keys: "Case Number", "Case Title", "Facts", "Decision", "Ruling", and "Verdict".
                - Ensure all values are correctly enclosed in double quotes.
                """)],
            )

            # Use generate_content with retries for transient errors
            response = call_model_with_retries(client, MODEL, contents, generate_content_config)

            # Guard against empty/damaged response
            if not response or not hasattr(response, 'text') or not response.text:
                idx = len(all_new_data) + 1
                with open(f"debug_empty_response_{idx}.txt", "w", encoding="utf-8") as f:
                    f.write(page_text)
                # One more attempt with stricter instruction
                stricter_config = types.GenerateContentConfig(
                    system_instruction=[types.Part.from_text(text="OUTPUT ONLY VALID JSON ARRAY. No markdown or extras.")],
                )
                print("  Empty response, retrying with stricter prompt...")
                try:
                    response = call_model_with_retries(client, MODEL, contents, stricter_config, max_retries=1)
                except Exception:
                    raise ValueError("Empty model response after retry")

            # The model is instructed to return a JSON array string
            raw_json_text = (response.text or "").strip()

            # Debugging outputs
            #print("DEBUG: raw response length:", len(raw_json_text))
            #print("DEBUG: raw response repr:", repr(raw_json_text)[:1000])

            if not raw_json_text:
                # Save debug files for inspection
                idx = len(all_new_data) + 1
                with open(f"debug_empty_response_{idx}.txt", "w", encoding="utf-8") as f:
                    f.write(page_text)
                raise ValueError("Empty model response")

            # Try direct load, with JSON repair as fallback, then extract a JSON array substring
            try:
                new_data = json.loads(raw_json_text)
            except json.JSONDecodeError:
                try:
                    new_data = json_repair.loads(raw_json_text)
                    print("  Repaired malformed JSON with json_repair")
                except Exception:
                    m = re.search(r"(\[\s*\{.*?\}\s*\])", raw_json_text, re.S)
                    if m:
                        try:
                            new_data = json.loads(m.group(1))
                        except json.JSONDecodeError:
                            new_data = json_repair.loads(m.group(1))
                            print("  Repaired regex-extracted JSON with json_repair")
                    else:
                        # Save raw response for manual debugging
                        idx = len(all_new_data) + 1
                        with open(f"debug_bad_json_{idx}.txt", "w", encoding='utf-8') as f:
                            f.write(raw_json_text)
                        raise ValueError("Could not parse JSON response even with repairs")

            # Validate it's a list with one object
            if not isinstance(new_data, list) or len(new_data) != 1:
                raise ValueError("Gemini response must be a JSON array with exactly one object.")

            # Add the new case data to our master list
            all_new_data.extend(new_data)
            print(f"Successfully extracted {len(new_data)} record(s).")

        except Exception as e:
            print(f"ERROR: Failed to process link {link}. Skipping to next link.")
            print(f"Error details: {e}")
            continue
            
    # --- File Writing and Appending Logic ---
    
    if not all_new_data:
        print("\nNo data extracted successfully. Exiting file write process.")
        return

    df_new = pd.DataFrame(all_new_data)
    
    # Check if the file already exists and handle accordingly
    if os.path.exists(EXCEL_FILENAME):
        try:
            # Read existing data
            df_existing = pd.read_excel(EXCEL_FILENAME, engine='openpyxl')

            # Check if existing data has non-matching columns and is not empty
            if len(df_existing) > 0 and list(df_existing.columns) != expected_columns:
                print(f"Existing Excel has different headers. Overwriting with new data.")
                df_combined = df_new
            else:
                print(f"Appending new data to existing file.")
                df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                print(f"Total records now in file: {len(df_combined)}")
        except Exception as e:
            print(f"Warning: Could not read existing Excel file. Writing only new data. Error: {e}")
            df_combined = df_new
    else:
        print(f"\n'{EXCEL_FILENAME}' not found. Creating new Excel file.")
        df_combined = df_new

    # Write the combined DataFrame back to the Excel file
    df_combined.to_excel(EXCEL_FILENAME, index=False)
    print(f"\n--- SUCCESS ---")
    print(f"Total new records appended: {len(df_new)}")
    print(f"File saved/updated as: {EXCEL_FILENAME}")
    
if __name__ == "__main__":
    generate_and_append_to_excel()
