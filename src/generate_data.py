import pandas as pd
import numpy as np
import os

def generate_sensor_data(num_samples=2000):
    np.random.seed(42)
    
    # 80% Normal data, 20% Failure data
    num_normal = int(num_samples * 0.8)
    num_failure = num_samples - num_normal
    
    # Generate Normal Data
    # Normal Temp: 30 to 60 C
    normal_temp = np.random.normal(45, 5, num_normal)
    # Normal Vibration: 1 to 4 mm/s
    normal_vib = np.random.normal(2.5, 0.5, num_normal)
    # Normal Current: 10 to 18 A
    normal_curr = np.random.normal(14, 2, num_normal)
    
    # Generate Failure Data (Simulating overheating, high vibration, power spikes)
    # Failure Temp: 65 to 90 C
    failure_temp = np.random.normal(78, 6, num_failure)
    # Failure Vibration: 5 to 10 mm/s
    failure_vib = np.random.normal(7.5, 1.5, num_failure)
    # Failure Current: 20 to 35 A
    failure_curr = np.random.normal(27, 3, num_failure)
    
    # Combine datasets
    temperatures = np.concatenate([normal_temp, failure_temp])
    vibrations = np.concatenate([normal_vib, failure_vib])
    currents = np.concatenate([normal_curr, failure_curr])
    
    # Labels: 0 = Normal, 1 = Failure
    labels = np.concatenate([np.zeros(num_normal), np.ones(num_failure)])
    
    # Create DataFrame
    df = pd.DataFrame({
        'temperature': temperatures,
        'vibration': vibrations,
        'current': currents,
        'failure': labels
    })
    
    # Shuffle the dataset
    df = df.sample(frac=1).reset_index(drop=True)
    
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    filepath = 'data/iot_sensor_data.csv'
    df.to_csv(filepath, index=False)
    print(f"Success: Generated {num_samples} samples and saved to {filepath}")

if __name__ == '__main__':
    generate_sensor_data()
