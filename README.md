# AI-Enabled Antibody Design Research Database

A Streamlit web application for searching and exploring research papers on AI-enabled antibody design and computational methods for antibody engineering.

## Features

- 🔍 **Advanced Search**: Search papers by keywords in titles and abstracts
- 📅 **Year Filtering**: Filter papers by publication year range
- 📊 **Citation Filtering**: Filter by minimum citation count
- 📚 **Source Filtering**: Filter by data source (SciSpace, Google Scholar, arXiv, PubMed)
- 📋 **Multiple Sort Options**: Sort by relevance, citations, or publication year
- 📄 **Pagination**: Browse through papers with customizable page size
- 📈 **Statistics Dashboard**: View total papers, citations, and trends
- 🔗 **Direct Links**: Access paper URLs and PDFs directly

## Database

The application contains **109 curated research papers** from multiple academic sources:
- SciSpace (100 papers)
- SciSpace Full Text (100 papers)
- Google Scholar (20 papers)
- arXiv (20 papers)
- PubMed (20 papers)

Papers have been merged, deduplicated, and reranked by relevance to AI-enabled antibody design.

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

Start the Streamlit server:
```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`

## Usage

### Search and Filter
- Use the sidebar to enter search keywords
- Set year range filters (from/to)
- Adjust minimum citation count
- Select specific data sources
- Choose sorting preference

### Browse Papers
- View paper titles, authors, and metadata
- Expand abstracts to read full descriptions
- Click links to access original papers and PDFs
- Navigate through pages using pagination controls

### View Statistics
- Total papers matching your criteria
- Total and average citations
- Year range of papers in results

## Data Structure

Papers are stored in `.papertable` format (JSON) with the following information:
- Title
- Authors
- Abstract
- Publication date
- Source database
- Citation metrics
- Paper URLs and PDF links

## Technology Stack

- **Streamlit**: Web application framework
- **Python**: Backend processing
- **Pandas**: Data manipulation
- **JSON**: Data storage format

## Last Updated

November 2025

## License

This application is for research and educational purposes.
