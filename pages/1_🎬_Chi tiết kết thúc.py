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


page_title = "Phiếu đăng ký kết thúc"
page_icon = "🎬"
layout = "wide"
st.set_page_config(page_title=page_title, page_icon=page_icon, layout=layout)

# ----------------------------------------
names = ["Phạm Tấn Thành", "Phạm Minh Tâm", "Vận hành"]
usernames = ["thanhpham", "tampham", "vietopvanhanh"]

# Load hashed passwords
file_path = Path(__file__).parent / 'hashed_pw.pkl'
with file_path.open("rb") as file:
    hashed_passwords = pickle.load(file)

authenticator = stauth.Authenticate(names, usernames, hashed_passwords,
                                    "sales_dashboard", "abcdef", cookie_expiry_days=1)

name, authentication_status, username = authenticator.login("Login", "main")

if authentication_status == False:
    st.error("Username/password is incorrect")

if authentication_status == None:
    st.warning("Please enter your username and password")

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
        return(pd.DataFrame((requests.get(link).json())))

    @st.cache_data(ttl=timedelta(days=365))
    def csv_reader(file):
        df = pd.read_csv(file)
        df = df.query("phanloai == 1")  # Filter lop chính
        df['date_created'] = pd.to_datetime(df['date_created'])
        return df

    @st.cache_data(ttl=timedelta(days=1))
    def collect_filtered_data(table, date_column='', start_time='', end_time=''):
        link = f"https://vietop.tech/api/get_data/{table}?column={date_column}&date_start={start_time}&date_end={end_time}"
        df = pd.DataFrame((requests.get(link).json()))
        df[date_column] = pd.to_datetime(df[date_column])
        return df

    @st.cache_data()
    def rename_lop(dataframe, column_name):
        dataframe[column_name] = dataframe[column_name].replace(
            {1: "Hoa Cúc", 2: "Gò Dầu", 3: "Lê Quang Định", 5: "Lê Hồng Phong"})
        return dataframe

    df = csv_reader("diemdanh_details.csv")
    df1 = collect_filtered_data(table='diemdanh_details', date_column='date_created',
                                start_time='2023-01-01', end_time='2025-01-01')
    # Tables for analysis ------------------------------------
    diemdanh_details = pd.concat([df, df1])
    orders = collect_data('https://vietop.tech/api/get_data/orders')

    # Filter ------------------------------------------------
    now = datetime.now()
    DEFAULT_START_DATE = datetime(now.year, now.month, 1)
    DEFAULT_END_DATE = datetime(now.year, now.month, 1) + timedelta(days=32)
    DEFAULT_END_DATE = DEFAULT_END_DATE.replace(day=1) - timedelta(days=1)

    # Create a form to get the date range filters
    with st.form(key='date_filter_form'):
        col1, col2 = st.columns(2)
        ketoan_start_time = col1.date_input(
            "Select start date", value=DEFAULT_START_DATE)
        ketoan_end_time = col2.date_input(
            "Select end date", value=DEFAULT_END_DATE)
        submit_button = st.form_submit_button(
            label='Filter',  use_container_width=True)

    # Filter ketthuc
    orders_ketthuc = orders.query("ketoan_active == 5 and deleted_at.isnull()")
    # Merge orders_ketthuc and diemdanh_details
    df = diemdanh_details[['ketoan_id', 'giohoc']]\
        .merge(orders_ketthuc, on='ketoan_id', how='right').groupby(
        ['ketoan_id', 'ketoan_coso', 'remaining_time', 'ketoan_tientrengio', 'date_end'], as_index=False).giohoc.sum()
    # Add 2 more columns
    df['gio_con_lai'] = df.remaining_time - df.giohoc
    try:
        df['thực thu kết thúc'] = df.gio_con_lai * df.ketoan_tientrengio
        # Convert to datetime
        df['date_end'] = pd.to_datetime(df['date_end'])
        # Filter gioconlai > 0 and time
        thucthu_ketthuc = df.query("gio_con_lai > 0")\
            .query("date_end >= @ketoan_start_time and date_end <= @ketoan_end_time")
        thucthu_ketthuc = thucthu_ketthuc.merge(
            orders[['hv_id', 'ketoan_id']], on='ketoan_id')

        thucthu_ketthuc = rename_lop(thucthu_ketthuc, 'ketoan_coso')
        thucthu_ketthuc_group = thucthu_ketthuc.groupby("ketoan_coso", as_index=False)[
            'thực thu kết thúc'].sum()
        ""
        st.subheader("Tổng thực thu kết thúc theo chi nhánh")

        fig1 = px.bar(thucthu_ketthuc_group, x='ketoan_coso',
                      y='thực thu kết thúc', text='thực thu kết thúc', color='ketoan_coso', color_discrete_sequence=['#07a203', '#ffc107', '#e700aa', '#2196f3', ])
        fig1.update_layout(
            # Increase font size for all text in the plot)
            xaxis_title='Chi nhánh', yaxis_title='Thực thu kết thúc', showlegend=True, font=dict(size=17))
        fig1.update_traces(
            hovertemplate="Thực thu kết thúc: %{y:,.0f}<extra></extra>",
            # Add thousand separators to the text label
            texttemplate='%{text:,.0f}',
            textposition='inside'  # Show the text label inside the bars
        )

        st.plotly_chart(fig1, use_container_width=True)
        thucthu_ketthuc.columns = ['ketoan_id', 'chi nhánh', 'giờ đăng ký', 'tiền trên giờ',
                                   'ngày kết thúc', 'giờ đã học', 'giờ còn lại', 'thực thu kết thúc', 'hv_id']
        st.subheader("Chi tiết thực thu kết thúc")
        st.dataframe(thucthu_ketthuc, use_container_width=True)
        import io
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            # Write each dataframe to a different worksheet.
            thucthu_ketthuc.to_excel(writer, sheet_name='Sheet1')
            # Close the Pandas Excel writer and output the Excel file to the buffer
            writer.save()
            st.download_button(
                label="Download thực thu kết thúc worksheets",
                data=buffer,
                file_name="thucthu_ketthuc.xlsx",
                mime="application/vnd.ms-excel"
            )
    except KeyError:
        st.warning(
            f"Tháng {date(now.year, now.month, 1)} hiện tại chưa có data, bạn chọn tháng trước nhé")
