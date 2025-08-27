import numpy as np
from . import data_transform as dt
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score 
from catboost import CatBoostClassifier
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FEATURE_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'data_feature')
MODEL_DIR = os.path.join(PROJECT_ROOT, 'model')

df = dt.data_concat(FEATURE_DATA_DIR)
X, y_defect, y_severity = dt.get_X_y_defect_y_severity(df)


X_train, X_test, y_defect_train, y_defect_test, y_severity_train, y_severity_test = train_test_split(
    X, y_defect, y_severity,
    test_size=0.2,
    random_state=42, 
)
X_train, X_val, y_defect_train, y_defect_val, y_severity_train, y_severity_val = train_test_split(
    X_train, y_defect_train, y_severity_train,
    test_size=0.1, 
    random_state=42,    
)
print(f"X_train: {X_train.shape}, X_val: {X_val.shape}, X_test: {X_test.shape}")
print(f"y_defect_train: {y_defect_train.shape}, y_defect_val: {y_defect_val.shape}, y_defect_test: {y_defect_test.shape}")
print(f"y_severity_train: {y_severity_train.shape}, y_severity_val: {y_severity_val.shape}, y_severity_test: {y_severity_test.shape}")


model_defect = CatBoostClassifier(
        iterations=199,  
        depth=6,
        learning_rate=0.1,
        loss_function='MultiClass',
        random_seed=42,
        verbose=True
    )

history_defect = model_defect.fit(
    X_train, y_defect_train, 
    eval_set=(X_val, y_defect_val),
)

model_severity = CatBoostClassifier(
        iterations=182,
        depth=6,
        learning_rate=0.1,
        loss_function='MultiClass', 
        random_seed=42,
        verbose=True
    )
history_severity = model_severity.fit(
    X_train, y_severity_train, 
    eval_set=(X_val, y_severity_val),
    )

y_defect_pred = model_defect.predict(X_test)
y_severity_pred = model_severity.predict(X_test)
    
    
defect_acc = accuracy_score(y_defect_test, y_defect_pred)
severity_acc = accuracy_score(y_severity_test, y_severity_pred)
print(f"Defect accuracy: {defect_acc}")
print(f"Severity accuracy: {severity_acc}")    

model_defect.save_model(os.path.join(MODEL_DIR, 'model_defect.cbm'))
model_severity.save_model(os.path.join(MODEL_DIR, 'model_severity.cbm'))
