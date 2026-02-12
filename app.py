import streamlit as st
import json
import pandas as pd
from datetime import datetime
import re
import os
import io
import html as html_module

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
    mark {
        background-color: #fff3cd;
        padding: 0 2px;
        border-radius: 2px;
    }
    .tldr-text {
        background-color: #f0f7ff;
        border-left: 3px solid #0066cc;
        padding: 0.5rem 1rem;
        margin: 0.5rem 0;
        font-size: 0.9rem;
        font-style: italic;
    }
    </style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data
def load_papers():
    """Load papers from the papertable file"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_file = os.path.join(script_dir, 'papers_data.papertable')
        with open(data_file, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        st.error(f"Error loading papers: {str(e)}")
        return None


@st.cache_data
def get_paper_column_id(papers_data):
    """Find the column ID for paper data"""
    for col in papers_data.get('columns', []):
        if 'Papers' in col.get('name', ''):
            return col['column_id']
    return None


@st.cache_data
def get_filter_options(papers_data):
    """Pre-compute all filter options from the dataset"""
    paper_col = get_paper_column_id(papers_data)
    if not paper_col:
        return [], [], []

    pub_types = set()
    journals = set()
    tags = set()

    for entry in papers_data.get('data', []):
        paper = entry.get(paper_col, {})
        if not paper:
            continue

        pt = paper.get('publication_type', '')
        if pt:
            pub_types.add(pt)

        j = paper.get('journal')
        if isinstance(j, dict):
            dn = j.get('display_name', '')
            if dn:
                journals.add(dn)

        rm = paper.get('relevance_metadata', {})
        for cj in rm.get('criteria_judgments', []):
            cn = cj.get('criterion_name', '')
            if cn:
                cn = cn.replace('\u2011', '-').replace('\u2010', '-')
                tags.add(cn)

    return sorted(pub_types), sorted(journals), sorted(tags)


def get_tag_counts(papers_data):
    """Count papers per topic tag (Perfectly/Highly Relevant only)"""
    paper_col = get_paper_column_id(papers_data)
    if not paper_col:
        return {}
    counts = {}
    for entry in papers_data.get('data', []):
        paper = entry.get(paper_col, {})
        rm = paper.get('relevance_metadata', {})
        for j in rm.get('criteria_judgments', []):
            rel = j.get('relevance', '')
            if rel in ('Perfectly Relevant', 'Highly Relevant'):
                name = j.get('criterion_name', '').replace('\u2011', '-').replace('\u2010', '-')
                if name:
                    counts[name] = counts.get(name, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Helpers: formatting
# ---------------------------------------------------------------------------

def extract_paper_info(paper_data, column_id):
    """Extract paper information from the data structure"""
    if column_id in paper_data:
        return paper_data[column_id]
    return None


def format_authors(authors):
    """Format author list from nested authors structure"""
    if not authors:
        return "Authors not available"

    if isinstance(authors, dict):
        author_list = authors.get('data', [])
        total = authors.get('total', len(author_list))
    elif isinstance(authors, list):
        author_list = authors
        total = len(authors)
    else:
        return str(authors)

    if not author_list:
        return "Authors not available"

    author_names = []
    for author in author_list[:5]:
        if isinstance(author, dict):
            name = author.get('display_name', '') or author.get('name', '')
            if name:
                author_names.append(name)
        elif isinstance(author, str):
            author_names.append(author)

    if not author_names:
        return "Authors not available"

    result = ", ".join(author_names)
    if total > 5:
        result += f" et al. ({total} authors)"
    return result


def extract_year(date_str):
    """Extract integer year from various date formats"""
    if not date_str or not isinstance(date_str, str):
        return None
    match = re.match(r'^(\d{4})', date_str.strip())
    if match:
        return int(match.group(1))
    return None


def format_date(date_str):
    """Format publication date from various formats"""
    if not date_str or not isinstance(date_str, str):
        return "Date not available"
    date_str = date_str.strip()
    # Strip time/timezone parts
    normalized = re.sub(r'[T ].*$', '', date_str)
    for fmt in ['%Y-%m-%d', '%Y-%m', '%Y']:
        try:
            date_obj = datetime.strptime(normalized, fmt)
            if fmt == '%Y':
                return str(date_obj.year)
            return date_obj.strftime('%B %Y')
        except ValueError:
            continue
    return date_str


def get_citation_count(metrics):
    """Extract citation count from metrics"""
    if not metrics or not isinstance(metrics, dict):
        return 0
    citations = metrics.get('citations', {})
    if isinstance(citations, dict):
        total = citations.get('total')
        if isinstance(total, (int, float)) and total > 0:
            return int(total)
    return 0


# ---------------------------------------------------------------------------
# Helpers: search engine
# ---------------------------------------------------------------------------

def tokenize_query(query):
    """Parse search query into tokens with AND/OR logic.

    Words separated by spaces are AND-ed by default.
    'OR' between words creates OR groups.
    Quoted phrases are treated as single tokens.

    Returns list of OR-groups where each group is a list of AND-tokens.
    """
    if not query or not query.strip():
        return []

    phrases = []

    def replace_phrase(match):
        phrases.append(match.group(1).lower())
        return f"__PHRASE{len(phrases) - 1}__"

    processed = re.sub(r'"([^"]+)"', replace_phrase, query)
    or_groups = re.split(r'\s+[Oo][Rr]\s+', processed)

    result = []
    for group in or_groups:
        tokens = group.lower().split()
        restored = []
        for token in tokens:
            m = re.match(r'__phrase(\d+)__', token)
            if m:
                restored.append(phrases[int(m.group(1))])
            else:
                restored.append(token)
        if restored:
            result.append(restored)
    return result


def text_matches_query(text, parsed_query):
    """Check if text matches parsed query (OR of AND groups)"""
    if not parsed_query:
        return True
    if not text:
        return False
    text_lower = text.lower()
    for and_group in parsed_query:
        if all(token in text_lower for token in and_group):
            return True
    return False


def get_searchable_text(paper):
    """Build combined searchable text from all relevant paper fields"""
    parts = [
        paper.get('title', ''),
        paper.get('abstract', ''),
        paper.get('tldr', ''),
        paper.get('relevance_summary', ''),
        paper.get('doi', ''),
    ]
    journal = paper.get('journal')
    if isinstance(journal, dict):
        parts.append(journal.get('display_name', ''))

    authors = paper.get('authors', {})
    if isinstance(authors, dict):
        for author in authors.get('data', []):
            if isinstance(author, dict):
                parts.append(author.get('display_name', ''))

    return ' '.join(filter(None, parts))


def highlight_text(text, query):
    """Add HTML highlight spans around matching query terms"""
    if not query or not text:
        return text
    escaped = html_module.escape(text)
    terms = set()
    clean_q = re.sub(r'"([^"]+)"', r'\1', query)
    for word in re.split(r'\s+(?:OR|or)\s+|\s+', clean_q):
        word = word.strip().strip('"')
        if word and len(word) > 2:
            terms.add(word)
    for term in terms:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        escaped = pattern.sub(
            lambda m: f'<mark>{m.group()}</mark>',
            escaped,
        )
    return escaped


# ---------------------------------------------------------------------------
# Helpers: display
# ---------------------------------------------------------------------------

TAG_COLORS = {
    "Perfectly Relevant": "#28a745",
    "Highly Relevant": "#007bff",
    "Somewhat Relevant": "#ffc107",
}


def render_topic_tags(judgments):
    """Render criteria judgments as colored tag chips"""
    tags_html = []
    for j in judgments:
        name = j.get('criterion_name', '').replace('\u2011', '-').replace('\u2010', '-')
        relevance = j.get('relevance', '')
        if relevance not in TAG_COLORS:
            continue
        color = TAG_COLORS[relevance]
        tags_html.append(
            f'<span style="background-color: {color}; color: white; '
            f'padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; '
            f'margin-right: 4px; display: inline-block; margin-bottom: 4px;">'
            f'{html_module.escape(name)}</span>'
        )
    if tags_html:
        return '<div style="margin: 4px 0 8px 0;">' + ''.join(tags_html) + '</div>'
    return ''


def get_best_paper_url(paper):
    """Extract the best available URL for a paper"""
    link = paper.get('link', '')
    if link:
        return link

    paper_urls = paper.get('paper_urls', {})
    if isinstance(paper_urls, dict):
        data = paper_urls.get('data', {})
        if isinstance(data, dict):
            for key in ['Html', 'Pdf', 'Others', 'Unknown']:
                urls = data.get(key, [])
                if isinstance(urls, list) and urls:
                    return urls[0]
        elif isinstance(data, list) and data:
            return data[0]

    doi = paper.get('doi', '')
    if doi:
        return f"https://doi.org/{doi}"
    return None


# ---------------------------------------------------------------------------
# Search / filter
# ---------------------------------------------------------------------------

def search_papers(papers_data, search_query, year_range, min_citations,
                  sources, publication_types=None, topic_tags=None,
                  author_filter="", journal_filter=None):
    """Filter papers based on search criteria"""
    if not papers_data or 'data' not in papers_data:
        return []

    paper_column_id = get_paper_column_id(papers_data)
    if not paper_column_id:
        return []

    parsed_query = tokenize_query(search_query)

    filtered_papers = []

    for paper_entry in papers_data['data']:
        paper = extract_paper_info(paper_entry, paper_column_id)
        if not paper:
            continue

        # Full-text tokenized search
        if parsed_query:
            searchable = get_searchable_text(paper)
            if not text_matches_query(searchable, parsed_query):
                continue

        # Year filter
        if year_range[0] or year_range[1]:
            year = extract_year(paper.get('date', ''))
            if year is not None:
                if year_range[0] and year < year_range[0]:
                    continue
                if year_range[1] and year > year_range[1]:
                    continue

        # Citation filter
        citations = get_citation_count(paper.get('metrics', {}))
        if citations < min_citations:
            continue

        # Source filter
        if sources:
            paper_source = paper.get('source', '').lower()
            if not any(source.lower() in paper_source for source in sources):
                continue

        # Publication type filter
        if publication_types:
            pt = paper.get('publication_type', '')
            if pt not in publication_types:
                continue

        # Topic tag filter
        if topic_tags:
            rm = paper.get('relevance_metadata', {})
            judgments = rm.get('criteria_judgments', [])
            paper_tags = set()
            for j in judgments:
                rel = j.get('relevance', '')
                if rel in ('Perfectly Relevant', 'Highly Relevant', 'Somewhat Relevant'):
                    cn = j.get('criterion_name', '').replace('\u2011', '-').replace('\u2010', '-')
                    paper_tags.add(cn)
            if not any(tag in paper_tags for tag in topic_tags):
                continue

        # Author filter
        if author_filter and author_filter.strip():
            author_lower = author_filter.strip().lower()
            authors_data = paper.get('authors', {})
            if isinstance(authors_data, dict):
                names = [a.get('display_name', '').lower()
                         for a in authors_data.get('data', []) if isinstance(a, dict)]
            else:
                names = []
            if not any(author_lower in n for n in names):
                continue

        # Journal filter
        if journal_filter:
            j = paper.get('journal')
            if not j or not isinstance(j, dict):
                continue
            if j.get('display_name', '') not in journal_filter:
                continue

        filtered_papers.append(paper)

    return filtered_papers


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_to_csv(papers):
    """Convert filtered papers to CSV bytes for download"""
    rows = []
    for paper in papers:
        journal = paper.get('journal', {})
        journal_name = journal.get('display_name', '') if isinstance(journal, dict) else ''
        doi = paper.get('doi', '')
        doi_url = f"https://doi.org/{doi}" if doi else ''

        rows.append({
            'Title': paper.get('title', ''),
            'Authors': format_authors(paper.get('authors', {})),
            'Year': extract_year(paper.get('date', '')) or '',
            'Date': paper.get('date', ''),
            'Journal': journal_name,
            'Publication Type': paper.get('publication_type', ''),
            'Source': paper.get('source', ''),
            'Citations': get_citation_count(paper.get('metrics', {})),
            'DOI': doi,
            'DOI URL': doi_url,
            'Rank': paper.get('rank', ''),
            'TLDR': paper.get('tldr', ''),
            'Relevance Summary': paper.get('relevance_summary', ''),
            'Abstract': paper.get('abstract', ''),
            'URL': get_best_paper_url(paper) or '',
        })

    df = pd.DataFrame(rows)
    return df.to_csv(index=False).encode('utf-8')


# ---------------------------------------------------------------------------
# Paper display
# ---------------------------------------------------------------------------

def display_paper(paper, index, search_query=""):
    """Display a single paper in a card format with enhanced info"""
    title = paper.get('title', 'Title not available')
    authors_str = format_authors(paper.get('authors', {}))
    date_str = format_date(paper.get('date', ''))
    source = paper.get('source', 'Unknown').upper()
    citations = get_citation_count(paper.get('metrics', {}))
    pub_type = paper.get('publication_type', '')
    rank = paper.get('rank', '')

    journal = paper.get('journal')
    journal_name = ''
    if isinstance(journal, dict):
        journal_name = journal.get('display_name', '')

    display_title = highlight_text(title, search_query) if search_query else html_module.escape(title)

    meta_parts = [f"📅 {date_str}"]
    if journal_name:
        meta_parts.append(f"📖 {html_module.escape(journal_name)}")
    meta_parts.append(f"📚 {html_module.escape(source)}")
    if pub_type:
        meta_parts.append(f"📄 {html_module.escape(pub_type)}")
    meta_parts.append(f"📊 {citations} citations")
    if rank:
        meta_parts.append(f"🏆 Rank #{rank}")

    st.markdown(f"""
        <div class="paper-card">
            <div class="paper-title">{index}. {display_title}</div>
            <div class="paper-authors">👥 {html_module.escape(authors_str)}</div>
            <div class="paper-meta">{' | '.join(meta_parts)}</div>
        </div>
    """, unsafe_allow_html=True)

    # TLDR shown directly
    tldr = paper.get('tldr', '')
    if tldr:
        st.markdown(
            f'<div class="tldr-text"><strong>TL;DR:</strong> {html_module.escape(tldr)}</div>',
            unsafe_allow_html=True,
        )

    # Topic tags as colored chips
    rm = paper.get('relevance_metadata', {})
    judgments = rm.get('criteria_judgments', [])
    if judgments:
        tag_html = render_topic_tags(judgments)
        if tag_html:
            st.markdown(tag_html, unsafe_allow_html=True)

    # Abstract in expandable section
    abstract = paper.get('abstract', 'Abstract not available')
    with st.expander("📄 View Abstract"):
        display_abstract = highlight_text(abstract, search_query) if search_query else html_module.escape(abstract)
        st.markdown(f'<div class="paper-abstract">{display_abstract}</div>', unsafe_allow_html=True)

    # Relevance summary in expandable section
    rel_summary = paper.get('relevance_summary', '')
    if rel_summary:
        with st.expander("🎯 Relevance Summary"):
            st.markdown(rel_summary)

    # Links row
    link_cols = st.columns([1, 1, 1, 1])

    with link_cols[0]:
        best_url = get_best_paper_url(paper)
        if best_url:
            st.link_button("🔗 View Paper", best_url, use_container_width=True)

    with link_cols[1]:
        fulltext_url = paper.get('fulltext_url', '')
        if fulltext_url:
            if fulltext_url.startswith('/pdf'):
                fulltext_url = f"https://scispace.com{fulltext_url}"
            st.link_button("📑 PDF", fulltext_url, use_container_width=True)

    with link_cols[2]:
        doi = paper.get('doi', '')
        if doi:
            doi_url = f"https://doi.org/{doi}" if not doi.startswith('http') else doi
            st.link_button("🔗 DOI", doi_url, use_container_width=True)

    st.markdown("---")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Session state init
    if 'selected_topic_tags' not in st.session_state:
        st.session_state['selected_topic_tags'] = []

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

    # Pre-compute filter options
    pub_types_opts, journal_opts, tag_opts = get_filter_options(papers_data)

    # ------------------------------------------------------------------
    # Sidebar filters
    # ------------------------------------------------------------------
    st.sidebar.header("🔍 Search & Filters")

    search_query = st.sidebar.text_input(
        "Search papers",
        placeholder='e.g., antibody design OR "deep learning" affinity',
        help=(
            "Search across titles, abstracts, authors, journals, TLDRs. "
            "Words are AND-ed by default. Use OR for alternatives. "
            'Use "quotes" for exact phrases.'
        ),
    )

    # Author search
    author_filter = st.sidebar.text_input(
        "🔎 Search by author",
        placeholder="e.g., Smith, Zhang...",
        help="Filter papers by author name (partial match)",
    )

    # Year range
    st.sidebar.subheader("📅 Publication Year")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        year_from = st.number_input("From", min_value=1990, max_value=2026, value=None, step=1)
    with col2:
        year_to = st.number_input("To", min_value=1990, max_value=2026, value=None, step=1)

    # Citation filter
    min_citations = st.sidebar.slider(
        "📊 Minimum Citations",
        min_value=0,
        max_value=500,
        value=0,
        step=10,
        help="Filter papers by minimum citation count",
    )

    # Source filter
    st.sidebar.subheader("📚 Data Sources")
    sources = st.sidebar.multiselect(
        "Filter by source",
        options=["SciSpace", "Google Scholar", "arXiv", "PubMed", "Full Text"],
        default=[],
        help="Select one or more sources to filter papers",
    )

    # Publication type filter
    st.sidebar.subheader("📄 Publication Type")
    publication_types = st.sidebar.multiselect(
        "Filter by type",
        options=pub_types_opts,
        default=[],
        help="Journal Article, Preprint, Posted Content, etc.",
    )

    # Journal filter
    if journal_opts:
        st.sidebar.subheader("📖 Journal")
        journal_filter = st.sidebar.multiselect(
            "Filter by journal",
            options=journal_opts,
            default=[],
            help="Filter papers by journal name",
        )
    else:
        journal_filter = []

    # Topic tag filter
    st.sidebar.subheader("🏷️ Topic Tags")
    topic_tags = st.sidebar.multiselect(
        "Filter by topic",
        options=tag_opts,
        default=st.session_state.get('selected_topic_tags', []),
        key='topic_tags_select',
        help="Show papers tagged with selected research topics",
    )

    # Sort options
    st.sidebar.subheader("📋 Sort By")
    sort_option = st.sidebar.selectbox(
        "Sort papers by",
        options=[
            "Relevance (Rank)",
            "Citations (High to Low)",
            "Year (Newest First)",
            "Year (Oldest First)",
            "Title (A-Z)",
        ],
        help="Choose how to sort the papers",
    )

    # ------------------------------------------------------------------
    # Apply filters
    # ------------------------------------------------------------------
    filtered_papers = search_papers(
        papers_data,
        search_query,
        (year_from, year_to),
        min_citations,
        sources,
        publication_types=publication_types or None,
        topic_tags=topic_tags or None,
        author_filter=author_filter,
        journal_filter=journal_filter or None,
    )

    # Sort
    if sort_option == "Relevance (Rank)":
        filtered_papers.sort(key=lambda x: x.get('rank', 9999))
    elif sort_option == "Citations (High to Low)":
        filtered_papers.sort(key=lambda x: get_citation_count(x.get('metrics', {})), reverse=True)
    elif sort_option == "Year (Newest First)":
        filtered_papers.sort(key=lambda x: extract_year(x.get('date', '')) or 0, reverse=True)
    elif sort_option == "Year (Oldest First)":
        filtered_papers.sort(key=lambda x: extract_year(x.get('date', '')) or 9999)
    elif sort_option == "Title (A-Z)":
        filtered_papers.sort(key=lambda x: x.get('title', '').lower())

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------
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
            years = [extract_year(p.get('date', '')) for p in filtered_papers]
            years = [y for y in years if y is not None]
            if years:
                st.metric("📅 Year Range", f"{min(years)}-{max(years)}")
            else:
                st.metric("📅 Year Range", "N/A")
        else:
            st.metric("📅 Year Range", "N/A")

    st.markdown("---")

    # ------------------------------------------------------------------
    # Quick topic tag browsing
    # ------------------------------------------------------------------
    tag_counts = get_tag_counts(papers_data)
    if tag_counts:
        with st.expander("🏷️ Browse by Topic", expanded=False):
            tag_cols = st.columns(3)
            for i, (tag, count) in enumerate(sorted(tag_counts.items(), key=lambda x: -x[1])):
                col = tag_cols[i % 3]
                with col:
                    if st.button(f"{tag} ({count})", key=f"tag_browse_{i}", use_container_width=True):
                        st.session_state['selected_topic_tags'] = [tag]
                        st.rerun()

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------
    if filtered_papers:
        col_results, col_export = st.columns([3, 1])
        with col_results:
            st.subheader(f"📖 Showing {len(filtered_papers)} Papers")
        with col_export:
            csv_data = export_to_csv(filtered_papers)
            st.download_button(
                label="📥 Export CSV",
                data=csv_data,
                file_name="antibody_papers_export.csv",
                mime="text/csv",
                use_container_width=True,
            )

        # Pagination
        papers_per_page = st.sidebar.number_input(
            "Papers per page",
            min_value=5,
            max_value=50,
            value=10,
            step=5,
        )

        total_pages = (len(filtered_papers) - 1) // papers_per_page + 1

        if total_pages > 1:
            page = st.sidebar.number_input(
                "Page",
                min_value=1,
                max_value=total_pages,
                value=1,
                step=1,
            )
        else:
            page = 1

        start_idx = (page - 1) * papers_per_page
        end_idx = min(start_idx + papers_per_page, len(filtered_papers))

        for i, paper in enumerate(filtered_papers[start_idx:end_idx], start=start_idx + 1):
            display_paper(paper, i, search_query)

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
