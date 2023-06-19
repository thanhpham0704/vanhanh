import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import io
buffer = io.BytesIO()


page_title = "Đối chiếu điểm danh"
page_icon = "💁"
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
    st.markdown("---")
    # Define a function

    @st.cache_data(ttl=timedelta(seconds=60))
    def collect_data(link):
        return (pd.DataFrame((requests.get(link).json())))

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
                    'cahoc', 'sogio', 'giaovien', 'class_status', 'auto_status']]
    # display(df2.columns)
    df3 = df1.merge(df2, left_on=['lop_id', 'class_period'], right_on=[
                    'lop_id', 'cahoc'], how='outer')
    df3.drop(['id', 'active'], axis=1, inplace=True)

    df4 = df3.merge(users[['id', 'fullname']], left_on='teacher_id', right_on='id', how='left')\
        .merge(users[['id', 'fullname']], left_on='giaovien', right_on='id', how='left')
    df5 = df4.merge(lophoc[['lop_id', 'kh_id', 'lop_cn']], on='lop_id', how='left')\
        .merge(khoahoc[['kh_id', 'kh_ten']], on='kh_id', how='left')
    df5 = df5.rename(columns={'fullname_x': 'gv_fullname_xepphong',
                     'fullname_y': 'gv_fullname_diemdanh', 'duration': 'sogio_xepphong', 'sogio': 'sogio_diemdanh', 'class_period': 'cahoc_xepphong', 'cahoc': 'cahoc_diemdanh'})
    df5.drop(['teacher_id', 'id_x', 'id_y', 'kh_id',
             'giaovien'], axis=1, inplace=True)
    # print(df5.columns)
    df6 = df5.reindex(columns=['room_id', 'lop_id',  'lop_cn', 'kh_ten', 'gv_fullname_xepphong', 'weekday', 'start_time',
                      'cahoc_xepphong', 'sogio_xepphong', 'date_created', 'class_status', 'gv_fullname_diemdanh', 'cahoc_diemdanh', 'sogio_diemdanh',])

    df7 = rename_lop(df6, 'lop_cn')

    # Tổng lơp thiếu điểm danh
    st.markdown(
        f"Tổng lớp có :blue[xếp phòng] nhưng không có :blue[điểm danh] là :blue[{df7.query('date_created.isna()').shape[0]} lớp]")
    st.dataframe(df7.query("date_created.isnull()").reset_index(drop=True))
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Write each dataframe to a different worksheet.
        df7.query("date_created.isnull()").reset_index(
            drop=True).to_excel(writer, sheet_name='Sheet1')
        # Close the Pandas Excel writer and output the Excel file to the buffer
        writer.save()
        st.download_button(
            label="Download danh sách thiếu điểm danh",
            data=buffer,
            file_name="diemdanh_missing.xlsx",
            mime="application/vnd.ms-excel"
        )
    st.markdown("")
    # Tổng lớp thiếu xếp phòng
    st.markdown(
        f"Tổng lớp có :blue[điểm danh] nhưng không có :blue[xếp phòng] là là :blue[{df7.query('room_id.isna()').shape[0]} lớp]")
    st.dataframe(df7.query("room_id.isnull()").reset_index(drop=True))
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Write each dataframe to a different worksheet.
        df7.query("room_id.isnull()").reset_index(drop=True).query("date_created.isnull()").reset_index(
            drop=True).to_excel(writer, sheet_name='Sheet1')
        # Close the Pandas Excel writer and output the Excel file to the buffer
        writer.save()
        st.download_button(
            label="Download danh sách thiếu xếp phòng",
            data=buffer,
            file_name="xepphong_missing.xlsx",
            mime="application/vnd.ms-excel"
        )
    st.markdown("")
    # Filter room_id and date_created not null
    df8 = df7.query('room_id.notnull() and date_created.notnull()')
    # Tổng lớp đầy đủ điểm danh và xếp phòng
    st.markdown(
        f"Tổng lớp lớp có đầy đủ :blue[xếp phòng] và :blue[điểm danh] là :blue[{df8.query('room_id.notnull() and date_created.notnull()').shape[0]} lớp]")
    df8['check_status'] = ['wrong teacher' if i['gv_fullname_xepphong'] != i['gv_fullname_diemdanh']
                           else 'wrong time' if i['sogio_xepphong'] != i['sogio_diemdanh']
                           else 'normal' for j, i in df8.iterrows()]
    # Filter for wrong_teacher
    wrong_teacher = df8.query('check_status == "wrong teacher"').shape[0]
    normal = df8.query('check_status == "normal"').shape[0]
    wrong_time = df8.query('check_status == "wrong time"').shape[0]
    col2, col3, col4 = st.columns(3)
    with col2:
        st.markdown("Số lớp sai giáo viên")
        st.markdown(f":blue[{wrong_teacher}] lớp")
    with col3:
        st.markdown("Số lớp sai giờ")
        st.markdown(f":blue[{wrong_time}] lớp")
    with col4:
        st.markdown("Số lớp bình thường")
        st.markdown(f":blue[{normal}] lớp")

    st.dataframe(df8.reset_index(drop=True))
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Write each dataframe to a different worksheet.
        df8.to_excel(writer, sheet_name='Sheet1')
        # Close the Pandas Excel writer and output the Excel file to the buffer
        writer.save()
        st.download_button(
            label="Download danh sách đầy đủ xếp phòng và điểm danh",
            data=buffer,
            file_name="xepphong_diemdanh_full.xlsx",
            mime="application/vnd.ms-excel"
        )
