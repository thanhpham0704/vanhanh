import streamlit as st
import requests
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta, date
from pathlib import Path
import pickle
import streamlit_authenticator as stauth
import numpy as np
import calendar


page_title = "Chi tiết thiếu điểm danh"
page_icon = "🎬"
layout = "wide"
st.set_page_config(page_title=page_title, page_icon=page_icon, layout=layout)
# ----------------------------------------
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
                right: 0px;
            }
            </style>
            """,
        unsafe_allow_html=True
    )
    st.title(page_title + " " + page_icon)
    # Define a function

    @st.cache_data(ttl=timedelta(days=1))
    def collect_data(link):
        return (pd.DataFrame((requests.get(link).json())))

    @st.cache_data(ttl=timedelta(days=1))
    def collect_filtered_data(table, date_column='', start_time='', end_time=''):
        link = f"https://vietop.tech/api/get_data/{table}?column={date_column}&date_start={start_time}&date_end={end_time}"
        df = pd.DataFrame((requests.get(link).json()))
        df[date_column] = pd.to_datetime(df[date_column])
        df[date_column] = df[date_column].dt.date
        return df

    @st.cache_data()
    def rename_lop(dataframe, column_name):
        dataframe[column_name] = dataframe[column_name].replace(
            {1: "Hoa Cúc", 2: "Gò Dầu", 3: "Lê Quang Định", 5: "Lê Hồng Phong"})
        return dataframe

    @st.cache_data()
    def grand_total(dataframe, column):
        # create a new row with the sum of each numerical column
        totals = dataframe.select_dtypes(include=[float, int]).sum()
        totals[column] = "Grand total"
        # append the new row to the dataframe
        dataframe = dataframe.append(totals, ignore_index=True)
        return dataframe

    lophoc = collect_data('https://vietop.tech/api/get_data/lophoc')
    lophoc_schedules = collect_data(
        'https://vietop.tech/api/get_data/lophoc_schedules')
    khoahoc = collect_data('https://vietop.tech/api/get_data/khoahoc')
    molop = collect_data('https://vietop.tech/api/get_data/molop')
    users = collect_data('https://vietop.tech/api/get_data/users')

    # Filter ------------------------------------------------
    now = datetime.now()
    DEFAULT_START_DATE = datetime(now.year, now.month, now.day)

    # Create a form to get the date range filters
    with st.sidebar.form(key='date_filter_form'):
        # col1, col2 = st.columns(2)
        ketoan_start_time = st.date_input(
            "Select date", value=DEFAULT_START_DATE)
        submit_button = st.form_submit_button(
            label='Filter',  use_container_width=True)
    # Collect diemdanh data based on the filter
    diemdanh = collect_filtered_data(
        table='diemdanh', date_column='date_created', start_time=ketoan_start_time, end_time=ketoan_start_time)
    # Get the weekday value from ketoan_start_time
    weekday_value = ketoan_start_time.weekday()
    mapping = {0: 2, 1: 3, 2: 4, 3: 5, 4: 6, 5: 7, 6: 8}
    weekday_value = mapping[weekday_value]
    # Filter lophoc_schedule based on the value of weekday
    lophoc_schedules_subset = lophoc_schedules\
        .query('weekday == @weekday_value')
    df = molop.query('molop_active ==1').drop_duplicates('lop_id')[['lop_id']]
    # Những lớp đang học và có lớp schedule
    df1 = df.merge(lophoc_schedules_subset, on='lop_id', how='inner')
    # display(df1.columns)
    df2 = diemdanh[['lop_id', 'date_created',
                    'cahoc', 'sogio', 'giaovien', 'auto_status']]
    # display(df2.columns)
    df3 = df1.merge(df2, left_on=['lop_id', 'class_period'], right_on=[
                    'lop_id', 'cahoc'], how='outer')
    df3.drop(['id', 'active'], axis=1, inplace=True)

    df4 = df3.merge(users[['id', 'fullname']], left_on='teacher_id', right_on='id', how='left')\
        .merge(users[['id', 'fullname']], left_on='giaovien', right_on='id', how='left')
    df5 = df4.merge(lophoc[['lop_id', 'kh_id', 'lop_cn']], on='lop_id', how='left')\
        .merge(khoahoc[['kh_id', 'kh_ten']], on='kh_id', how='left')
    df5 = df5.rename(columns={'fullname_x': 'gv_fullname_xepphong',
                     'fullname_y': 'gv_fullname_diemdanh', 'duration': 'sogio_xepphong', 'sogio': 'sogio_diemdanh'})
    df5.drop(['teacher_id', 'id_x', 'id_y', 'kh_id',
             'giaovien'], axis=1, inplace=True)
    # print(df5.columns)
    df6 = df5.reindex(columns=['room_id', 'lop_cn', 'lop_id', 'kh_ten', 'gv_fullname_xepphong', 'weekday', 'start_time',
                      'class_period', 'sogio_xepphong', 'auto_status', 'date_created', 'gv_fullname_diemdanh', 'cahoc', 'sogio_diemdanh',])
    df7 = rename_lop(df6, 'lop_cn')
    # df7.to_excel('/Users/phamtanthanh/Desktop/sosanh_diemdanh.xlsx', sheet_name='sosanh_diemdanh', engine="xlsxwriter", index=False)
    df8 = df7.query("date_created.isna()")
    st.subheader(
        f"Tổng lớp thiếu điểm danh trong ngày :blue[{ketoan_start_time}] là :blue[{df8.shape[0]} lớp]")
    st.dataframe(df8)

    import io
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Write each dataframe to a different worksheet.
        df8.to_excel(writer, sheet_name='Sheet1')
        # Close the Pandas Excel writer and output the Excel file to the buffer
        writer.save()
        st.download_button(
            label="Download danh sách thiếu điểm danh",
            data=buffer,
            file_name="diemdanh_missing.xlsx",
            mime="application/vnd.ms-excel"
        )
