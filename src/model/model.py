import numpy as np
import data_transform as dt
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_absolute_error
from catboost import CatBoostClassifier, CatBoostRegressor
from visualise_reports.data_visualiser import plot_training_history

FEATURE_DATA_DIR = "feature_data"

df = dt.data_concat(FEATURE_DATA_DIR)
X, y_defect, y_severity = dt.get_X_y_defect_y_severity(df)

# df.to_csv(r'C:\Users\Andrey\Desktop\df.csv', index=False)
# pd.DataFrame(X).to_csv(r'C:\Users\Andrey\Desktop\X.csv', index=False)
# pd.DataFrame(y).to_csv(r'C:\Users\Andrey\Desktop\y.csv', index=False)


X_train, X_test, y_defect_train, y_defect_test, y_severity_train, y_severity_test = train_test_split(
    X, y_defect, y_severity, 
    test_size=0.2, 
    random_state=42
)
X_train, X_val, y_defect_train, y_defect_val, y_severity_train, y_severity_val = train_test_split(
    X_train, y_defect_train, y_severity_train,
    test_size=0.1, 
    random_state=42
)
print(f"X_train: {X_train.shape}, X_val: {X_val.shape}, X_test: {X_test.shape}")
print(f"y_defect_train: {y_defect_train.shape}, y_defect_val: {y_defect_val.shape}, y_defect_test: {y_defect_test.shape}")
print(f"y_severity_train: {y_severity_train.shape}, y_severity_val: {y_severity_val.shape}, y_severity_test: {y_severity_test.shape}")

    
# Обучение модели для defect type (multiclass classification)
model_defect = CatBoostClassifier(
        iterations=200,  
        depth=6,
        learning_rate=0.1,
        loss_function='MultiClass',
        random_seed=42,
        verbose=True
    )

# Обучение с сохранением истории
history_defect = model_defect.fit(
    X_train, y_defect_train, 
    eval_set=(X_val, y_defect_val),
)

# Построение графиков обучения
plot_training_history(history_defect.get_evals_result(), 'Defect Type Classification', 'MultiClass')

# Обучение модели для severity (ordinal regression как регрессия)
model_severity = CatBoostRegressor(
        iterations=226,
        depth=6,
        learning_rate=0.1,
        loss_function='RMSE',  # Или MAE для ordinal
        random_seed=42,
        verbose=True
    )
history_severity = model_severity.fit(
    X_train, y_severity_train, 
    eval_set=(X_val, y_severity_val),
    )

# Построение графиков обучения
plot_training_history(history_severity.get_evals_result(), 'Severity Regression', 'RMSE')    

# Предсказания и оценка
y_defect_pred = model_defect.predict(X_test)
y_severity_pred = model_severity.predict(X_test)
    
# Для severity, поскольку ordinal, округляем до ближайшего int
y_severity_pred_rounded = np.round(y_severity_pred).astype(int)
    
defect_acc = accuracy_score(y_defect_test, y_defect_pred)
severity_mae = mean_absolute_error(y_severity_test, y_severity_pred_rounded)
print(f"Defect accuracy: {defect_acc}")
print(f"Severity MAE: {severity_mae}")    

# Опционально: сохранение моделей
model_defect.save_model('src\model\model_defect.cbm')
model_severity.save_model('src\model\model_severity.cbm')
