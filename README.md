# Generative AI for Data Scraping

This is the GitHub repo to accompany the paper [Generative AI for Data Scraping](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5353923).
## 📁 Project Structure

```
genai-data-scraping-html/
├── data/                    # Sample scraped data
│   ├── amazon.com/         # Amazon product pages (HTML + assets)
│   ├── cars.com/           # Car listings (HTML + assets)
│   └── upwork.com/         # Freelancer profiles (HTML + assets)
├── method2/                # HTML processing with LLM
├── method3/                # Image/screenshot processing with vision API
├── websearch/              # Web search integration
├── requirements.txt        # Python dependencies
└── venv/                   # Virtual environment
```

## 🗂️ Available Data

The project includes scraped data from three major websites:

### Amazon.com Data
- **Format**: Complete HTML files with associated assets
- **Content**: Product pages including:
  - Kitchen appliances (rice cookers, pressure cookers, sous vide machines)
  - Japanese tableware and bowls
  - Books and educational materials
  - Electronics and gadgets
- **File Size**: 1.6MB - 2.6MB per page
- **Count**: 50+ product pages

### Cars.com Data
- **Format**: Complete HTML files with associated assets
- **Content**: Vehicle listings including:
  - New and used cars (2015-2025 models)
  - Various makes: Toyota, Ford, Tesla, BMW, Mercedes, etc.
  - Price range: $13,907 - $324,900
  - Different vehicle types: sedans, SUVs, trucks, sports cars
- **File Size**: 1.1MB - 3.0MB per page
- **Count**: 50+ vehicle listings

### Upwork.com Data
- **Format**: Complete HTML files with associated assets
- **Content**: Freelancer profiles including:
  - Developers (Full-stack, Mobile, AI/ML specialists)
  - Designers (UI/UX, Graphic, Motion designers)
  - Digital marketers and SEO experts
  - Writers and consultants
- **File Size**: 1.1MB - 1.5MB per page
- **Count**: 50+ freelancer profiles

## Setup Instructions

### 1. Environment Setup

```bash
# Clone or navigate to the project directory
cd genai-data-scraping-html

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables

All methods require an OpenRouter API key. Set it up:

```bash
# Add to your shell profile (.bashrc, .zshrc, etc.)
export OPENROUTER_API_KEY="your_api_key_here"

# Or create a .env file in the project root
echo "OPENROUTER_API_KEY=your_api_key_here" > .env
```

##  Method 2: HTML Processing

**Purpose**: Extracts structured data from HTML files using LLM analysis with intelligent content cleaning and parallel processing.

### Features
- Intelligent HTML cleaning and content scoring
- Parallel processing with configurable worker threads
- Preserves important content while removing boilerplate
- Extracts product information, prices, features, availability

### Configuration
- **Model**: `openai/gpt-4o-mini`
- **Default Workers**: 10 (configurable)
- **Timeout**: 60 seconds
- **Temperature**: 0.1

### Usage Examples

```bash
# Navigate to method2 directory
cd method2

# Basic usage - process 5 random Amazon files
python app.py -d "../data/amazon.com" -n 5

# Custom output file and worker count
python app.py -d "../data/amazon.com" -n 10 -o "amazon_results.json" -w 5

# Process car listings with custom prompt
python app.py -d "../data/cars.com" -n 8 -p "custom_prompt.txt" -o "cars_output.json"

# Process Upwork profiles
python app.py -d "../data/upwork.com" -n 6 -w 3
```

### Command Line Arguments
- `-d, --directory`: Directory containing HTML files (required)
- `-n, --num-files`: Number of random files to process (required)
- `-p, --prompt-file`: Path to prompt file (default: `prompt.txt`)
- `-o, --output`: Output JSON file (default: `results.json`)
- `-w, --max-workers`: Maximum worker threads (default: 10)

### Output Format
```json
{
  "processed_files": [
    {
      "filename": "product_page.html",
      "full_path": "/path/to/file",
      "url": "https://amazon.com/product",
      "status": "success",
      "error": null,
      "llm_response": "{\"price\": \"$29.99\", \"brand\": \"Sony\", ...}",
      "thread_id": 12345
    }
  ],
  "summary": {
    "total_requested": 5,
    "total_processed": 5,
    "successful": 4,
    "failed": 1,
    "directory": "../data/amazon.com",
    "max_workers": 10
  }
}
```

## Method 3: Image/Screenshot Processing

**Purpose**: Analyzes screenshots and images using vision API to extract structured data from visual content.

### Features
- Supports multiple image formats (PNG, JPG, JPEG, GIF, BMP, WEBP)
- Batch processing of image folders
- Image statistics and validation
- Base64 encoding for API transmission

### Configuration
- **Model**: `mistralai/mistral-small-3.2-24b-instruct`
- **Timeout**: 120 seconds
- **Default Folder**: `scraped_photos`

### Usage Examples

```bash
# Navigate to method3 directory
cd method3

# Basic usage with default settings
python app.py

# Process custom folder with specific output
python app.py -f screenshots -o results.json

# Custom prompt and folder with preview
python app.py -p custom_prompt.txt -f images/ --preview

# Show folder statistics only
python app.py -f screenshots --stats-only

# Verbose logging with backup
python app.py -f images --verbose --backup
```

### Command Line Arguments
- `-f, --folder`: Folder containing images (default: `scraped_photos`)
- `-p, --prompt-file`: Path to prompt file (default: `prompt.txt`)
- `-o, --output`: Output JSON file (default: `vision_results.json`)
- `--preview`: Show preview of results in console
- `--backup`: Create backup of existing output file
- `--verbose`: Enable verbose logging
- `--stats-only`: Only show folder statistics

### Output Format
```json
{
  "success": true,
  "image_count": 3,
  "folder_path": "screenshots",
  "timestamp": "2024-01-15T10:30:00",
  "data": {
    "extracted_fields": "...",
    "analysis": "..."
  }
}
```

## WebSearch: Web Search Integration

**Purpose**: Combines HTML file processing with live web search capabilities for enhanced data extraction.

### Features
- Extracts URLs from HTML files automatically
- Uses web search-enabled LLM model
- Parallel processing with rate limiting
- Real-time web content analysis

### Configuration
- **Model**: `openai/gpt-4o-search-preview-2025-03-11`
- **Default Workers**: 5 (lower for API rate limits)
- **Temperature**: 0.1
- **Timeout**: 120 seconds

### Usage Examples

```bash
# Navigate to websearch directory
cd websearch

# Basic usage - process 3 random files
python app.py -d "../data/amazon.com" -n 3

# Custom settings with lower worker count for rate limiting
python app.py -d "../data/cars.com" -n 5 -w 2 -o "cars_web_results.json"

# Process with custom prompt
python app.py -d "../data/upwork.com" -n 4 -p "custom_search_prompt.txt"
```

### Command Line Arguments
- `-d, --directory`: Directory containing HTML files (required)
- `-n, --num-files`: Number of random files to process (required)
- `-p, --prompt-file`: Path to prompt file (default: `prompt.txt`)
- `-o, --output`: Output JSON file (default: `web_search_results.json`)
- `-w, --max-workers`: Maximum worker threads (default: 5, recommended ≤5 for rate limits)

### Output Format
```json
{
  "processed_files": [
    {
      "filename": "listing.html",
      "full_path": "/path/to/file",
      "url": "https://cars.com/listing/123",
      "status": "success",
      "error": null,
      "llm_response": "{\"make\": \"Toyota\", \"model\": \"Camry\", ...}",
      "thread_id": 67890
    }
  ],
  "summary": {
    "total_requested": 3,
    "total_processed": 3,
    "successful": 3,
    "failed": 0,
    "directory": "../data/cars.com",
    "max_workers": 5
  }
}
```

## Customizing Prompts

Each method uses a `prompt.txt` file that defines what data to extract:

### Method 2 Prompt (HTML Processing)
```text
You are an expert at extracting structured data from HTML content.

Extract the following fields:
- Full Price (include discounts, import charges, shipping fees)
- Brand
- Color
- Availability
- Product Features
- Product Name

Return data in JSON format.
```

### Method 3 Prompt (Image Processing)
```text
You are an expert in extracting structured information from web page screenshots.

Required data fields:
- Field 1
- Field 2
- Field 3

Analyze all screenshots and extract data from the primary content.
Return data in JSON format.
```

### WebSearch Prompt (Web Search)
```text
Please visit the provided URL and extract the specified information.

Fields to extract:
1. Field 1
2. Field 2
3. Field 3

Return results in JSON format.
```

## Configuration Options

### Method 2 Settings (`method2/config/settings.py`)
```python
# API Settings
MODEL_NAME = "openai/gpt-4o-mini"
API_TIMEOUT = 60
API_TEMPERATURE = 0.1
DEFAULT_MAX_WORKERS = 10

# Content Preservation
PRESERVE_CLASSES = {'product', 'item', 'listing', 'price', 'reviews'}
PRESERVE_IDS = {'main', 'products', 'productTitle', 'priceblock_ourprice'}
```

### Method 3 Settings (`method3/config/settings.py`)
```python
# API Configuration
API_MODEL = "mistralai/mistral-small-3.2-24b-instruct"
API_TIMEOUT = 120

# Image Processing
SUPPORTED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
DEFAULT_FOLDER_PATH = "scraped_photos"
```

### WebSearch Settings (`websearch/config/settings.py`)
```python
# API Configuration
API_MODEL = "openai/gpt-4o-search-preview-2025-03-11"
API_TEMPERATURE = 0.1
DEFAULT_MAX_WORKERS = 5  # Lower for rate limiting
```

## Performance Tips

### Method 2 (HTML Processing)
- Use 5-10 workers for optimal performance
- Larger files may require more processing time
- Monitor API rate limits with high worker counts

### Method 3 (Image Processing)
- Ensure images are high quality for better extraction
- Large image folders may require significant processing time
- Use `--stats-only` to check folder contents first

### WebSearch
- Keep worker count ≤5 to avoid API rate limits
- Processing time depends on web search complexity
- Monitor for timeout issues with slow websites

## Troubleshooting

### Common Issues

1. **API Key Not Set**
   ```bash
   # Error: OPENROUTER_API_KEY environment variable not set
   export OPENROUTER_API_KEY="your_key_here"
   ```

2. **No Files Found**
   ```bash
   # Ensure directory path is correct and contains HTML files
   ls -la data/amazon.com/*.html
   ```

3. **Rate Limit Errors**
   ```bash
   Reduce worker count in the argparse command
   ```

## 📄 License

This project is provided for research and reproducibility purposes. 
