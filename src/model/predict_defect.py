import sys
import pandas as pd
import numpy as np
import joblib
from feature_classifier import get_feature_vector, analyze_signal
import matplotlib.pyplot as plt

if len(sys.argv) < 2:
    print("Usage: python predict_defect.py <data_file.csv>")
    sys.exit(1)

data = pd.read_csv(sys.argv[1])
data.columns = [c.strip().replace(" ", "_").replace(",", "") for c in data.columns]
required = ["Current_R", "Current_S", "Current_T"]
for col in required:
    if col not in data:
        data[col] = np.nan

# Заполняем NaN: если вся фаза NaN — нулями, иначе медианой
for col in required:
    if data[col].isnull().all():
        data[col] = 0.0
    else:
        data[col] = data[col].fillna(data[col].median())

current_R = data['Current_R'].values[:25600]
current_S = data['Current_S'].values[:25600]
current_T = data['Current_T'].values[:25600]

scaler = joblib.load("scaler.pkl")
clf = joblib.load("defect_classifier.pkl")
reg = joblib.load("severity_regressor.pkl")

X = get_feature_vector(current_R, current_S, current_T).reshape(1,-1)
X_scaled = scaler.transform(X)
predicted_type = clf.predict(X_scaled)[0]
predicted_sev_value = reg.predict(X_scaled)[0]

if predicted_type == "Normal":
    predicted_sev_label = "None"
else:
    sev_val = float(predicted_sev_value)
    if sev_val < 0.5:
        predicted_sev_label = "None"
    elif sev_val < 1.5:
        predicted_sev_label = "Low"
    elif sev_val < 2.5:
        predicted_sev_label = "Medium"
    else:
        predicted_sev_label = "High"

print(f"Predicted defect type: {predicted_type}")
print(f"Predicted severity: {predicted_sev_label}")

analysis = analyze_signal(current_R, current_S, current_T)
raw_freqs, raw_mag = analysis["raw_spectrum"]
env_freqs, env_mag = analysis["envelope_spectrum"]
def_freqs = analysis["defect_freqs"]
peak_amps = analysis["peak_amps"]

plt.figure(figsize=(6,4))
plt.plot(raw_freqs, 20*np.log10(raw_mag+1e-6))
plt.xlim(0, 500)
plt.xlabel('Frequency (Hz)')
plt.ylabel('Amplitude (dB)')
plt.title('FFT Spectrum')
plt.tight_layout()
plt.savefig('fft_spectrum.png')
plt.close()

plt.figure(figsize=(6,4))
plt.plot(env_freqs, 20*np.log10(env_mag+1e-6))
plt.xlim(0, 500)
plt.xlabel('Frequency (Hz)')
plt.ylabel('Amplitude (dB)')
plt.title('Envelope Spectrum')
for name, f in def_freqs.items():
    if f <= 500:
        plt.axvline(x=f, color='r', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig('envelope_spectrum.png')
plt.close()

plt.figure(figsize=(6,4))
labels = ['BPFI','BPFO','BSF','FTF']
amps = [peak_amps['BPFI'], peak_amps['BPFO'], peak_amps['BSF'], peak_amps['FTF']]
plt.bar(labels, amps, color=['g' if a==max(amps) else 'gray' for a in amps])
plt.ylabel('Amplitude')
plt.title('Defect Frequency Amplitudes')
plt.tight_layout()
plt.savefig('amplitude_bars.png')
plt.close()