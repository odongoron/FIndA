# FindA
## A Social Media Reverse-Image & Name Finder

A desktop application that lets you drop a face image or enter a name, then searches multiple social platforms (Google, Facebook, Instagram, Twitter, etc.) to find matching profiles using a mix of web scraping, face-recognition embeddings and perceptual hashing.

## Features

- Reverse-image search: take any face photo, compute embeddings + pHash, query 4 major platforms  
- Name search: lookup people by full name across Facebook, Instagram, Twitter  
- Background threads with live progress bars  
- Stealth-mode Selenium (anti-bot flags, optional proxy rotation)  
- Graceful error handling & fallback stubs for unsupported platforms  
- Exportable results list with profile URL, name/username and similarity score  

## Architecture & Tech Stack

- Python 3.10+  
- PyQt5 for GUI  
- Selenium + ChromeDriver (via webdriver-manager) for scraping  
- ONNX Runtime + InsightFace models for face embeddings  
- `imagehash` + Pillow for perceptual-hash fallback  
- ThreadPoolExecutor for concurrent platform queries  
- ProxyManager stub (configurable in `config/targets.yaml`)  
- CaptchaSolver extension (pluggable)  

## Prerequisites

- Chrome or Chromium browser installed  
- Python 3.10+ and pip  
- Environment variables set:
  ```
  export FACEBOOK_USER="your_fb_email"
  export FACEBOOK_PASS="your_fb_pass"
  export INSTAGRAM_USER="your_ig_user"
  export INSTAGRAM_PASS="your_ig_pass" 
  ```

## Installation

1. Clone the repo

```
git clone https://github.com/ronodongo/FindA.git
cd FindA
```

2. Create and activate a virtual environment

```
python -m venv venv
source venv/bin/activate    # macOS/Linux
venv\Scripts\activate       # Windows 
```

3. Install dependencies

```
pip install -r requirements.txt
```

4. Copy and tweak config/targets.yaml and config/proxies.yaml as needed.


## Configuration

- Targets: edit config/targets.yaml to enable/disable platforms or proxies

- Proxies: list real proxies in config/proxies.yaml & toggle proxies.enabled

- Face models: default InsightFace models download to ~/.insightface/models/

## Usage

1. Launch the app:

```
python main.py
```


2. In the GUI:

 Face Search: click “Browse Image,” select a photo, then “Start Face Search.”

 Name Search: enter a full name, click “Search by Name.”

3. View and export results from the list panel.

## Project Structure

```
FindA/
├── app.py
├── main.py
├── config/
│   ├── targets.yaml
│   └── proxies.yaml
├── core/
│   ├── face_recognition.py
│   ├── search_engine.py
│   └── scrapers/
│       ├── base_scraper.py
│       ├── facebook.py
│       ├── instagram.py
│       ├── twitter.py
│       └── google.py
├── utils/
│   ├── captcha.py
│   ├── file_utils.py
│   └── network.py
├── views/
│   ├── main_window.py
│   └── search_tabs.py
├── requirements.txt
└── README.md
```

## Version Control & Collaboration

 Commits: small, frequent, descriptive messages

 Branches: feature branches (feature/image-search), PRs for merges

 Pull Requests: review & CI checks before merging to main

 Tags/Releases: use annotated tags for v1.0, v1.1, etc.



## License

MIT License 

## Acknowledgements

 InsightFace team for face-recognition models

 Selenium & WebDriver-manager maintainers

 PyQt5 community

