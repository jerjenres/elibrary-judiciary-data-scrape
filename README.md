# Philippine Judiciary Legal Case Scraper

A Python-based web scraping tool designed to extract and organize legal case data from the Philippine Judiciary eLibrary. The project uses AI-powered text extraction to parse case details including case numbers, titles, facts, decisions, rulings, and verdicts, and saves them to Excel spreadsheets.

## TLDR

**Setup:** Get Gemini API key → `pip install google-genai python-dotenv requests beautifulsoup4 pandas json-repair` → create `.env` with GEMINI_API_KEY → create a text file `links.txt`

**Quick Start:**
1. Collect case URLs: `python link_scraper.py` (enter eLibrary page URL)
2. Paste the case URLs in `links.txt`
3. Extract data: `python main.py` (enter Excel filename - creates/appends to excel_files/ directory)

$\color{orange}{\textsf{\textbf{Remember to close the specified excel file to avoid errors.}}}$

## Features

- **Web Scraping**: Automates extraction of case URLs from the Philippine Judiciary eLibrary pages
- **AI-Powered Extraction**: Utilizes Google's Gemini AI to accurately parse and structure legal document data
- **Data Organization**: Saves extracted data to Excel files with consistent formatting
- **Retry Mechanisms**: Built-in retry logic for handling transient API and network errors
- **Incremental Updates**: Appends new data to existing Excel files without overwriting previous entries
- **Environment Configuration**: Secure API key management using .env files

## Prerequisites

- Python 3.7 or higher
- Google Gemini API key (obtain from [Google AI Studio](https://aistudio.google.com/app/apikey))

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/elibrary-judiciary-data-scrape.git
   cd elibrary-judiciary-data-scrape
   ```

2. Install required dependencies:
   ```bash
   pip install google-genai python-dotenv requests beautifulsoup4 pandas json-repair
   ```

3. Create a `.env` file in the project root and add your Gemini API key:
   ```
   GEMINI_API_KEY="your_api_key_here"
   ```

4. Create a text file `links.txt`

## Usage

### Step 1: Collect Case URLs

Use the link scraper to extract case document URLs from a specific eLibrary page:

```bash
python link_scraper.py
```

Follow the prompts to enter the URL of the eLibrary page containing case links. The script will output URLs matching the default pattern for case documents.

Example link of the month and year - https://elibrary.judiciary.gov.ph/thebookshelf/docmonth/May/2021/1

The extracted URLs will be displayed on stdout.
```
https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/67421
https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/67425
https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/67440
...
 ```

Copy and save them to `links.txt` (one URL per line).


### Step 2: Extract Case Data

Be sure to paste the extracted URLs to `links.txt` before running this main script.

Open another terminal and run the main extraction script:

```bash
python main.py
```

When prompted, enter the Excel filename (without the `.xlsx` extension). 

**Note: If the file does not exist, it will be created. If it exists, new data will be appended to it. The script will:**

- Load URLs from `links.txt`
- Fetch and parse each case page
- Extract structured data using Gemini AI
- Save/append results to the specified Excel file in the `excel_files/` directory

$\color{orange}{\textsf{\textbf{Remember to close the specified excel file to avoid errors.}}}$

## Example Output

The following table shows a sample of what the extracted data might look like:

| Case Number | Case Title | Facts | Decision | Ruling | Verdict |
|-------------|------------|-------|----------|--------|---------|
| G.R. No. 789012 | Juan dela Cruz v. Bank of the Philippines | Respondent bank implemented a repossession of the properties mortgaged by petitioner after default on loan payments despite petitioner's claim of moratorium due to COVID-19 pandemic impacts. | The Court AFFIRMS the decision of the Court of Appeals upholding the validity of the repossession but REMANDS for proper valuation proceedings. | The mortgage contract is deemed valid and enforceable, but the bank must conduct proper appraisal hearings per banking regulations. | SO ORDERED. |

## Data Structure

Each processed case is saved with the following fields:

- **Case Number**: The official case identifier
- **Case Title**: Title of the legal case
- **Facts**: Summary of case facts as extracted from the document
- **Decision**: Court decision details
- **Ruling**: Specific ruling information
- **Verdict**: Final verdict of the case


## Error Handling

The tool includes comprehensive error handling for:
- Network request failures (with automatic retries)
- API rate limits and transient errors
- Malformed JSON responses (with repair attempts)
- Missing or invalid data fields
- Empty model responses: Typically indicate that the case content is sensitive or violates AI content policies - these cases will be skipped and not processed
- During data extraction, you may see warnings like "Warning: there are non-text parts in the response: ['thought_signature'], returning concatenated text result from text parts." These are normal and indicate the AI response includes internal metadata alongside the text. The code handles this correctly, and extraction will proceed successfully.

Debug files (debug_empty_response_*.txt) are created for problematic pages, including those with empty responses, to aid troubleshooting.

## Configuration

### Environment Variables
- `GEMINI_API_KEY`: Your Google Gemini API key (required)

### File Formats
- `links.txt`: Plain text file with one URL per line
- Output files: Excel (.xlsx) format saved to the `excel_files/` directory with standardized columns

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for educational and research purposes. Ensure compliance with the Philippine Judiciary eLibrary terms of service and applicable laws regarding automated data collection. Respect rate limits and avoid overloading the servers.
