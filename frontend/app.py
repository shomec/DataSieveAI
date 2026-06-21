import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
import json
import io

# Setup Page Config
st.set_page_config(
    page_title="DataSieve AI - Automated Data Sanitization & Pattern Discovery",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Endpoint URL
BACKEND_URL = "http://localhost:8001"

# Inject Custom CSS for Rich Aesthetics
st.markdown("""
<style>
    /* Gradient Header */
    .main-header {
        background: linear-gradient(135deg, #6C3082, #1C0A35);
        padding: 2rem 2.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    }
    .main-header h1 {
        margin: 0;
        font-family: 'Outfit', 'Inter', sans-serif;
        font-weight: 800;
        font-size: 2.8rem;
        letter-spacing: -0.5px;
        color: white;
    }
    .main-header p {
        margin: 10px 0 0 0;
        font-size: 1.15rem;
        opacity: 0.9;
        font-weight: 300;
        color: white;
    }
    
    /* Metrics Box */
    .metric-container {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #0E1117;
        border: 1px solid #30363D;
        border-radius: 8px;
        padding: 1.25rem;
        flex: 1;
        text-align: center;
        transition: transform 0.2s ease-in-out;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: #58A6FF;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #8B949E;
        text-transform: uppercase;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 800;
        color: #58A6FF;
        margin: 0;
    }
    .metric-sub {
        font-size: 0.75rem;
        color: #8B949E;
        margin-top: 0.25rem;
    }
    
    /* Threat Cards */
    .threat-card {
        background-color: #1A0D1A;
        border: 1px solid #FF7B72;
        border-left: 6px solid #FF7B72;
        border-radius: 8px;
        padding: 1rem 1.5rem;
        margin-bottom: 1rem;
    }
    .threat-card.critical {
        background-color: #2D0F15;
        border-color: #FF5A5F;
        border-left-color: #FF5A5F;
    }
    
    /* Tags styling */
    .keyword-tag {
        display: inline-block;
        background-color: #21262D;
        border: 1px solid #30363D;
        color: #C9D1D9;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8rem;
        margin-right: 5px;
        margin-bottom: 5px;
        font-family: monospace;
    }
    
    /* Centered status message */
    .status-msg {
        font-size: 1.1rem;
        font-weight: 500;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Main Banner
st.markdown("""
<div class="main-header">
    <h1>🔍 DataSieve AI</h1>
    <p>Automated Unsupervised Data Sanitization & Pattern Discovery Engine</p>
</div>
""", unsafe_allow_html=True)

# Sidebar - Configuration and Ingestion
st.sidebar.image("https://img.icons8.com/nolan/96/filter.png", width=64)
st.sidebar.header("📁 Ingestion & Configuration")

# 1. Check Backend Status
backend_ready = False
try:
    status_response = requests.get(f"{BACKEND_URL}/api/status")
    status_data = status_response.json()
    if status_data.get("status") == "ready":
        backend_ready = True
        st.sidebar.success("Backend: Ready (Embedding Model Loaded)")
    else:
        st.sidebar.warning("Backend: Embedding Model Loading...")
except Exception:
    st.sidebar.error("Backend: Offline (Start the FastAPI server on port 8001)")

# Data Ingestion Options
st.sidebar.subheader("Dataset Ingestion")
data_source = st.sidebar.radio(
    "Select Input Data Source",
    ["Load Synthetic RAG Dataset (Recommended)", "Upload CSV File"]
)

texts_to_process = []
uploaded_file = None
text_column = ""

if data_source == "Load Synthetic RAG Dataset (Recommended)":
    st.sidebar.info("Generates a mixture of customer support queries, SQL injection scripts, web tracebacks, and spam.")
    if st.sidebar.button("Generate Synthetic Data"):
        if backend_ready:
            with st.spinner("Generating dataset..."):
                try:
                    res = requests.get(f"{BACKEND_URL}/api/generate_synthetic")
                    if res.status_code == 200:
                        st.session_state["raw_texts"] = res.json()["texts"]
                        st.sidebar.success(f"Generated {len(st.session_state['raw_texts'])} records!")
                    else:
                        st.sidebar.error("Failed to generate synthetic data.")
                except Exception as e:
                    st.sidebar.error(f"Error: {e}")
        else:
            st.sidebar.error("Backend model is still loading, please wait.")

else:
    uploaded_file = st.sidebar.file_uploader("Upload CSV file containing text columns", type=["csv"])
    if uploaded_file is not None:
        try:
            # Read header first
            df_preview = pd.read_csv(uploaded_file, nrows=5)
            text_columns = [col for col in df_preview.columns if df_preview[col].dtype == 'object']
            if not text_columns:
                st.sidebar.error("No text-like columns found in CSV!")
            else:
                text_column = st.sidebar.selectbox("Select Text Column", text_columns)
                # Read all data
                uploaded_file.seek(0)
                df_full = pd.read_csv(uploaded_file)
                texts_to_process = df_full[text_column].dropna().astype(str).tolist()
                st.sidebar.success(f"Loaded {len(texts_to_process)} rows.")
        except Exception as e:
            st.sidebar.error(f"Error loading CSV: {e}")

# Sidebar Algorithm Controls
st.sidebar.subheader("ML Hyperparameters")
n_clusters = st.sidebar.slider(
    "Number of Clusters (K-Means K)", 
    min_value=2, 
    max_value=12, 
    value=5, 
    help="How many topic partitions to fit on the embedding vectors."
)

outlier_percentile = st.sidebar.slider(
    "Outlier Distance Percentile", 
    min_value=50, 
    max_value=99, 
    value=90, 
    help="Points whose distance to their assigned centroid is above this percentile are sifted as outliers (noise). E.g., 90th percentile flags the top 10% most distant points."
)

# Process Button
run_sieve = False
if "raw_texts" in st.session_state and data_source == "Load Synthetic RAG Dataset (Recommended)":
    texts_to_process = st.session_state["raw_texts"]

if len(texts_to_process) > 0:
    run_sieve = st.sidebar.button("⚡ Run Sieve Engine", use_container_width=True)
else:
    st.sidebar.warning("Load or upload a dataset to enable the sieve processing.")

# Main Application Screen
if not run_sieve and "sieve_results" not in st.session_state:
    # Educational Landing Page
    st.markdown("""
    ### Why is Unsupervised Data Sanitization Important?
    
    In the rush to build RAG (Retrieval-Augmented Generation) systems, semantic search, or fine-tuning pipelines, developers often **dump unverified text documents directly into vector databases**. 
    
    This **"garbage in, garbage out"** approach creates major issues:
    *   **Hallucinations & Noise:** Corrupt files, HTTP log dumps, and duplicate scrapings distort the vector search space, leading to irrelevant context fetches.
    *   **Security Vulnerabilities:** Direct user inputs containing SQL Injections or prompt injection scripts bypass filters and poison the semantic index, exposing downstream systems to breaches.
    *   **Poor Model Training:** Outliers skew distributions, resulting in misaligned weights and degrades accuracy.
    
    ### How DataSieve AI Guards Your Pipeline
    
    DataSieve runs a lightweight, unsupervised sifting flow:
    1.  **Semantic Embedding:** Translates raw textual data into a high-dimensional dense vector space using a local Hugging Face transformer model.
    2.  **K-Means Partitioning:** Groups semantically similar texts together.
    3.  **Euclidean Centroid Thresholding:** Identifies points located at the sparse edges of clusters (outliers/noise) and isolates them automatically.
    4.  **c-TF-IDF Topic Modeling:** Auto-extracts terms to describe each dense cluster without human annotators or expensive LLM API calls.
    5.  **Anomalous Thread Isolation:** Flags script injections, tracebacks, and alerts security guards in real-time.
    
    ***
    **To start, load the synthetic dataset in the sidebar, or upload a custom CSV!**
    """)
    
    if "raw_texts" in st.session_state:
        st.subheader("📋 Loaded Raw Data Preview")
        st.dataframe(pd.DataFrame({"Raw Text": st.session_state["raw_texts"]}).head(15), use_container_width=True)

else:
    # We have execution triggers
    if run_sieve:
        with st.spinner("Embedding dataset & running clustering (Executing locally)..."):
            try:
                payload = {
                    "texts": texts_to_process,
                    "n_clusters": n_clusters,
                    "outlier_percentile": outlier_percentile
                }
                res = requests.post(f"{BACKEND_URL}/api/sift", json=payload)
                if res.status_code == 200:
                    st.session_state["sieve_results"] = res.json()
                    st.session_state["original_texts"] = texts_to_process
                else:
                    st.error(f"Error sifting: {res.text}")
            except Exception as e:
                st.error(f"Failed to connect to backend: {e}")

    # Display Results
    if "sieve_results" in st.session_state:
        results = st.session_state["sieve_results"]
        metrics = results["metrics"]
        
        # Display Metrics Dashboard Row
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-card">
                <div class="metric-label">Total Ingested Data</div>
                <div class="metric-value">{metrics['total_records']}</div>
                <div class="metric-sub">Raw inputs processed</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Clean Core Records</div>
                <div class="metric-value" style="color: #2EA043;">{metrics['clean_count']}</div>
                <div class="metric-sub">Dense cluster signal (High Quality)</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Sifted Outliers / Noise</div>
                <div class="metric-value" style="color: #F85149;">{metrics['noise_count']}</div>
                <div class="metric-sub">Sparse vectors isolated</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Purge Ratio</div>
                <div class="metric-value" style="color: #FFC53D;">{metrics['noise_percentage']:.1f}%</div>
                <div class="metric-sub">Percent of dataset discarded</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Build DataFrame for visualization
        df = pd.DataFrame({
            "Text": results["texts"],
            "Label": results["labels"],
            "Original_KMeans_Label": results["original_kmeans_labels"],
            "Distance": results["distances"],
            "x": results["x"],
            "y": results["y"]
        })
        
        # Map labels to human-readable strings
        df["Type"] = df["Label"].apply(lambda l: "Sifted Outlier (Noise)" if l == -1 else f"Core Cluster {l}")
        
        # Create Tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Visual Cluster Map", 
            "🔍 Discovered Topics & Clusters", 
            "🚨 System Guardrails & Threats", 
            "💾 Clean Dataset Export"
        ])
        
        with tab1:
            st.subheader("2D Projection of Embedded Vectors (PCA)")
            st.markdown("""
            This plot maps the high-dimensional sentence embeddings down to a 2D space. 
            *   **Dense groups** are core semantic topics (valid content).
            *   **Scattered, isolated points** are outliers (marked in red), representing corrupted texts, threat scripts, or off-topic anomalies that are filtered out.
            """)
            
            # Create interactive plotly scatter
            fig = px.scatter(
                df,
                x="x",
                y="y",
                color="Type",
                hover_data={"Text": True, "Distance": ":.4f", "x": False, "y": False},
                title="Embedding Space Semantic Clustering & Outlier Isolation",
                color_discrete_map={
                    "Sifted Outlier (Noise)": "#FF5A5F",
                    **{f"Core Cluster {i}": px.colors.qualitative.Plotly[i % 10] for i in range(12)}
                },
                labels={"color": "Cluster Assignment"}
            )
            
            # Style improvements
            fig.update_traces(marker=dict(size=8, opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))
            fig.update_layout(
                plot_bgcolor="#0E1117",
                paper_bgcolor="#0E1117",
                font_color="#C9D1D9",
                height=600,
                xaxis=dict(showgrid=True, gridcolor="#30363D", zeroline=False),
                yaxis=dict(showgrid=True, gridcolor="#30363D", zeroline=False),
            )
            st.plotly_chart(fig, use_container_width=True)
            
        with tab2:
            st.subheader("Cluster Breakdown & Auto-Labeling (c-TF-IDF)")
            st.markdown("""
            DataSieve groups documents using K-Means and identifies their core themes without human labeling.
            Below is the topic summary and sample texts of each **Clean Core Cluster**.
            """)
            
            summaries = results["cluster_summaries"]
            for cid_str, summary in summaries.items():
                cid = int(cid_str)
                # Display cluster header
                st.markdown(f"#### 📂 {summary['label']}")
                
                # Render c-TF-IDF tag pills
                keywords = summary["keywords"]
                keyword_html = ""
                for kw in keywords:
                    keyword_html += f'<span class="keyword-tag">{kw}</span>'
                
                st.markdown(f"**Key Words:** {keyword_html if keyword_html else '*None extracted*'}", unsafe_allow_html=True)
                st.markdown(f"**Size:** {summary['size']} records")
                
                # Show sample texts
                with st.expander("View Cluster Samples"):
                    sample_df = pd.DataFrame({"Sample Texts": summary["representative_samples"]})
                    st.dataframe(sample_df, use_container_width=True)
                
                st.markdown("---")
                
        with tab3:
            st.subheader("🛡️ Automated System Guardrail & Threats")
            st.markdown("""
            By scanning isolated outliers and cluster anomalies, DataSieve detects structural or security threats.
            These alerts indicate that your ingestion pipeline is receiving noise that should be rejected at the firewall/gateway level.
            """)
            
            alerts = results["alerts"]
            if not alerts:
                st.success("✅ No critical security threats or log abnormalities detected in the outliers.")
            else:
                for alert in alerts:
                    severity = alert.get("severity", "Medium")
                    alert_type = alert.get("type", "Security Anomaly")
                    message = alert.get("message", "")
                    
                    if severity == "Critical" or severity == "High":
                        card_class = "threat-card critical"
                        badge_color = "🔴 CRITICAL THREAT"
                    else:
                        card_class = "threat-card"
                        badge_color = "🟡 SYSTEM WARNING"
                        
                    st.markdown(f"""
                    <div class="{card_class}">
                        <div style="font-weight: 800; font-size: 0.95rem; margin-bottom: 0.5rem;">{badge_color} ({alert_type})</div>
                        <div style="font-size: 1rem; color: #C9D1D9;">{message}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
            st.markdown("""
            ### Dynamic Guardrail Action Plan
            When DataSieve flags these clusters:
            1.  **API Gateway Rule:** Block user accounts or IP ranges generating inputs in anomalous threat clusters.
            2.  **Firewall Update:** Ingest the extracted c-TF-IDF keyword signatures (e.g. `union, select, script`) directly into a Web Application Firewall (WAF) or semantic guardrail filter (e.g., Llama Guard).
            3.  **Sanitization Script:** Strip stack traces and tracebacks from raw database exports before vectorizing them for your RAG model.
            """)
            
        with tab4:
            st.subheader("💾 Export Clean & Safe Dataset")
            st.markdown("""
            Download the sanitised data. Outliers, tracebacks, and attack scripts have been removed, leaving only the pristine semantic clusters.
            """)
            
            # Filter clean data
            df_clean = df[df["Label"] != -1][["Text", "Original_KMeans_Label"]]
            df_clean.columns = ["Clean Text", "Cluster Assignment"]
            
            # Filter outliers
            df_outliers = df[df["Label"] == -1][["Text", "Distance"]]
            df_outliers.columns = ["Isolated Text / Noise", "Centroid Distance"]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"##### Pristine Core Dataset ({len(df_clean)} rows)")
                st.dataframe(df_clean.head(100), use_container_width=True)
                
                # Convert to CSV
                csv_clean = df_clean.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Clean CSV",
                    data=csv_clean,
                    file_name="datasieve_cleaned_dataset.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
            with col2:
                st.markdown(f"##### Isolated Outliers / Noise ({len(df_outliers)} rows)")
                st.dataframe(df_outliers.head(100), use_container_width=True)
                
                # Convert to CSV
                csv_outliers = df_outliers.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Isolated Outliers CSV",
                    data=csv_outliers,
                    file_name="datasieve_isolated_outliers.csv",
                    mime="text/csv",
                    use_container_width=True
                )
