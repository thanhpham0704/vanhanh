import streamlit as st
import requests
import pandas as pd
from pathlib import Path
import pickle
import streamlit_authenticator as stauth
from datetime import timedelta
import numpy as np

page_title = "Ca học và thời khoá biểu "
page_icon = "🗓️"

layout = "wide"
st.set_page_config(page_title=page_title,
                   page_icon=page_icon, layout=layout)
# ------------------------------------------
try:
    authentication_status = st.session_state['authentication_status']
    authenticator = st.session_state['authenticator']
except KeyError:
    authentication_status = None

if authentication_status == False:
    st.error("Username/password is incorrect")

if authentication_status == None:
    st.warning("Please enter your username and password on the Homepage")

if authentication_status:
    authenticator.logout("logout", "main")

    # Add CSS styling to position the button on the top right corner of the page
    st.markdown(
        """
            <style>
            .stButton button {
                position: absolute;
                top: 0px;
                right: 10px;
            }
            </style>
            """,
        unsafe_allow_html=True
    )
    st.title(page_title + " " + page_icon)
    "---"
    @st.cache_data(ttl=timedelta(days=0.25))
    def collect_data(link):
        return (pd.DataFrame((requests.get(link).json())))

    @st.cache_data(ttl=timedelta(days=0.25))
    def rename_lop(dataframe, column_name):
        dataframe[column_name] = dataframe[column_name].replace(
            {1: "Hoa Cúc", 2: "Gò Dầu", 3: "Lê Quang Định", 5: "Lê Hồng Phong"})
        return dataframe

    @st.cache_data(ttl=timedelta(days=0.25))
    def collect_filtered_data(table, date_column='', start_time='', end_time=''):
        link = f"https://vietop.tech/api/get_data/{table}?column={date_column}&date_start={start_time}&date_end={end_time}"
        df = pd.DataFrame((requests.get(link).json()))
        df[date_column] = pd.to_datetime(df[date_column])
        # Extract date portion from datetime values
        df[date_column] = df[date_column].dt.date
        return df

    # ------------------------------------------------------------ Tiền giờ của lớp
    lophoc_schedules = collect_data(
        'https://vietop.tech/api/get_data/lophoc_schedules')
    lophoc_schedules = lophoc_schedules[[
        'lop_id', 'teacher_id', 'active']].drop_duplicates("lop_id")
    khoahoc = collect_data('https://vietop.tech/api/get_data/khoahoc')
    khoahoc_me = khoahoc.query("kh_parent_id == 0 and kh_active == 1")
    lophoc = collect_data(
        'https://vietop.tech/api/get_data/lophoc').query("deleted_at.isnull()")
    molop = collect_data('https://vietop.tech/api/get_data/molop')
    hocvien = collect_data('https://vietop.tech/api/get_data/hocvien')
    users = collect_data('https://vietop.tech/api/get_data/users')
    # Filter date
    # orders = collect_filtered_data(table='orders', date_column='created_at',
    #                                 start_time=ketoan_start_time, end_time=ketoan_end_time)
    orders = collect_data('https://vietop.tech/api/get_data/orders')
    # Merge lophoc and molop
    molop_orders = pd.merge(
        lophoc, molop[['lop_id', 'ketoan_id', 'molop_active']], on='lop_id', how='inner')
    # Merge orders
    molop_orders_lophoc = pd.merge(
        orders, molop_orders, on='ketoan_id', how='inner')
    # Query molop active
    final = molop_orders_lophoc.query('molop_active == 1')
    # Group by lop_id
    tiengiolop = final.groupby(["lop_id"], as_index=False).agg(
        {'ketoan_id': 'count', 'ketoan_tientrengio': 'sum'})
    # Merge back
    tiengiolop = tiengiolop.merge(molop_orders_lophoc, on='lop_id', how='left')
    tiengiolop = tiengiolop.drop_duplicates(subset='lop_id')
    # merge khoahoc
    tiengiolop = tiengiolop.merge(
        khoahoc, left_on='kh_id_x', right_on='kh_id', how='left')
    # Filter
    tiengiolop = tiengiolop.loc[:, ['created_at_x', 'lop_cahoc', 'kh_ten', 'lop_cn', 'lop_id', 'lop_ten', 'lop_thoigianhoc',
                                    'lop_type', 'lop_status', 'ketoan_id_x', 'ketoan_tientrengio_x']]
    tiengiolop = tiengiolop.merge(lophoc_schedules, on='lop_id')

    # Merge users
    tiengiolop = tiengiolop.merge(
        users[['id', 'fullname']], left_on='teacher_id', right_on='id')
    tiengiolop = tiengiolop.loc[:, ~
                                tiengiolop.columns.isin(['id', 'teacher_id'])]

    # Mapping
    tiengiolop = rename_lop(tiengiolop, "lop_cn")
    # Drop used columns
    tiengiolop.drop(['active', 'ketoan_id_x'], axis=1, inplace=True)
    tiengiolop = tiengiolop[['lop_id', 'lop_cn', 'fullname',
                             'kh_ten', 'lop_ten', 'ketoan_tientrengio_x', 'created_at_x']]
    lop_danghoc = lophoc[lophoc['lop_status'].isin([2, 4])]
    # Create lophoc_khoahoc
    lophoc_khoahoc = lop_danghoc.merge(
        khoahoc_me[['kh_id', 'kh_ten']], left_on='kh_parent', right_on='kh_id')
    df = lophoc_khoahoc[['lop_id', 'lop_cn', 'lop_cahoc', 'lop_thoigianhoc',
                         'kh_ten', 'class_type',]].sort_values('lop_id', ascending=True)
    # Create kh_ten_group from kh_ten
    df['kh_ten_group'] = [
        'Lớp Kèm' if "Kèm" in i else 'Lớp Nhóm' if 'Nhóm' in i else i for i in df['kh_ten']]
    df1 = df.merge(tiengiolop, on='lop_id')
    # ------------------------------------------------------------ Filter
    # Create a form to filter coso
    with st.sidebar.form(key='coso_filter_form'):
        coso_filter = st.multiselect(label="Select cơ sở:",
                                     options=list(df1['lop_cn_y'].unique()), default=['Hoa Cúc', 'Gò Dầu', 'Lê Hồng Phong', 'Lê Quang Định'])
        submit_button = st.form_submit_button(
            label='Filter',  use_container_width=True)
    df1 = df1[df1['lop_cn_y'].isin(coso_filter)]
    # ------------------------------------------------------------ Final

    df2 = df1.groupby(['kh_ten_group', 'lop_cahoc',
                      'class_type'], as_index=False).size()
    df2_1 = df1.groupby(['kh_ten_group', 'lop_cahoc', 'class_type'],
                        as_index=False).ketoan_tientrengio_x.mean()
    df2_1['ketoan_tientrengio_x'] = round(df2_1['ketoan_tientrengio_x'], 2)
    df2_2 = df1.groupby(['kh_ten_group', 'lop_thoigianhoc',
                        'class_type'], as_index=False).size()
    df2_2 = df2_2[df2_2['lop_thoigianhoc'].isin(
        ['["2","4","6"]', '["3","5","7"]', '["7","8"]', '["7"]'])]
    df2_3 = df1.groupby(['kh_ten_group', 'class_type'],
                        as_index=False).ketoan_tientrengio_x.mean()
    # df2 = grand_total(df1, 'lop_cn')
    # Create a pivot table
    df3 = pd.pivot_table(df2, index=['kh_ten_group', 'class_type'],
                         columns='lop_cahoc', values='size', fill_value=0,
                         margins=True, margins_name='Total count', aggfunc='sum').reset_index()
    st.subheader("Số lớp theo ca học và loại lớp")
    st.dataframe(df3.style.background_gradient(
        cmap='YlOrRd', axis=1, subset=[1, 2, 3, 4, 5, 6]))
    # Create a pivot table
    df5 = pd.pivot_table(df2_2, index=['kh_ten_group', 'class_type'],
                         columns='lop_thoigianhoc', values='size', fill_value=0,
                         margins=True, margins_name='Total count', aggfunc='sum').reset_index()
    st.subheader("Số lớp theo thời khoá biểu và loại lớp")
    st.dataframe(df5.style.background_gradient(cmap='YlOrRd', axis=1, subset=[
                 '["2","4","6"]', '["3","5","7"]', '["7","8"]', '["7"]']))
    # Create a pivot table
    df4 = pd.pivot_table(df2_1, index=['kh_ten_group', 'class_type'],
                         columns='lop_cahoc', values='ketoan_tientrengio_x', fill_value=0,
                         margins=True, margins_name='Total mean', aggfunc='mean').reset_index()

    df4 = df4.style.background_gradient(
        cmap='YlOrRd', axis=1, subset=[1, 2, 3, 4, 5, 6])
    st.subheader("Trung bình tiền của lớp theo ca học và loại lớp")
    st.dataframe(df4.format({1: '{:,.0f}', 2: '{:,.0f}', 3: '{:,.0f}',
                 4: '{:,.0f}', 5: '{:,.0f}', 6: '{:,.0f}', 'Total mean': '{:,.0f}'}))
    st.subheader("Trung bình tiền của lớp theo loại lớp")
    df2_3 = df2_3.style.background_gradient(cmap='YlOrRd', axis=0)
    st.dataframe(df2_3.format({'ketoan_tientrengio_x': '{:,.0f}'}))

    st.subheader("Chi tiết")
    st.dataframe(df1.drop(['lop_cn_x'], axis=1))
    # Change columns name
    # tiengiolop.columns = ['Ngày mở lớp', 'ca học', 'tên khoá học', 'chi nhánh', 'lớp id',
    #                         'tên lớp', 'lop_thoigianhoc', 'loại lớp', 'online/offline', 'ketoan_id_x', 'tiền giờ', 'active', 'giao_vien']

    import io
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Write each dataframe to a different worksheet.
        df1.to_excel(writer, sheet_name='Sheet1')
        # Close the Pandas Excel writer and output the Excel file to the buffer
        writer.save()
        st.download_button(
            label="Download chi tiết ca học và thời khoá biểu worksheets",
            data=buffer,
            file_name="cahoc_thoikhoabieu.xlsx",
            mime="application/vnd.ms-excel"
        )
