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
try:
    authentication_status = st.session_state['authentication_status']
    authenticator = st.session_state['authenticator']
except KeyError:
    authentication_status = None
# names = ["Phạm Tấn Thành", "Phạm Minh Tâm", "Vận hành"]
# usernames = ["thanhpham", "tampham", "vietopvanhanh"]

# # Load hashed passwords
# file_path = Path(__file__).parent / 'hashed_pw.pkl'
# with file_path.open("rb") as file:
#     hashed_passwords = pickle.load(file)

# authenticator = stauth.Authenticate(names, usernames, hashed_passwords,
#                                     "sales_dashboard", "abcdef", cookie_expiry_days=1)


# name, authentication_status, username = authenticator.login("Login", "main")r

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
    with st.sidebar.form(key='date_filter_form'):
        ketoan_start_time = st.date_input(
            "Select start date", value=DEFAULT_START_DATE)
        ketoan_end_time = st.date_input(
            "Select end date", value=DEFAULT_END_DATE)
        submit_button = st.form_submit_button(
            label='Filter',  use_container_width=True)

    @st.cache_data(ttl=timedelta(days=1))
    def collect_data(link):
        return (pd.DataFrame((requests.get(link).json())))

    @st.cache_data(ttl=timedelta(days=1))
    def collect_filtered_data(table, date_column='', start_time='', end_time=''):
        link = f"https://vietop.tech/api/get_data/{table}?column={date_column}&date_start={start_time}&date_end={end_time}"
        df = pd.DataFrame((requests.get(link).json()))
        df[date_column] = pd.to_datetime(df[date_column])
        return df

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

    # Get khoahoc
    khoahoc = collect_data('https://vietop.tech/api/get_data/khoahoc')
    # Get a response
    lophoc = collect_filtered_data(
        table='lophoc', date_column='created_at', start_time=ketoan_start_time, end_time=ketoan_end_time)

    df = lophoc.merge(khoahoc[['kh_id', 'kh_ten']], on='kh_id', how='inner')
    df = df.query("lop_type == 1 and deleted_at.isnull()")
    df['created_at'] = df['created_at'].astype("datetime64[ns]")

    # Create Month
    # df['created_at'] = df['created_at'].astype("datetime64[ns]")
    # df['created_at_month'] = df['created_at'].dt.strftime('%-m')
    # df['created_at_year'] = df['created_at'].dt.strftime('%-Y')
    # df['lop_end'] = df['lop_end'].astype("datetime64[ns]")
    # df['lop_end_month'] = df['lop_end'].dt.strftime('%-m')
    # df['lop_end_year'] = df['created_at'].dt.strftime('%-Y')
    # display(lophoc_2023.head())
    # total class open
    df['created_at'] = df['created_at'].dt.date
    df = rename_lop(df, 'lop_cn')
    df = df.groupby(['lop_id', 'lop_cn', 'class_type', 'kh_ten',
                    'created_at'], as_index=False).size()
    df = grand_total(df, 'lop_cn')
    df_group = df.groupby("lop_cn", as_index=False)['size'].sum()
    # Create bar_chart
    fig1 = px.bar(df_group, x='lop_cn',
                  y='size', text='size', color='lop_cn', color_discrete_map={'Gò Dầu': '#07a203', 'Hoa Cúc': '#ffc107', 'Lê Hồng Phong': '#e700aa', 'Lê Quang Định': '#2196f3', 'Grand total': "White"})
    fig1.update_layout(
        # Increase font size for all text in the plot)
        xaxis_title='Chi nhánh', yaxis_title='Số lớp khai giảng', showlegend=True, font=dict(size=17), xaxis={'categoryorder': 'total descending'})
    fig1.update_traces(
        hovertemplate="Số lớp khai giảng: %{y:,.0f}<extra></extra>",
        # Add thousand separators to the text label
        texttemplate='%{text:,.0f}',
        textposition='inside')  # Show the text label inside the bars
    st.subheader("Số lớp khai giảng theo chi nhánh")
    st.plotly_chart(fig1, use_container_width=True)
    df = df.set_index("lop_id")
    "---"
    st.subheader(
        f"Chi tiết lớp khai giảng")
    st.dataframe(df.drop('size', axis=1), use_container_width=True)
