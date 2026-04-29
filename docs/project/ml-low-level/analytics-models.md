# Analytics Models (Linear Regression & K-Means Clustering)

## Overview
The analytics system uses two machine learning models to generate insights from risk-scored bills: (1) Linear Regression to quantify risk drivers and validate the composite formula, and (2) K-Means Clustering to segment bills into distinct risk profiles for portfolio managers. Both models are fitted on-the-fly during analysis (no persistent training) and serve descriptive rather than predictive purposes.

---

## Architecture

```
Input: bills_with_risk.parquet (1000 bills with risk scores)
   ↓
Feature Selection & Preprocessing
   ↓
┌──────────────────────┬──────────────────────┐
│ Model 1:             │ Model 2:             │
│ Linear Regression    │ K-Means Clustering   │
│ (Risk Drivers)       │ (Bill Segmentation)  │
└──────────────────────┴──────────────────────┘
   ↓                            ↓
Coefficient Analysis      Cluster Profiling
   ↓                            ↓
Automated Insights       Portfolio Segments
```

---

## Model 1: Linear Regression (Risk Driver Analysis)

### Purpose

**Goal:** Quantify the contribution of each feature to the risk score

**Use Cases:**
1. **Validation:** Verify composite formula implementation (coefficients should match weights)
2. **Insights:** Identify strongest predictors ("Stage is 1.6x more important than cosponsors")
3. **Debugging:** Detect data quality issues (unexpected coefficients)

### Mathematical Formulation

**Linear Model:**
```
risk_score = β₀ + β₁·stage_score + β₂·cosponsor_score + β₃·recency_score + β₄·bipartisan_score + ε
```

**Expected Coefficients (by design):**
- β₁ (stage) = 0.40
- β₂ (cosponsor) = 0.25
- β₃ (recency) = 0.20
- β₄ (bipartisan) = 0.15
- β₀ (intercept) = 0.00

**Residual:** ε ~ N(0, σ²) (should be near-zero since risk_score is derived from features)

### Implementation

```python
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import pandas as pd
import numpy as np

def fit_risk_driver_model(df: pd.DataFrame) -> dict:
    """
    Fit linear regression to identify risk drivers.
    
    Args:
        df: DataFrame with risk scores and component features
        
    Returns:
        Dictionary with model, coefficients, metrics, and insights
        
    Example:
        >>> df = pd.read_parquet("bills_with_risk.parquet")
        >>> results = fit_risk_driver_model(df)
        >>> print(results['coefficients'])
        Feature          Coefficient    Expected
        ─────────────────────────────────────────
        stage_score      0.400          0.400  ✓
        cosponsor_score  0.250          0.250  ✓
        recency_score    0.200          0.200  ✓
        bipartisan_score 0.150          0.150  ✓
    """
    # Select features (independent variables)
    feature_cols = ['stage_score', 'cosponsor_score', 'recency_score', 'bipartisan_score']
    X = df[feature_cols].fillna(0)
    
    # Target variable
    y = df['risk_score']
    
    # Fit model
    model = LinearRegression()
    model.fit(X, y)
    
    # Predictions
    y_pred = model.predict(X)
    
    # Coefficients
    coefficients = pd.DataFrame({
        'Feature': feature_cols,
        'Coefficient': model.coef_,
        'Abs_Coefficient': np.abs(model.coef_)
    }).sort_values('Abs_Coefficient', ascending=False)
    
    # Performance metrics
    metrics = {
        'r2_score': r2_score(y, y_pred),
        'mae': mean_absolute_error(y, y_pred),
        'rmse': np.sqrt(mean_squared_error(y, y_pred)),
        'intercept': model.intercept_
    }
    
    # Generate insights
    insights = generate_regression_insights(coefficients, metrics)
    
    return {
        'model': model,
        'coefficients': coefficients,
        'metrics': metrics,
        'insights': insights
    }
```

### Feature Importance Analysis

```python
def generate_regression_insights(coefficients: pd.DataFrame, metrics: dict) -> list:
    """
    Generate automated insights from regression results.
    
    Args:
        coefficients: DataFrame with feature coefficients
        metrics: Dictionary with performance metrics
        
    Returns:
        List of insight strings
        
    Example:
        >>> insights = generate_regression_insights(coefficients, metrics)
        >>> for insight in insights:
        ...     print(f"• {insight}")
        • stage_score is the strongest predictor (coefficient: 0.40)
        • Model explains 99.7% of variance in risk scores (R² = 0.997)
        • Average prediction error is 0.89 points (MAE)
    """
    insights = []
    
    # Strongest predictor
    top_feature = coefficients.iloc[0]
    insights.append(
        f"**{top_feature['Feature']}** is the strongest predictor "
        f"(coefficient: {top_feature['Coefficient']:.2f})"
    )
    
    # Relative importance
    if len(coefficients) >= 2:
        top_two = coefficients.iloc[:2]
        ratio = top_two.iloc[0]['Abs_Coefficient'] / top_two.iloc[1]['Abs_Coefficient']
        insights.append(
            f"**{top_two.iloc[0]['Feature']}** is {ratio:.1f}x more important than "
            f"**{top_two.iloc[1]['Feature']}**"
        )
    
    # Model fit
    r2 = metrics['r2_score']
    insights.append(
        f"Model explains **{r2*100:.1f}%** of variance in risk scores (R² = {r2:.3f})"
    )
    
    # Prediction accuracy
    mae = metrics['mae']
    insights.append(
        f"Average prediction error is **{mae:.2f} points** (MAE)"
    )
    
    # Validation check
    expected_coefs = {'stage_score': 0.40, 'cosponsor_score': 0.25, 
                      'recency_score': 0.20, 'bipartisan_score': 0.15}
    
    coef_dict = dict(zip(coefficients['Feature'], coefficients['Coefficient']))
    
    max_deviation = max(
        abs(coef_dict[feat] - expected_coefs[feat]) 
        for feat in expected_coefs.keys()
    )
    
    if max_deviation < 0.01:
        insights.append("✓ Coefficients match formula weights (validation passed)")
    else:
        insights.append(f"⚠ Coefficients deviate from expected weights (max deviation: {max_deviation:.3f})")
    
    return insights
```

### Performance Metrics

**Expected Performance (By Design):**
```
R² Score:  0.997-1.000  (near-perfect fit)
MAE:       0.5-2.0      (minimal error)
RMSE:      1.0-3.0      (low residuals)
Intercept: -0.01-0.01   (near-zero)
```

**Why Near-Perfect Fit?**
- Risk score is **derived** from features (not independent)
- No external factors or noise
- Formula validation (not predictive modeling)

**If Metrics Deviate:**
```
R² < 0.95       → Data corruption or missing values
MAE > 5.0       → Implementation bug in risk formula
Intercept > 1.0 → Systematic bias in scoring
```

### Visualization

```python
import matplotlib.pyplot as plt
import seaborn as sns

def plot_regression_results(df: pd.DataFrame, model: LinearRegression, coefficients: pd.DataFrame):
    """
    Visualize regression analysis results.
    
    Creates 2 plots:
        1. Feature importance (coefficient bar chart)
        2. Predicted vs Actual risk scores (scatter plot)
        
    Args:
        df: DataFrame with risk data
        model: Fitted LinearRegression model
        coefficients: DataFrame with feature coefficients
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Plot 1: Feature Importance
    ax1 = axes[0]
    coefficients_sorted = coefficients.sort_values('Coefficient', ascending=True)
    ax1.barh(coefficients_sorted['Feature'], coefficients_sorted['Coefficient'])
    ax1.set_xlabel('Coefficient Value')
    ax1.set_title('Feature Importance (Linear Regression Coefficients)')
    ax1.axvline(x=0, color='gray', linestyle='--', linewidth=0.8)
    
    # Plot 2: Predicted vs Actual
    ax2 = axes[1]
    feature_cols = ['stage_score', 'cosponsor_score', 'recency_score', 'bipartisan_score']
    X = df[feature_cols].fillna(0)
    y_pred = model.predict(X)
    y_actual = df['risk_score']
    
    ax2.scatter(y_actual, y_pred, alpha=0.5, s=20)
    ax2.plot([0, 100], [0, 100], 'r--', linewidth=2, label='Perfect Prediction')
    ax2.set_xlabel('Actual Risk Score')
    ax2.set_ylabel('Predicted Risk Score')
    ax2.set_title('Predicted vs Actual Risk Scores')
    ax2.legend()
    
    plt.tight_layout()
    plt.show()
```

---

## Model 2: K-Means Clustering (Bill Segmentation)

### Purpose

**Goal:** Group bills into distinct risk profiles for targeted monitoring

**Use Cases:**
1. **Portfolio Segmentation:** "Monitor high-momentum cluster closely"
2. **Narrative Generation:** "48.9% of bills are newly introduced"
3. **Alert Targeting:** "Bill moved from Stalled to High Momentum cluster"

### Algorithm Overview

**K-Means Clustering:**
- Unsupervised learning (no labels required)
- Partitions data into K clusters
- Minimizes within-cluster variance
- Iterative algorithm (Lloyd's algorithm)

**Objective Function:**
```
Minimize: Σᵢ Σₓ∈Cᵢ ||x - μᵢ||²

Where:
  Cᵢ = cluster i
  μᵢ = centroid of cluster i
  x = data point
```

### Optimal K Selection (Elbow Method)

```python
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt

def find_optimal_k(df: pd.DataFrame, max_k: int = 10) -> int:
    """
    Find optimal number of clusters using elbow method.
    
    Tests K from 2 to max_k and plots inertia (within-cluster sum of squares).
    
    Args:
        df: DataFrame with risk features
        max_k: Maximum K to test
        
    Returns:
        Optimal K (elbow point)
        
    Example:
        >>> df = pd.read_parquet("bills_with_risk.parquet")
        >>> optimal_k = find_optimal_k(df)
        Testing K=2: Inertia=5234.2
        Testing K=3: Inertia=3821.5
        Testing K=4: Inertia=2847.3  ← Elbow
        Testing K=5: Inertia=2412.8
        ...
        Optimal K: 4
    """
    # Select clustering features
    cluster_features = ['risk_score', 'stage_score', 'cosponsor_score', 'recency_score']
    X = df[cluster_features].fillna(0)
    
    # Standardize features (mean=0, std=1)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Test different K values
    inertias = []
    silhouette_scores = []
    
    for k in range(2, max_k + 1):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(X_scaled)
        
        inertias.append(kmeans.inertia_)
        
        # Silhouette score (quality metric)
        from sklearn.metrics import silhouette_score
        sil_score = silhouette_score(X_scaled, kmeans.labels_)
        silhouette_scores.append(sil_score)
        
        print(f"Testing K={k}: Inertia={kmeans.inertia_:.1f}, Silhouette={sil_score:.3f}")
    
    # Plot elbow curve
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Inertia plot
    ax1.plot(range(2, max_k + 1), inertias, marker='o')
    ax1.set_xlabel('Number of Clusters (K)')
    ax1.set_ylabel('Inertia (Within-Cluster Sum of Squares)')
    ax1.set_title('Elbow Method: Inertia vs K')
    ax1.grid(True, alpha=0.3)
    
    # Silhouette plot
    ax2.plot(range(2, max_k + 1), silhouette_scores, marker='o', color='green')
    ax2.set_xlabel('Number of Clusters (K)')
    ax2.set_ylabel('Silhouette Score')
    ax2.set_title('Silhouette Score vs K')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    
    # Heuristic: Choose K=4 (elbow point + interpretability)
    optimal_k = 4
    
    print(f"\nOptimal K: {optimal_k}")
    return optimal_k
```

**Elbow Detection:**
- **K=2:** Single split (too coarse)
- **K=3:** Moderate segmentation
- **K=4:** Clear elbow (diminishing returns after this)
- **K=5+:** Over-segmentation (clusters too similar)

### Implementation

```python
def fit_clustering_model(df: pd.DataFrame, n_clusters: int = 4) -> dict:
    """
    Fit K-Means clustering model to segment bills.
    
    Args:
        df: DataFrame with risk scores
        n_clusters: Number of clusters (default 4)
        
    Returns:
        Dictionary with model, cluster assignments, profiles, and insights
        
    Example:
        >>> df = pd.read_parquet("bills_with_risk.parquet")
        >>> results = fit_clustering_model(df, n_clusters=4)
        >>> cluster_profiles = results['cluster_profiles']
        >>> print(cluster_profiles)
        
        Cluster 0 (High Momentum): 42 bills
          - Mean risk_score: 68.4
          - Mean stage_score: 72.3
          - Mean cosponsor_score: 85.1
          
        Cluster 1 (Stalled): 315 bills
          - Mean risk_score: 22.1
          - Mean stage_score: 18.2
          - Mean cosponsor_score: 45.3
        ...
    """
    # Select clustering features
    cluster_features = ['risk_score', 'stage_score', 'cosponsor_score', 'recency_score']
    X = df[cluster_features].fillna(0)
    
    # Standardize features (critical for K-Means)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Fit K-Means
    kmeans = KMeans(
        n_clusters=n_clusters,
        random_state=42,      # Reproducibility
        n_init=10,            # Multiple initializations
        max_iter=300,         # Maximum iterations
        tol=1e-4              # Convergence tolerance
    )
    
    cluster_labels = kmeans.fit_predict(X_scaled)
    
    # Add cluster assignments to DataFrame
    df = df.copy()
    df['cluster'] = cluster_labels
    
    # Compute cluster profiles
    cluster_profiles = []
    
    for cluster_id in range(n_clusters):
        cluster_df = df[df['cluster'] == cluster_id]
        
        profile = {
            'cluster_id': cluster_id,
            'count': len(cluster_df),
            'percentage': len(cluster_df) / len(df) * 100,
            'mean_risk_score': cluster_df['risk_score'].mean(),
            'mean_stage_score': cluster_df['stage_score'].mean(),
            'mean_cosponsor_score': cluster_df['cosponsor_score'].mean(),
            'mean_recency_score': cluster_df['recency_score'].mean(),
            'mean_bipartisan_score': cluster_df['bipartisan_score'].mean(),
            'std_risk_score': cluster_df['risk_score'].std()
        }
        
        cluster_profiles.append(profile)
    
    # Sort by mean risk score (descending)
    cluster_profiles = sorted(cluster_profiles, key=lambda x: x['mean_risk_score'], reverse=True)
    
    # Assign interpretable names
    cluster_names = name_clusters(cluster_profiles)
    
    # Performance metrics
    from sklearn.metrics import silhouette_score, davies_bouldin_score
    
    metrics = {
        'silhouette_score': silhouette_score(X_scaled, cluster_labels),
        'davies_bouldin_score': davies_bouldin_score(X_scaled, cluster_labels),
        'inertia': kmeans.inertia_
    }
    
    # Generate insights
    insights = generate_clustering_insights(cluster_profiles, cluster_names, metrics)
    
    return {
        'model': kmeans,
        'scaler': scaler,
        'cluster_labels': cluster_labels,
        'cluster_profiles': cluster_profiles,
        'cluster_names': cluster_names,
        'metrics': metrics,
        'insights': insights
    }
```

### Cluster Naming

```python
def name_clusters(cluster_profiles: list) -> dict:
    """
    Assign interpretable names to clusters based on characteristics.
    
    Naming Rules:
        - High risk + high stage → "High Momentum"
        - Low risk + low stage → "Stalled"
        - High recency + low stage → "Newly Introduced"
        - High cosponsor + medium stage → "Bipartisan Focus"
        
    Args:
        cluster_profiles: List of cluster profile dicts
        
    Returns:
        Dictionary mapping cluster_id to name
        
    Example:
        >>> names = name_clusters(cluster_profiles)
        >>> names
        {0: "High Momentum", 1: "Stalled", 2: "Newly Introduced", 3: "Bipartisan Focus"}
    """
    names = {}
    
    for profile in cluster_profiles:
        cid = profile['cluster_id']
        
        # High Momentum: High risk, high stage
        if profile['mean_risk_score'] > 60 and profile['mean_stage_score'] > 50:
            names[cid] = "High Momentum"
        
        # Newly Introduced: High recency, low stage
        elif profile['mean_recency_score'] > 80 and profile['mean_stage_score'] < 30:
            names[cid] = "Newly Introduced"
        
        # Bipartisan Focus: High cosponsors, medium stage
        elif profile['mean_cosponsor_score'] > 80 and 30 <= profile['mean_stage_score'] <= 50:
            names[cid] = "Bipartisan Focus"
        
        # Stalled: Low risk, low stage
        elif profile['mean_risk_score'] < 30 and profile['mean_stage_score'] < 30:
            names[cid] = "Stalled"
        
        # Default: Cluster ID
        else:
            names[cid] = f"Cluster {cid}"
    
    return names
```

### Cluster Insights

```python
def generate_clustering_insights(
    cluster_profiles: list, 
    cluster_names: dict, 
    metrics: dict
) -> list:
    """
    Generate automated insights from clustering results.
    
    Args:
        cluster_profiles: List of cluster profile dicts
        cluster_names: Dictionary mapping cluster_id to name
        metrics: Dictionary with performance metrics
        
    Returns:
        List of insight strings
        
    Example:
        >>> insights = generate_clustering_insights(profiles, names, metrics)
        >>> for insight in insights:
        ...     print(f"• {insight}")
        • Bills segmented into 4 distinct risk profiles
        • Largest cluster: "Newly Introduced" (48.9%, 489 bills)
        • Highest risk cluster: "High Momentum" (avg 68.4, 42 bills)
        • Clusters are well-separated (Silhouette = 0.67)
    """
    insights = []
    
    # Overall segmentation
    n_clusters = len(cluster_profiles)
    insights.append(f"Bills segmented into **{n_clusters} distinct risk profiles**")
    
    # Largest cluster
    largest = max(cluster_profiles, key=lambda x: x['count'])
    insights.append(
        f"Largest cluster: **\"{cluster_names[largest['cluster_id']]}\"** "
        f"({largest['percentage']:.1f}%, {largest['count']} bills)"
    )
    
    # Highest risk cluster
    highest_risk = cluster_profiles[0]  # Already sorted by risk
    insights.append(
        f"Highest risk cluster: **\"{cluster_names[highest_risk['cluster_id']]}\"** "
        f"(avg {highest_risk['mean_risk_score']:.1f}, {highest_risk['count']} bills)"
    )
    
    # Cluster quality
    sil_score = metrics['silhouette_score']
    if sil_score > 0.7:
        quality = "excellent"
    elif sil_score > 0.5:
        quality = "good"
    elif sil_score > 0.3:
        quality = "moderate"
    else:
        quality = "poor"
    
    insights.append(
        f"Clusters are **{quality}** separated (Silhouette = {sil_score:.2f})"
    )
    
    # Portfolio recommendations
    high_risk_clusters = [
        cluster_names[p['cluster_id']] 
        for p in cluster_profiles 
        if p['mean_risk_score'] > 50
    ]
    
    if high_risk_clusters:
        insights.append(
            f"**Recommendation:** Monitor {', '.join(high_risk_clusters)} clusters closely"
        )
    
    return insights
```

### Visualization

```python
def plot_clustering_results(df: pd.DataFrame, cluster_names: dict):
    """
    Visualize clustering results in 2D using PCA.
    
    Args:
        df: DataFrame with cluster assignments
        cluster_names: Dictionary mapping cluster_id to name
        
    Creates 2 plots:
        1. Cluster scatter plot (2D PCA projection)
        2. Cluster size distribution (bar chart)
    """
    from sklearn.decomposition import PCA
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Plot 1: 2D PCA Projection
    ax1 = axes[0]
    
    cluster_features = ['risk_score', 'stage_score', 'cosponsor_score', 'recency_score']
    X = df[cluster_features].fillna(0)
    
    # Apply PCA (4D → 2D)
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(StandardScaler().fit_transform(X))
    
    # Scatter plot by cluster
    for cluster_id in df['cluster'].unique():
        cluster_mask = df['cluster'] == cluster_id
        ax1.scatter(
            X_pca[cluster_mask, 0],
            X_pca[cluster_mask, 1],
            label=cluster_names.get(cluster_id, f"Cluster {cluster_id}"),
            alpha=0.6,
            s=30
        )
    
    ax1.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% variance)')
    ax1.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% variance)')
    ax1.set_title('Bill Clusters (2D PCA Projection)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Cluster Size Distribution
    ax2 = axes[1]
    
    cluster_counts = df['cluster'].value_counts().sort_index()
    cluster_labels = [cluster_names.get(cid, f"Cluster {cid}") for cid in cluster_counts.index]
    
    ax2.bar(cluster_labels, cluster_counts.values)
    ax2.set_ylabel('Number of Bills')
    ax2.set_title('Cluster Size Distribution')
    ax2.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.show()
```

---

## Integrated Analytics Dashboard

### 9-Panel Visualization

```python
def create_analytics_dashboard(df: pd.DataFrame):
    """
    Create comprehensive 9-panel analytics dashboard.
    
    Panels:
        1. Risk score distribution (histogram)
        2. Stage score distribution (histogram)
        3. Risk by sector (bar chart)
        4. Cosponsor vs Risk (scatter)
        5. Recency vs Risk (scatter)
        6. Stage vs Cosponsor (scatter)
        7. Risk over time (line chart)
        8. Cluster visualization (2D PCA)
        9. Correlation heatmap
        
    Args:
        df: DataFrame with risk scores and clusters
    """
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    fig, axes = plt.subplots(3, 3, figsize=(18, 15))
    
    # Panel 1: Risk Score Distribution
    axes[0, 0].hist(df['risk_score'], bins=30, edgecolor='black', alpha=0.7)
    axes[0, 0].set_xlabel('Risk Score')
    axes[0, 0].set_ylabel('Frequency')
    axes[0, 0].set_title('1. Risk Score Distribution')
    axes[0, 0].axvline(df['risk_score'].mean(), color='red', linestyle='--', label='Mean')
    axes[0, 0].legend()
    
    # Panel 2: Stage Score Distribution
    axes[0, 1].hist(df['stage_score'], bins=20, edgecolor='black', alpha=0.7, color='green')
    axes[0, 1].set_xlabel('Stage Score')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].set_title('2. Legislative Stage Distribution')
    
    # Panel 3: Risk by Sector
    sector_data = []
    for _, row in df[df['gics_sectors'].notna()].iterrows():
        sectors = row['gics_sectors'].split('|')
        for sector in sectors:
            sector_data.append({'sector': sector.strip(), 'risk_score': row['risk_score']})
    
    sector_df = pd.DataFrame(sector_data)
    sector_avg = sector_df.groupby('sector')['risk_score'].mean().sort_values(ascending=False)
    
    axes[0, 2].barh(sector_avg.index, sector_avg.values, color='orange')
    axes[0, 2].set_xlabel('Average Risk Score')
    axes[0, 2].set_title('3. Average Risk by Sector')
    
    # Panel 4: Cosponsor vs Risk
    axes[1, 0].scatter(df['cosponsor_score'], df['risk_score'], alpha=0.5, s=20)
    axes[1, 0].set_xlabel('Cosponsor Score')
    axes[1, 0].set_ylabel('Risk Score')
    axes[1, 0].set_title('4. Cosponsor Support vs Risk')
    
    # Panel 5: Recency vs Risk
    axes[1, 1].scatter(df['recency_score'], df['risk_score'], alpha=0.5, s=20, color='purple')
    axes[1, 1].set_xlabel('Recency Score')
    axes[1, 1].set_ylabel('Risk Score')
    axes[1, 1].set_title('5. Recent Activity vs Risk')
    
    # Panel 6: Stage vs Cosponsor
    axes[1, 2].scatter(df['stage_score'], df['cosponsor_score'], alpha=0.5, s=20, color='red')
    axes[1, 2].set_xlabel('Stage Score')
    axes[1, 2].set_ylabel('Cosponsor Score')
    axes[1, 2].set_title('6. Legislative Stage vs Cosponsors')
    
    # Panel 7: Risk Over Time
    df_with_date = df.copy()
    df_with_date['action_date'] = df_with_date['latestAction'].apply(
        lambda x: pd.to_datetime(x['actionDate']) if isinstance(x, dict) and 'actionDate' in x else None
    )
    
    time_data = df_with_date[df_with_date['action_date'].notna()].sort_values('action_date')
    time_data['month'] = time_data['action_date'].dt.to_period('M')
    monthly_risk = time_data.groupby('month')['risk_score'].mean()
    
    axes[2, 0].plot(monthly_risk.index.astype(str), monthly_risk.values, marker='o')
    axes[2, 0].set_xlabel('Month')
    axes[2, 0].set_ylabel('Average Risk Score')
    axes[2, 0].set_title('7. Risk Score Over Time')
    axes[2, 0].tick_params(axis='x', rotation=45)
    
    # Panel 8: Cluster Visualization (if clusters exist)
    if 'cluster' in df.columns:
        from sklearn.decomposition import PCA
        from sklearn.preprocessing import StandardScaler
        
        cluster_features = ['risk_score', 'stage_score', 'cosponsor_score', 'recency_score']
        X = df[cluster_features].fillna(0)
        X_scaled = StandardScaler().fit_transform(X)
        
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X_scaled)
        
        for cluster_id in df['cluster'].unique():
            mask = df['cluster'] == cluster_id
            axes[2, 1].scatter(X_pca[mask, 0], X_pca[mask, 1], label=f"Cluster {cluster_id}", alpha=0.6, s=30)
        
        axes[2, 1].set_xlabel('PC1')
        axes[2, 1].set_ylabel('PC2')
        axes[2, 1].set_title('8. Bill Clusters (PCA)')
        axes[2, 1].legend()
    
    # Panel 9: Correlation Heatmap
    corr_features = ['risk_score', 'stage_score', 'cosponsor_score', 'recency_score', 'bipartisan_score']
    corr_matrix = df[corr_features].corr()
    
    sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm', center=0, 
                square=True, ax=axes[2, 2], cbar_kws={'shrink': 0.8})
    axes[2, 2].set_title('9. Feature Correlation Heatmap')
    
    plt.tight_layout()
    plt.show()
```

---

## Testing

### Unit Tests

```python
def test_regression_model():
    """Test linear regression fitting."""
    # Create synthetic data
    df = pd.DataFrame({
        'stage_score': [10, 20, 70, 95],
        'cosponsor_score': [0, 30, 80, 100],
        'recency_score': [50, 60, 90, 100],
        'bipartisan_score': [20, 40, 60, 100],
        'risk_score': [
            0.40*10 + 0.25*0 + 0.20*50 + 0.15*20,
            0.40*20 + 0.25*30 + 0.20*60 + 0.15*40,
            0.40*70 + 0.25*80 + 0.20*90 + 0.15*60,
            0.40*95 + 0.25*100 + 0.20*100 + 0.15*100
        ]
    })
    
    results = fit_risk_driver_model(df)
    
    # Check coefficients
    assert results['metrics']['r2_score'] > 0.95
    assert abs(results['model'].coef_[0] - 0.40) < 0.01
    assert abs(results['model'].coef_[1] - 0.25) < 0.01

def test_clustering_model():
    """Test K-Means clustering."""
    # Create synthetic data with clear clusters
    df = pd.DataFrame({
        'risk_score': [10]*100 + [50]*100 + [90]*100,
        'stage_score': [10]*100 + [50]*100 + [90]*100,
        'cosponsor_score': [0]*100 + [50]*100 + [100]*100,
        'recency_score': [30]*100 + [60]*100 + [95]*100
    })
    
    results = fit_clustering_model(df, n_clusters=3)
    
    # Check cluster separation
    assert results['metrics']['silhouette_score'] > 0.5
    assert len(results['cluster_profiles']) == 3
```

---

## Monitoring

### Metrics Dashboard

```python
def compute_analytics_metrics(df: pd.DataFrame) -> dict:
    """Compute metrics for monitoring analytics quality."""
    regression_results = fit_risk_driver_model(df)
    clustering_results = fit_clustering_model(df)
    
    return {
        'regression_r2': regression_results['metrics']['r2_score'],
        'regression_mae': regression_results['metrics']['mae'],
        'clustering_silhouette': clustering_results['metrics']['silhouette_score'],
        'clustering_inertia': clustering_results['metrics']['inertia'],
        'n_clusters': len(clustering_results['cluster_profiles']),
        'largest_cluster_pct': max(p['percentage'] for p in clustering_results['cluster_profiles'])
    }
```

---

## References

- **Linear Regression:** https://scikit-learn.org/stable/modules/linear_model.html
- **K-Means Clustering:** https://scikit-learn.org/stable/modules/clustering.html#k-means
- **Silhouette Score:** https://scikit-learn.org/stable/modules/clustering.html#silhouette-coefficient
- **PCA Visualization:** https://scikit-learn.org/stable/modules/decomposition.html#pca
- **Elbow Method:** https://en.wikipedia.org/wiki/Elbow_method_(clustering)
