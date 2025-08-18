import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def data_visualize(df: pd.DataFrame, n_points: int = 2000):
    """
    Визуализирует токи трёх фаз из CSV-файла.
    
    Аргументы:
    df: датафрейм с данными
    n_points: сколько отсчётов отобразить (по умолчанию: 2000)
    """

    # Извлекаем первые n_points точек
    sample = df.iloc[:n_points]

    # Построение графика
    plt.figure(figsize=(14, 5))
    
    # Добавляем идеальную синусоиду для сравнения
    # Частота дискретизации 25.6 кГц
    sampling_frequency = 25600  # Гц
    sampling_period = 1 / sampling_frequency  # секунды
    
    # Генерируем временной массив для всех отсчетов
    time = np.arange(n_points) * sampling_period
    
    # Идеальная синусоида с частотой 50 Гц
    frequency = 50  # Гц (стандартная частота электрической сети)
    ideal_sine = np.sin(2 * np.pi * frequency * time)
    plt.plot(sample.index, ideal_sine, label='Идеальная синусоида', color='black', linestyle='--', alpha=0.5)
    
    plt.plot(sample['current_R'], label='Фаза R', alpha=0.7)
    plt.plot(sample['current_S'], label='Фаза S', alpha=0.7)
    plt.plot(sample['current_T'], label='Фаза T', alpha=0.7)
    
    plt.title('График токов трёх фаз')
    plt.xlabel('Отсчёты')
    plt.ylabel('Ток в А')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()


def data_visualize_combined(df: pd.DataFrame, n_points: int = 2000):

    df = df.mean(axis=1)
    sample = df.iloc[:n_points]

    plt.figure(figsize=(14, 5))
    
    sampling_frequency = 25600  # Гц
    sampling_period = 1 / sampling_frequency  # секунды
    time = np.arange(n_points) * sampling_period
    frequency = 50  # Гц (стандартная частота электрической сети)
    ideal_sine = np.sin(2 * np.pi * frequency * time)

    plt.plot(sample.index, ideal_sine, label='Идеальная синусоида', color='black', linestyle='--', alpha=0.5)
    plt.plot(sample, label='Ток объединенной фазы', alpha=0.7)

    plt.title('График объединенной фазы')
    plt.xlabel('Отсчёты')
    plt.ylabel('Ток в А')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()


def plot_training_history(history: dict, title: str, metric_name: str) -> None:

    plt.figure(figsize=(12, 5))
    
    # Print available keys for debugging
    # print("Available keys in history:", history.keys())
    
    # Plot training metric
    if 'learn' in history and metric_name in history['learn']:
        plt.plot(history['learn'][metric_name], label='Train')
    
    # Plot validation metric
    if 'validation' in history and metric_name in history['validation']:
        plt.plot(history['validation'][metric_name], label='Validation')
    
    plt.title(f'{title} - Training History')
    plt.xlabel('Iterations')
    plt.ylabel(metric_name)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()  # Display the plot
