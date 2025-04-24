import streamlit as st
import pandas as pd
from io import BytesIO

st.title("📦 Сравнение остатков на складах")

# Загрузка файла
uploaded_file = st.file_uploader("Загрузите Excel-файл", type=["xlsx"])

if uploaded_file:
    data = pd.read_excel(uploaded_file, sheet_name=0)

    # Приводим все названия колонок к единому виду
    data.columns = [col.strip().lower() for col in data.columns]

    # Сопоставление названий для внутреннего использования
    column_mapping = {
        'item id': 'item id',
        'style code': 'style code',
        'color cod': 'color cod',
        'size': 'size desc',  # заменяем size на size desc
        'style desc': 'style desc',
        'line': 'line'
    }

    # Выбор признака для сравнения
    compare_options = {
        "Полный SKU (Item Id)": [column_mapping['item id']],
        "SKU без сезона (Style Code + Color Cod + Size)": [column_mapping['style code'], column_mapping['color cod'], column_mapping['size']],
        "Артикул + Цвет (Style Code + Color Cod)": [column_mapping['style code'], column_mapping['color cod']],
        "Только артикул (Style Code)": [column_mapping['style code']]
    }
    compare_by = st.selectbox("Сравнивать по:", list(compare_options.keys()))
    group_cols = compare_options[compare_by] + [column_mapping['style desc'], column_mapping['line']]

    # Выбор локаций
    loc_options = data['store desc'].unique()
    loc1 = st.selectbox("Выберите первую локацию:", loc_options)
    loc2 = st.selectbox("Выберите вторую локацию:", loc_options, index=1)

    if st.button("Сравнить"):
        def prepare_data(df, location):
            grouped = df[df['store desc'] == location].groupby(group_cols, as_index=False)['quantity'].sum()
            grouped = grouped.rename(columns={'quantity': f'Количество в {location}'})
            return grouped

        missing_columns = [col for col in group_cols if col not in data.columns]
        if missing_columns:
            st.error(f"В файле отсутствуют необходимые столбцы: {', '.join(missing_columns)}")
        else:
            df1 = prepare_data(data, loc1)
            df2 = prepare_data(data, loc2)

            result = pd.merge(df1, df2, on=group_cols, how='outer').fillna(0)
            result['Разница'] = result[f'Количество в {loc1}'] - result[f'Количество в {loc2}']

            def get_status(row):
                q1 = row[f'Количество в {loc1}']
                q2 = row[f'Количество в {loc2}']
                if q1 > 0 and q2 > 0:
                    return "Товар есть в каждой локации"
                elif q1 > 0:
                    return f"Товар есть только в локации {loc1}"
                elif q2 > 0:
                    return f"Товар есть только в локации {loc2}"
                else:
                    return "Нет в наличии"

            result['Статус'] = result.apply(get_status, axis=1)

            st.dataframe(result)

            @st.cache_data
            def convert_df(df):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                return output.getvalue()

            excel = convert_df(result)

            st.download_button(
                label="📥 Скачать отчет в Excel",
                data=excel,
                file_name=f"сравнение_{loc1}_и_{loc2}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
