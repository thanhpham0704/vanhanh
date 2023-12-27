import streamlit as st
import requests
import pandas as pd
from pathlib import Path
import pickle
import streamlit_authenticator as stauth
from datetime import timedelta
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import io
buffer = io.BytesIO()

page_title = "Thực thu điểm danh theo hình thức lớp"
page_icon = "📘"

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
    # %%
    # Date filter
    now = datetime.now()
    DEFAULT_START_DATE = datetime(now.year, now.month, 1)
    DEFAULT_END_DATE = datetime(now.year, now.month, 1) + timedelta(days=32)
    DEFAULT_END_DATE = DEFAULT_END_DATE.replace(day=1) - timedelta(days=1)

    # Create a form to get the date range filters
    with st.sidebar.form(key='date_filter_form'):
        # col1, col2 = st.columns(2)
        ketoan_start_time = st.date_input(
            "Select start date", value=DEFAULT_START_DATE)
        ketoan_end_time = st.date_input(
            "Select end date", value=DEFAULT_END_DATE)
        submit_button = st.form_submit_button(
            label='Filter',  use_container_width=True)
    # %%

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
    lophoc = collect_data('https://vietop.tech/api/get_data/lophoc')

    def lophoc_khoahoc_me():
        # lop_danghoc = lophoc.query(
        #         "(class_status == 'progress') and deleted_at.isnull()")
        # lophoc = collect_data('https://vietop.tech/api/get_data/lophoc')
        khoahoc = collect_data('https://vietop.tech/api/get_data/khoahoc')
        khoahoc_me = khoahoc.query("kh_parent_id == 0 and kh_active == 1")
        df = lophoc.merge(
        khoahoc_me[['kh_id', 'kh_ten']], left_on='kh_parent', right_on='kh_id')
        return df
        
 
    diemdanh_details = collect_filtered_data(table='diemdanh_details', date_column='date_created', start_time='2023-01-01', end_time='2023-12-31')

    users = collect_data('https://vietop.tech/api/get_data/users')
 

    diemdanh_details['date_created'] = diemdanh_details['date_created'].astype(
    "datetime64[ns]")

    thucthu = diemdanh_details.query(
        'date_created >= @ketoan_start_time and date_created <= @ketoan_end_time')\
        .groupby(['ketoan_id', 'lop_id', 'gv_id', 'date_created'], as_index=False)['price', 'giohoc'].sum()\
        .merge(lophoc[['lop_id']], on='lop_id', how='left')\
        .merge(users[['fullname', 'id']], left_on='gv_id', right_on='id', how='left')

    
    df = thucthu.merge(lophoc_khoahoc_me()[['lop_id', 'lop_cn', 'kh_ten', 'class_type','lop_ten', 'lop_start', 'lop_end']], on = 'lop_id', how = 'left')
    df_group = df.groupby(["kh_ten", "class_type"], as_index = False).price.sum()
   
    
    fig1 = px.bar(df_group, x="price",
                   y="kh_ten", color="class_type", barmode="group", color_discrete_sequence=['#ffc107', '#07a203', '#2196f3', '#e700aa'], text=df_group["price"].apply(lambda x: f'{x:,.0f}'))
    # update the chart layout
    fig1.update_layout(title='',
                        xaxis_title='', yaxis_title='', showlegend=True, height=600 )
    fig1.update_traces(
        hovertemplate="Thực thu: %{x:,.0f}<extra></extra>",
         textposition='auto')
    
    st.plotly_chart(fig1, use_container_width=True)
    "---"
    st.subheader(
        f"Chi tiết thực thu điểm danh theo hình thức lớp")
    st.dataframe(df, use_container_width=True)

    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Write each dataframe to a different worksheet.
        df.to_excel(
            writer, sheet_name='Sheet1')
        # Close the Pandas Excel writer and output the Excel file to the buffer
        writer.save()
        st.download_button(
            label="Download",
            data=buffer,
            file_name="Chi_tiet_thucthu_theo_hinh_thuc_lop.xlsx",
            mime="application/vnd.ms-excel"
        )

