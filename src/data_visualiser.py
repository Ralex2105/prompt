import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from preprocessing import dq_transform

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
    

def data_visualize_dq(df: pd.DataFrame, n_points: int = 2000):
    """
    Визуализирует токи в dq системе.
    
    Аргументы:
    df: датафрейм с данными
    n_points: количество отсчётов для отображения
    """
    sample = df.iloc[:n_points]
    sample = dq_transform(sample)
    
    # Создаем два графика: временной и полярный
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 6))

    # Временной график
    ax1.plot(sample.index, sample['i_d'], label='i_d', alpha=0.7)
    ax1.plot(sample.index, sample['i_q'], label='i_q', alpha=0.7)
    ax1.set_title('График i_d и i_q')
    ax1.set_xlabel('Отсчёты')
    ax1.set_ylabel('Ток в dq системе')
    ax1.legend()
    ax1.grid(True)

    # Полярный график
    ax2 = plt.subplot(122, polar=True)
    
    # Вычисляем амплитуду и фазу для каждого момента времени
    magnitude = np.sqrt(sample['i_d']**2 + sample['i_q']**2)
    angle = np.arctan2(sample['i_q'], sample['i_d'])
    
    # Строим векторы
    ax2.plot(angle, magnitude, label='Вектор Парка', alpha=0.7)
    
    # Добавляем сетку и метки
    ax2.set_rticks([0.5, 1, 1.5, 2])  # r labels
    ax2.set_rlabel_position(-22.5)  # get radial labels away from plotted line
    ax2.grid(True)
    
    ax2.set_title('Векторы Парка в полярной системе')
    ax2.legend()
    
    plt.tight_layout()