import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import CountVectorizer
from sentence_transformers import SentenceTransformer
import os
import re

class SieveEngine:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        print(f"Initializing SieveEngine with model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        print("SieveEngine model loaded successfully.")

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Compute sentence embeddings for a list of texts."""
        if not texts:
            return np.empty((0, 384))
        # sentence-transformers outputs a numpy array
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return np.array(embeddings)

    def cluster_and_sift(
        self, 
        texts: list[str], 
        n_clusters: int = 5, 
        outlier_percentile: float = 90.0
    ) -> dict:
        """
        Runs KMeans clustering on the text embeddings.
        Flags outliers based on Euclidean distance to centroids.
        Calculates c-TF-IDF to auto-label the clean clusters.
        """
        n_samples = len(texts)
        if n_samples == 0:
            return {"error": "Empty dataset"}

        # Adjust clusters if we have fewer samples than requested clusters
        actual_clusters = min(n_clusters, n_samples)
        if actual_clusters < 1:
            actual_clusters = 1

        # 1. Embed texts
        embeddings = self.embed_texts(texts)

        # 2. Fit K-Means
        kmeans = KMeans(n_clusters=actual_clusters, random_state=42, n_init='auto')
        cluster_labels = kmeans.fit_predict(embeddings)
        centroids = kmeans.cluster_centers_

        # 3. Calculate distance to assigned centroid for each point
        distances = np.zeros(n_samples)
        for i in range(n_samples):
            centroid = centroids[cluster_labels[i]]
            distances[i] = np.linalg.norm(embeddings[i] - centroid)

        # 4. Outlier classification
        # We classify points with distance > threshold as outliers
        # If outlier_percentile is 90.0, we flag the furthest 10% of points
        threshold = np.percentile(distances, outlier_percentile)
        
        final_labels = np.copy(cluster_labels)
        is_outlier = distances > threshold
        final_labels[is_outlier] = -1  # Mark outliers as -1

        # 5. PCA Projection for 2D visualization
        # We fit PCA on all embeddings to project them to 2D
        pca = PCA(n_components=2, random_state=42)
        coords_2d = pca.fit_transform(embeddings)
        x_coords = coords_2d[:, 0].tolist()
        y_coords = coords_2d[:, 1].tolist()

        # 6. c-TF-IDF Topic Modeling for clean clusters
        # Group clean texts by their KMeans cluster assignment
        clean_cluster_keywords = {}
        unique_clean_labels = sorted(list(set(cluster_labels))) # KMeans labels range from 0 to actual_clusters-1
        
        cluster_docs = []
        cluster_ids_present = []
        
        for cid in unique_clean_labels:
            # We construct document using texts in the cluster that are NOT outliers
            texts_in_cluster = [
                texts[i] for i in range(n_samples) 
                if cluster_labels[i] == cid and not is_outlier[i]
            ]
            if texts_in_cluster:
                cluster_docs.append(" ".join(texts_in_cluster))
                cluster_ids_present.append(cid)
            else:
                cluster_docs.append("")
                cluster_ids_present.append(cid)

        # Calculate c-TF-IDF if we have valid documents
        if any(doc != "" for doc in cluster_docs):
            try:
                # Basic tokenization setup, ignoring standard stop words
                vectorizer = CountVectorizer(stop_words='english', min_df=1)
                X = vectorizer.fit_transform(cluster_docs)
                words = vectorizer.get_feature_names_out()
                
                tf = X.toarray() # shape: (n_clusters, n_words)
                
                # Formula: log(1 + average_words_per_cluster / term_frequency_all_clusters)
                # We can use: log(1 + (average words per cluster / term frequency + 1e-9))
                # Or standard: log(1 + C / tf.sum(axis=0))
                C = len(cluster_ids_present)
                sum_tf = tf.sum(axis=0)
                idf = np.log(1 + (C / (sum_tf + 1e-9)))
                
                c_tf_idf = tf * idf
                
                for idx, cid in enumerate(cluster_ids_present):
                    row = c_tf_idf[idx]
                    if len(row) > 0:
                        top_word_indices = row.argsort()[-5:][::-1]
                        keywords = [words[w_idx] for w_idx in top_word_indices if row[w_idx] > 0]
                        clean_cluster_keywords[int(cid)] = keywords
                    else:
                        clean_cluster_keywords[int(cid)] = ["cluster", str(cid)]
            except Exception as e:
                print(f"c-TF-IDF extraction error: {e}")
                for cid in unique_clean_labels:
                    clean_cluster_keywords[int(cid)] = ["cluster", str(cid)]
        else:
            for cid in unique_clean_labels:
                clean_cluster_keywords[int(cid)] = ["cluster", str(cid)]

        # 7. Threat / Threat-like alert detection on Outliers & Clusters
        # Let's inspect outliers (label -1) and regular clusters for specific patterns (SQL Injection, script injection, Tracebacks, spam, gibberish)
        # We look for security anomalies
        security_patterns = {
            "SQL Injection": r"(select\s+.*\s+from|union\s+select|insert\s+into|delete\s+from|drop\s+table|where\s+.*=.*--|or\s+\d+=\d+)",
            "XSS Attack": r"(<script>|javascript:|onerror=|onload=|<iframe|alert\()",
            "Path Traversal": r"(\.\./\.\./|etc/passwd|/windows/win\.ini)",
            "System Error Log / Traceback": r"(traceback\s*\(most\s*recent|exception\s*in\s*thread|java\.lang\..*Exception|http\s+error\s+\d{3}|fatal\s+error|nullpointerexception)"
        }
        
        alerts = []
        
        # Check all outliers for security flags
        outlier_indices = np.where(is_outlier)[0]
        outlier_threats = {}
        for idx in outlier_indices:
            text = texts[idx]
            for threat_name, pattern in security_patterns.items():
                if re.search(pattern, text, re.IGNORECASE):
                    outlier_threats[threat_name] = outlier_threats.get(threat_name, 0) + 1
        
        for threat_name, count in outlier_threats.items():
            alerts.append({
                "type": "Outlier Threat",
                "message": f"Detected {count} instances of potential {threat_name} in the outlier (noise) cluster.",
                "severity": "High" if "Attack" in threat_name or "Injection" in threat_name else "Medium"
            })

        # Check clean clusters for general labeling/insights
        cluster_summaries = {}
        for cid in unique_clean_labels:
            indices = np.where((cluster_labels == cid) & (~is_outlier))[0]
            cluster_texts = [texts[i] for i in indices]
            
            # Check if this clean cluster itself is primarily composed of logs or tracebacks or threats
            threat_counts = {}
            for t in cluster_texts:
                for threat_name, pattern in security_patterns.items():
                    if re.search(pattern, t, re.IGNORECASE):
                        threat_counts[threat_name] = threat_counts.get(threat_name, 0) + 1
            
            dominant_threat = None
            for threat_name, count in threat_counts.items():
                if count > len(cluster_texts) * 0.4:  # If >40% of cluster matches
                    dominant_threat = threat_name
            
            keywords = clean_cluster_keywords.get(int(cid), [])
            
            # Formulate label
            if dominant_threat:
                label = f"Anomalous Cluster: {dominant_threat}"
                alerts.append({
                    "type": "Cluster Threat",
                    "message": f"Cluster {cid} is classified as '{dominant_threat}' with {threat_counts[dominant_threat]} matches. Downstream models should block this cluster.",
                    "severity": "Critical" if "Attack" in dominant_threat or "Injection" in dominant_threat else "High"
                })
            else:
                if keywords:
                    label = f"Cluster {cid}: " + ", ".join(keywords[:3])
                else:
                    label = f"Cluster {cid}"

            cluster_summaries[int(cid)] = {
                "label": label,
                "keywords": keywords,
                "size": len(indices),
                "representative_samples": cluster_texts[:5] if cluster_texts else []
            }

        # Format output
        results = {
            "texts": texts,
            "embeddings": embeddings.tolist(),
            "labels": final_labels.tolist(),  # Outliers are -1
            "original_kmeans_labels": cluster_labels.tolist(),
            "distances": distances.tolist(),
            "x": x_coords,
            "y": y_coords,
            "cluster_summaries": cluster_summaries,
            "alerts": alerts,
            "metrics": {
                "total_records": n_samples,
                "noise_count": int(np.sum(is_outlier)),
                "clean_count": int(np.sum(~is_outlier)),
                "noise_percentage": float(np.sum(is_outlier) / n_samples * 100) if n_samples > 0 else 0
            }
        }
        
        return results
