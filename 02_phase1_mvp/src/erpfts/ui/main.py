"""
Streamlit main application for ERPFTS Phase1 MVP

Provides the main Streamlit interface for the ERP Fit To Standard
knowledge search and management system.
"""

import streamlit as st
import requests
from typing import Dict, List, Any
import json

from ..core.config import settings

# Configure Streamlit page
st.set_page_config(
    page_title=settings.ui_title,
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# API base URL
API_BASE = f"http://{settings.api_host}:{settings.api_port}"


def check_api_connection() -> bool:
    """Check if the API is accessible."""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def search_knowledge(query: str, top_k: int = 10, threshold: float = 0.7) -> Dict[str, Any]:
    """Search the knowledge base via API."""
    try:
        response = requests.get(
            f"{API_BASE}/api/v1/search",
            params={
                "q": query,
                "top_k": top_k,
                "threshold": threshold,
            },
            timeout=30,
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Search failed: {response.status_code} - {response.text}")
            return {}
    except Exception as e:
        st.error(f"Search error: {str(e)}")
        return {}


def upload_document(file, source_type: str = "manual_upload") -> Dict[str, Any]:
    """Upload a document via API."""
    try:
        files = {"file": (file.name, file, file.type)}
        data = {"source_type": source_type}
        
        response = requests.post(
            f"{API_BASE}/api/v1/documents/upload",
            files=files,
            data=data,
            timeout=60,
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Upload failed: {response.status_code} - {response.text}")
            return {}
    except Exception as e:
        st.error(f"Upload error: {str(e)}")
        return {}


def get_knowledge_stats() -> Dict[str, Any]:
    """Get knowledge base statistics via API."""
    try:
        response = requests.get(f"{API_BASE}/api/v1/knowledge/stats", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {}
    except Exception:
        return {}


def main():
    """Main Streamlit application."""
    # Title and description
    st.title("🎯 ERP Fit To Standard - Knowledge Search")
    st.markdown("**Find answers in ERP standards and best practices**")
    
    # Check API connection
    if not check_api_connection():
        st.error("⚠️ Cannot connect to API server. Please ensure the API is running.")
        st.info(f"Expected API URL: {API_BASE}")
        st.stop()
    
    # Sidebar
    with st.sidebar:
        st.header("📊 System Status")
        
        # Knowledge base stats
        stats = get_knowledge_stats()
        if stats:
            st.metric("Documents", stats.get("total_documents", 0))
            st.metric("Knowledge Chunks", stats.get("total_chunks", 0))
            st.metric("Storage (MB)", f"{stats.get('storage_size_mb', 0):.1f}")
        
        st.header("📤 Upload Document")
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["pdf", "docx", "txt", "html"],
            help="Supported: PDF, DOCX, TXT, HTML (max 50MB)",
        )
        
        if uploaded_file and st.button("Upload"):
            with st.spinner("Uploading..."):
                result = upload_document(uploaded_file)
                if result:
                    st.success(f"✅ {result.get('message', 'Upload successful')}")
    
    # Main content
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.header("🔍 Knowledge Search")
        
        # Search input
        query = st.text_input(
            "What would you like to know?",
            placeholder="e.g., 'How to manage project risks in PMBOK?' or 'BABOK requirements analysis techniques'",
            help="Enter your question in natural language",
        )
        
        # Search options
        col_a, col_b = st.columns(2)
        with col_a:
            top_k = st.slider("Number of results", 1, 20, 10)
        with col_b:
            threshold = st.slider("Similarity threshold", 0.0, 1.0, 0.7, 0.1)
    
    with col2:
        st.header("📚 Quick Links")
        st.markdown("""
        **Standards Coverage:**
        - 📖 PMBOK Guide
        - 💼 BABOK Guide  
        - 📊 DMBOK Guide
        - ⚙️ SPEM Framework
        - 🏗️ TOGAF Framework
        - 📝 BIF Consulting Blog
        
        **Quick Searches:**
        """)
        
        quick_searches = [
            "Project risk management",
            "Requirements analysis",
            "Data governance",
            "Architecture patterns",
        ]
        
        for search in quick_searches:
            if st.button(f"🔍 {search}", key=f"quick_{search}"):
                query = search
    
    # Perform search
    if query:
        with st.spinner("Searching..."):
            results = search_knowledge(query, top_k, threshold)
        
        if results and results.get("results"):
            st.success(f"Found {results['total_results']} results in {results['search_time_ms']}ms")
            
            # Display results
            for i, result in enumerate(results["results"], 1):
                with st.expander(
                    f"📄 Result {i} - Score: {result['similarity_score']:.3f}",
                    expanded=i <= 3,
                ):
                    st.markdown(f"**Content:**")
                    st.markdown(result["content"])
                    
                    if result.get("metadata"):
                        st.markdown("**Metadata:**")
                        st.json(result["metadata"])
                    
                    if result.get("source_info"):
                        st.markdown("**Source:**")
                        st.json(result["source_info"])
        
        elif query:
            st.warning("No results found. Try different keywords or lower the similarity threshold.")
    
    # Footer
    st.markdown("---")
    st.markdown("*ERP Fit To Standard Knowledge System - Phase1 MVP*")


def run_app():
    """Run the Streamlit application."""
    main()


if __name__ == "__main__":
    run_app()