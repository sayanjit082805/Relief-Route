"""
Prepare quality disaster data from labeled datasets.
Filters only actionable reports (infrastructure damage, injuries, evacuations, etc.)
"""

import pandas as pd
import os

# Labels that are actionable for disaster response
ACTIONABLE_LABELS = [
    'infrastructure_and_utilities_damage',
    'injured_or_dead_people', 
    'missing_trapped_or_found_people',
    'displaced_people_and_evacuations',
    'caution_and_advice',
    'other_useful_information'  # Often contains location-specific info
]

def load_and_filter_tsv(filepath, disaster_type, region):
    """Load TSV file and filter to actionable labels."""
    df = pd.read_csv(filepath, sep='\t')
    
    # Filter to actionable labels only
    df = df[df['label'].isin(ACTIONABLE_LABELS)]
    
    # Rename columns for consistency
    df = df.rename(columns={'tweet_text': 'text'})
    
    # Add metadata
    df['disaster_type'] = disaster_type
    df['region'] = region
    df['source'] = 'twitter'
    
    return df[['text', 'label', 'disaster_type', 'region', 'source']]

def main():
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    raw_dir = os.path.join(data_dir, 'raw')
    processed_dir = os.path.join(data_dir, 'processed')
    
    os.makedirs(processed_dir, exist_ok=True)
    
    datasets = []
    
    # Load Nepal Earthquake data
    nepal_path = os.path.join(raw_dir, '2015_Nepal_Earthquake_en_CF_labeled_data.tsv')
    if os.path.exists(nepal_path):
        nepal_df = load_and_filter_tsv(nepal_path, 'earthquake', 'Nepal')
        datasets.append(nepal_df)
        print(f"Nepal Earthquake: {len(nepal_df)} actionable reports")
    
    # Load India Floods data
    india_path = os.path.join(raw_dir, '2014_India_floods_CF_labeled_data.tsv')
    if os.path.exists(india_path):
        india_df = load_and_filter_tsv(india_path, 'flood', 'India')
        datasets.append(india_df)
        print(f"India Floods: {len(india_df)} actionable reports")
    
    if datasets:
        # Combine all datasets
        combined = pd.concat(datasets, ignore_index=True)
        
        # Save full actionable dataset
        output_path = os.path.join(processed_dir, 'disaster_reports.csv')
        combined.to_csv(output_path, index=False)
        print(f"\nTotal: {len(combined)} actionable reports saved to {output_path}")
        
        # Create a small sample for testing (50 rows)
        sample = combined.sample(n=min(50, len(combined)), random_state=42)
        sample_path = os.path.join(processed_dir, 'disaster_reports_sample.csv')
        sample.to_csv(sample_path, index=False)
        print(f"Sample: {len(sample)} reports saved to {sample_path}")
        
        # Show label distribution
        print("\nLabel distribution:")
        print(combined['label'].value_counts())
    else:
        print("No datasets found!")

if __name__ == '__main__':
    main()
