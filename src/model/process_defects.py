import pandas as pd
from collections import Counter
from datetime import datetime


def process_defects_file(input_path, output_path):

    df = pd.read_csv(input_path)

    analysis_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    total_rows = len(df)
    normal_count = len(df[df['defect'] == 'Normal'])
    normal_percentage = (normal_count / total_rows) * 100 if total_rows > 0 else 0

    if normal_percentage > 90:
        summary_defect = 'Normal'
        summary_severity = '-'
        unique_defects = df['defect'].unique()
        if len(unique_defects) > 1:
            additional_note = 'Предположительно есть другие дефекты, необходима экспертная оценка'
        else:
            additional_note = '-'
    else:
        non_normal_df = df[df['defect'] != 'Normal']
        if not non_normal_df.empty:
            non_normal_df['defect_severity'] = (
                    non_normal_df['defect'].astype(str) + '_' + non_normal_df['severity'].astype(str)
            )
            defect_severity_counts = Counter(non_normal_df['defect_severity'])
            max_count = max(defect_severity_counts.values())
            most_frequent = [combo for combo, count in defect_severity_counts.items() if count == max_count]
            severity_priority = {'High': 3, 'Medium': 2, 'Low': 1}
            if len(most_frequent) > 1:
                most_frequent.sort(key=lambda x: severity_priority.get(x.split('_')[1], 0), reverse=True)
            summary_combo = most_frequent[0]
            summary_defect, summary_severity = summary_combo.split('_')
        else:
            summary_defect = 'Unknown'
            summary_severity = 'Unknown'

        unique_defects = non_normal_df['defect'].unique()
        if len(unique_defects) > 1:
            additional_note = 'Предположительно есть другие дефекты, необходима экспертная оценка'
        else:
            additional_note = '-'

    defect_map = {
        'Outer Race': 'Дефект внешнего кольца',
        'Inner Race': 'Дефект внутреннего кольца',
        'Ball': 'Дефект тел качения',
        'Cage': 'Дефект сепаратора',
        'Misalignment': 'Дисбаланс',
        'Rotor': 'Дефект ротора',
        'Normal': 'Нормальное состояние',
        'Unknown': 'Неизвестно'
    }

    severity_map = {
        'Low': 'отклонения незначительны',
        'Medium': 'отклонения свыше нормы, необходим анализ',
        'High': 'отклонения значительны, возможен дефект',
        '-': '-',
        'Unknown': 'Неизвестно'
    }

    summary_defect_ru = defect_map.get(summary_defect, summary_defect)
    summary_severity_ru = severity_map.get(summary_severity, summary_severity)
    
    df['summary_defect'] = summary_defect_ru
    df['summary_severity'] = summary_severity_ru
    df['additional_note'] = additional_note
    df['analysis_time'] = analysis_time

    df.to_csv(output_path, index=False)

    return {
        'summary_defect': summary_defect_ru,
        'summary_severity': summary_severity_ru,
        'additional_note': additional_note,
        'analysis_time': analysis_time
    }