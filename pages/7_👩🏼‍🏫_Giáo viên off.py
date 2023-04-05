import matplotlib.pyplot as plt
import requests
import pandas as pd
from datetime import datetime, timedelta, date
import streamlit as st
import plotly.express as px
from pathlib import Path
import pickle
import streamlit_authenticator as stauth
import plotly.graph_objects as go

page_title = "Số lớp khai giảng"
page_icon = "📖"
layout = "wide"
st.set_page_config(page_title=page_title, page_icon=page_icon, layout=layout)
# names = ["Phạm Tấn Thành", "Phạm Minh Tâm", "Vận hành"]
# usernames = ["thanhpham", "tampham", "vietopvanhanh"]

# # Load hashed passwords
# file_path = Path(__file__).parent / 'hashed_pw.pkl'
# with file_path.open("rb") as file:
#     hashed_passwords = pickle.load(file)

# authenticator = stauth.Authenticate(names, usernames, hashed_passwords,
#                                     "sales_dashboard", "abcdef", cookie_expiry_days=1)

# name, authentication_status, username = authenticator.login("Login", "main")
authentication_status = st.session_state['authentication_status']
authenticator = st.session_state['authenticator']

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
    # -----------------------------------------------------------------------------
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

    @st.cache_data(ttl=timedelta(days=1))
    def collect_data(link):
        return(pd.DataFrame((requests.get(link).json())))

    @st.cache_data()
    def grand_total(dataframe, column):
        # create a new row with the sum of each numerical column
        totals = dataframe.select_dtypes(include=[float, int]).sum()
        totals[column] = "Grand total"
        # append the new row to the dataframe
        dataframe = dataframe.append(totals, ignore_index=True)
        return dataframe

    @st.cache_data()
    def rename_lop(dataframe, column_name):
        dataframe[column_name] = dataframe[column_name].replace(
            {1: "Hoa Cúc", 2: "Gò Dầu", 3: "Lê Quang Định", 5: "Lê Hồng Phong"})
        return dataframe

    @st.cache_data(ttl=timedelta(days=1))
    def collect_filtered_data(table, date_column='', start_time='', end_time=''):
        link = f"https://vietop.tech/api/get_data/{table}?column={date_column}&date_start={start_time}&date_end={end_time}"
        df = pd.DataFrame((requests.get(link).json()))
        df[date_column] = pd.to_datetime(df[date_column])
        return df

    gv_diemdanh = collect_filtered_data(
        table='diemdanh', date_column='date_created', start_time=ketoan_start_time, end_time=ketoan_end_time)
    users = collect_data('https://vietop.tech/api/get_data/users')

    df = gv_diemdanh[gv_diemdanh.class_status == 'gv_off']
    df = df[['lop_id', 'giaovien', 'cahoc',
             'class_status', 'date_created', 'module']]
    df = df.merge(users[['id', 'fullname', 'vietop_dept']],
                  left_on='giaovien', right_on='id')
    df = rename_lop(df, 'vietop_dept')
    st.subheader("Danh sách giáo viên off")
    df
