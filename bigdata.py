import requests
import pandas as pd
import numpy as np
import time

#Target Location
LAT = 37.4095
LON = 141.0123
RADIUS = 3000   # 3 km radius
PAGES_TO_FETCH = 10  

def fetch_dense_data():
    all_data = []
    print(f"Mining data from Fukushima Exclusion Zone (Route 6)...")
    print(f"Target: {LAT}, {LON} | Radius: {RADIUS}m")

    for page in range(1, PAGES_TO_FETCH + 1):
        print(f"   ...Fetching Page {page} of {PAGES_TO_FETCH}...")
        
        url = "https://api.safecast.org/measurements.json"
        params = {
            'latitude': LAT,
            'longitude': LON,
            'distance': RADIUS,
            'format': 'json',
            'page': page  
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if not data:
                print("   [!] No more data on this page.")
                break
                
            all_data.extend(data)
            time.sleep(1) 
            
        except Exception as e:
            print(f"Error on page {page}: {e}")
            break
    
    print(f"Download complete. Total raw points: {len(all_data)}")
    return all_data

def process_to_grid(json_data):
    df = pd.DataFrame(json_data)
    
    if 'unit' in df.columns:
        df = df[df['unit'] == 'cpm']
    
    df['dose_rate'] = df['value'] / 334.0
    
    ref_lat = LAT
    ref_lon = LON
    
    df['y'] = (df['latitude'] - ref_lat) * 111000
    df['x'] = (df['longitude'] - ref_lon) * 111000 * np.cos(np.radians(ref_lat))
    
    final_df = df[['x', 'y', 'dose_rate']].copy()
    
    final_df = final_df[final_df['dose_rate'] > 0]
    final_df = final_df[final_df['dose_rate'] < 1000] 
    
    return final_df

if __name__ == "__main__":
    raw = fetch_dense_data()
    
    if raw:
        df = process_to_grid(raw)
        
        fname = "actual_fukushima_route6.csv"
        df.to_csv(fname, index=False)
        
        print("\n" + "="*50)
        print(f"SUCCESS!")
        print(f"Saved to: {fname}")
        print(f"Total Data Points: {len(df)}")
        print(f"Max Dose: {df['dose_rate'].max():.2f} µSv/hr")
        print(f"Avg Dose: {df['dose_rate'].mean():.2f} µSv/hr")
        
        if df['dose_rate'].max() > 0.5:
            print("RADIATION DETECTED!")
            print("This dataset contains actual hotspots suitable for validation.")
        print("="*50)
