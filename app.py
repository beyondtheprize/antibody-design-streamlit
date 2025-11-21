import streamlit as st
import json
import pandas as pd
from datetime import datetime
import re

# Page configuration
st.set_page_config(
    page_title="AI-Enabled Antibody Design Research",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stAlert {
        margin-top: 1rem;
    }
    .paper-card {
        background-color: #f8f9fa;
        border-left: 4px solid #0066cc;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .paper-title {
        color: #0066cc;
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .paper-authors {
        color: #555;
        font-size: 0.95rem;
        margin-bottom: 0.5rem;
    }
    .paper-meta {
        color: #777;
        font-size: 0.85rem;
        margin-bottom: 0.8rem;
    }
    .paper-abstract {
        color: #333;
        font-size: 0.95rem;
        line-height: 1.6;
        margin-top: 0.8rem;
    }
    .metric-box {
        background-color: #e7f3ff;
        padding: 0.5rem;
        border-radius: 0.3rem;
        display: inline-block;
        margin-right: 0.5rem;
    }
    .filter-section {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_papers():
    """Load papers from the papertable file"""
    try:
        with open('/home/sandbox/antibody-design-streamlit/papers_data.papertable', 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        st.error(f"Error loading papers: {str(e)}")
        return None

def extract_paper_info(paper_data, column_id):
    """Extract paper information from the data structure"""
    if column_id in paper_data:
        return paper_data[column_id]
    return None

def format_authors(authors):
    """Format author list"""
    if not authors:
        return "Authors not available"
    
    if isinstance(authors, list):
        author_names = []
        for author in authors[:5]:  # Show first 5 authors
            if isinstance(author, dict):
                name = author.get('name', '')
                if name:
                    author_names.append(name)
            elif isinstance(author, str):
                author_names.append(author)
        
        result = ", ".join(author_names)
        if len(authors) > 5:
            result += f" et al. ({len(authors)} authors)"
        return result
    return str(authors)

def format_date(date_str):
    """Format publication date"""
    if not date_str:
        return "Date not available"
    try:
        # Try to parse and format the date
        if isinstance(date_str, str):
            # Handle different date formats
            for fmt in ['%Y-%m-%d', '%Y-%m', '%Y']:
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    return date_obj.strftime('%B %Y')
                except:
                    continue
        return date_str
    except:
        return date_str

def get_citation_count(metrics):
    """Extract citation count from metrics"""
    if not metrics:
        return 0
    if isinstance(metrics, dict):
        return metrics.get('citationCount', 0) or metrics.get('citation_count', 0) or 0
    return 0

def search_papers(papers_data, search_query, year_range, min_citations, sources):
    """Filter papers based on search criteria"""
    if not papers_data or 'data' not in papers_data:
        return []
    
    filtered_papers = []
    paper_column_id = None
    
    # Find the paper column ID
    for col in papers_data.get('columns', []):
        if 'Papers' in col.get('name', ''):
            paper_column_id = col['column_id']
            break
    
    if not paper_column_id:
        return []
    
    for paper_entry in papers_data['data']:
        paper = extract_paper_info(paper_entry, paper_column_id)
        if not paper:
            continue
        
        # Search filter
        if search_query:
            search_lower = search_query.lower()
            title = paper.get('title', '').lower()
            abstract = paper.get('abstract', '').lower()
            
            if search_lower not in title and search_lower not in abstract:
                continue
        
        # Year filter
        if year_range[0] or year_range[1]:
            paper_date = paper.get('date', '')
            try:
                if paper_date:
                    year = int(paper_date.split('-')[0])
                    if year_range[0] and year < year_range[0]:
                        continue
                    if year_range[1] and year > year_range[1]:
                        continue
            except:
                pass
        
        # Citation filter
        metrics = paper.get('metrics', {})
        citations = get_citation_count(metrics)
        if citations < min_citations:
            continue
        
        # Source filter
        if sources:
            paper_source = paper.get('source', '').lower()
            if not any(source.lower() in paper_source for source in sources):
                continue
        
        filtered_papers.append(paper)
    
    return filtered_papers

def display_paper(paper, index):
    """Display a single paper in a card format"""
    st.markdown(f"""
        <div class="paper-card">
            <div class="paper-title">{index}. {paper.get('title', 'Title not available')}</div>
            <div class="paper-authors">👥 {format_authors(paper.get('authors', []))}</div>
            <div class="paper-meta">
                📅 {format_date(paper.get('date', ''))} | 
                📚 {paper.get('source', 'Unknown').upper()} | 
                📊 {get_citation_count(paper.get('metrics', {}))} citations
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Abstract in expandable section
    abstract = paper.get('abstract', 'Abstract not available')
    with st.expander("📄 View Abstract"):
        st.markdown(f'<div class="paper-abstract">{abstract}</div>', unsafe_allow_html=True)
    
    # Links
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        # Paper URL
        paper_urls = paper.get('paper_urls', {})
        if isinstance(paper_urls, dict) and 'data' in paper_urls:
            urls = paper_urls['data']
            if urls and len(urls) > 0:
                st.link_button("🔗 View Paper", urls[0], use_container_width=True)
    
    with col2:
        # PDF URL
        fulltext_url = paper.get('fulltext_url', '')
        if fulltext_url:
            if fulltext_url.startswith('/pdf'):
                fulltext_url = f"https://scispace.com{fulltext_url}"
            st.link_button("📑 PDF", fulltext_url, use_container_width=True)
    
    st.markdown("---")

def main():
    # Header
    st.title("🧬 AI-Enabled Antibody Design Research")
    st.markdown("""
        Explore cutting-edge research on artificial intelligence and machine learning applications 
        in antibody design and engineering. This database contains curated papers from multiple 
        academic sources including SciSpace, Google Scholar, arXiv, and PubMed.
    """)
    
    # Load papers
    papers_data = load_papers()
    
    if not papers_data:
        st.error("Failed to load papers data. Please check the data file.")
        return
    
    # Sidebar filters
    st.sidebar.header("🔍 Search & Filters")
    
    # Search box
    search_query = st.sidebar.text_input(
        "Search papers",
        placeholder="Enter keywords (title, abstract)...",
        help="Search in paper titles and abstracts"
    )
    
    # Year range filter
    st.sidebar.subheader("📅 Publication Year")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        year_from = st.number_input("From", min_value=1990, max_value=2025, value=None, step=1)
    with col2:
        year_to = st.number_input("To", min_value=1990, max_value=2025, value=None, step=1)
    
    # Citation filter
    min_citations = st.sidebar.slider(
        "📊 Minimum Citations",
        min_value=0,
        max_value=500,
        value=0,
        step=10,
        help="Filter papers by minimum citation count"
    )
    
    # Source filter
    st.sidebar.subheader("📚 Data Sources")
    sources = st.sidebar.multiselect(
        "Filter by source",
        options=["SciSpace", "Google Scholar", "arXiv", "PubMed", "Full Text"],
        default=[],
        help="Select one or more sources to filter papers"
    )
    
    # Sort options
    st.sidebar.subheader("📋 Sort By")
    sort_option = st.sidebar.selectbox(
        "Sort papers by",
        options=["Relevance", "Citations (High to Low)", "Year (Newest First)", "Year (Oldest First)"],
        help="Choose how to sort the papers"
    )
    
    # Apply filters
    filtered_papers = search_papers(
        papers_data,
        search_query,
        (year_from, year_to),
        min_citations,
        sources
    )
    
    # Sort papers
    if sort_option == "Citations (High to Low)":
        filtered_papers.sort(key=lambda x: get_citation_count(x.get('metrics', {})), reverse=True)
    elif sort_option == "Year (Newest First)":
        filtered_papers.sort(key=lambda x: x.get('date', ''), reverse=True)
    elif sort_option == "Year (Oldest First)":
        filtered_papers.sort(key=lambda x: x.get('date', ''))
    
    # Statistics
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📚 Total Papers", len(filtered_papers))
    
    with col2:
        total_citations = sum(get_citation_count(p.get('metrics', {})) for p in filtered_papers)
        st.metric("📊 Total Citations", f"{total_citations:,}")
    
    with col3:
        if filtered_papers:
            avg_citations = total_citations / len(filtered_papers)
            st.metric("📈 Avg Citations", f"{avg_citations:.1f}")
        else:
            st.metric("📈 Avg Citations", "0")
    
    with col4:
        if filtered_papers:
            years = []
            for p in filtered_papers:
                date_str = p.get('date', '')
                if date_str:
                    try:
                        year = int(date_str.split('-')[0])
                        years.append(year)
                    except:
                        pass
            if years:
                st.metric("📅 Year Range", f"{min(years)}-{max(years)}")
            else:
                st.metric("📅 Year Range", "N/A")
        else:
            st.metric("📅 Year Range", "N/A")
    
    st.markdown("---")
    
    # Display results
    if filtered_papers:
        st.subheader(f"📖 Showing {len(filtered_papers)} Papers")
        
        # Pagination
        papers_per_page = st.sidebar.number_input(
            "Papers per page",
            min_value=5,
            max_value=50,
            value=10,
            step=5
        )
        
        total_pages = (len(filtered_papers) - 1) // papers_per_page + 1
        
        if total_pages > 1:
            page = st.sidebar.number_input(
                "Page",
                min_value=1,
                max_value=total_pages,
                value=1,
                step=1
            )
        else:
            page = 1
        
        start_idx = (page - 1) * papers_per_page
        end_idx = min(start_idx + papers_per_page, len(filtered_papers))
        
        # Display papers
        for i, paper in enumerate(filtered_papers[start_idx:end_idx], start=start_idx + 1):
            display_paper(paper, i)
        
        # Pagination info
        if total_pages > 1:
            st.info(f"📄 Page {page} of {total_pages} | Showing papers {start_idx + 1}-{end_idx} of {len(filtered_papers)}")
    else:
        st.warning("🔍 No papers found matching your criteria. Try adjusting the filters.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
        <div style="text-align: center; color: #666; padding: 2rem 0;">
            <p><strong>AI-Enabled Antibody Design Research Database</strong></p>
            <p>Data aggregated from SciSpace, Google Scholar, arXiv, and PubMed</p>
            <p>Last updated: November 2025</p>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
