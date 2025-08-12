import glob
import numpy as np
from joblib import Parallel, delayed
from feature_extraction import extract_features_from_file
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
import joblib

data_files = sorted(glob.glob("src/tests/processed_files/*.csv"))
all_features, all_types, all_sevs = [], [], []
for feats, types, sevs in Parallel(n_jobs=-1)(delayed(extract_features_from_file)(f) for f in data_files):
    if len(feats) > 0:
        all_features.append(feats)
        all_types.append(types)
        all_sevs.append(sevs)

X_features = np.vstack(all_features)
y_type = np.concatenate(all_types)
sev_map = {"None":0, "Low":1, "Medium":2, "High":3}
y_severity = np.array([sev_map.get(s,0) for s in np.concatenate(all_sevs)])

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_features)

X_train, X_test, y_train, y_test = train_test_split(X_scaled, y_type, test_size=0.2, random_state=42, stratify=y_type)

clf = RandomForestClassifier(n_estimators=200, max_depth=8, class_weight='balanced', n_jobs=-1, random_state=42)
print("CV accuracy:", cross_val_score(clf, X_train, y_train, cv=5).mean())
clf.fit(X_train, y_train)
print("Test accuracy:", clf.score(X_test, y_test))
print("Feature importance:", clf.feature_importances_)

reg = RandomForestRegressor(n_estimators=200, max_depth=8, n_jobs=-1, random_state=42)
reg.fit(X_train, [sev_map.get(s,0) for s in y_train])

joblib.dump(clf, "defect_classifier.pkl")
joblib.dump(reg, "severity_regressor.pkl")
joblib.dump(scaler, "scaler.pkl")
print("Models and scaler saved.")