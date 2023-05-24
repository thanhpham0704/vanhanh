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

page_title = "Giáo viên và lớp off"
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

    lophoc = collect_data('https://vietop.tech/api/get_data/lophoc')
    khoahoc = collect_data('https://vietop.tech/api/get_data/khoahoc')
    khoahoc_me = khoahoc.query("kh_parent_id == 0 and kh_active == 1")
    # Get kh_ten
    lop_danghoc = lophoc.query(
        "(class_status == 'progress' or class_status == 'suspended') and deleted_at.isnull()")
    # lop_danghoc[['lop_id']]
    kh_lop = lop_danghoc.merge(
        khoahoc_me[['kh_id', 'kh_ten']], left_on='kh_parent', right_on='kh_id', how='left')
    # kh_lop[['lop_id', 'kh_ten']]
    # Chi tiết gv_off
    df = gv_diemdanh[gv_diemdanh.class_status == 'gv_off']
    df = df[['lop_id', 'giaovien', 'cahoc',
             'class_status', 'date_created', 'module']]
    df = df.merge(users[['id', 'fullname', 'vietop_dept']],
                  left_on='giaovien', right_on='id')
    df = rename_lop(df, 'vietop_dept')
    df = df.reindex(columns=['lop_id', 'fullname', 'vietop_dept',
                    'cahoc', 'class_status', 'module', 'date_created'])

    # Chi tiết gv_off and kh_ten
    df_kh_ten = df.merge(kh_lop[['kh_ten', 'lop_id']], on='lop_id', how='left')
    df_kh_ten['kh_ten'] = df_kh_ten['kh_ten'].fillna("Không có tên khoá học")
    # Group gv_off by vietop_dept
    df_group = df.groupby("vietop_dept", as_index=False).size()
    df_group = grand_total(df_group, 'vietop_dept')
    # Group gv_off by kh_ten
    df_group_kh_ten = df_kh_ten.groupby("kh_ten", as_index=False).size()
    df_group_kh_ten = grand_total(df_group_kh_ten, 'kh_ten')
    # Create bar_chart
    fig1 = px.bar(df_group, x='vietop_dept',
                  y='size', text='size', color='vietop_dept', color_discrete_map={'Gò Dầu': '#07a203', 'Hoa Cúc': '#ffc107', 'Lê Hồng Phong': '#e700aa', 'Lê Quang Định': '#2196f3', 'Grand total': "White"})
    fig1.update_layout(
        # Increase font size for all text in the plot)
        xaxis_title='Chi nhánh', yaxis_title='Giáo viên off', showlegend=True, font=dict(size=17), xaxis={'categoryorder': 'total descending'})
    fig1.update_traces(
        hovertemplate="Số giáo viên off: %{y:,.0f}<extra></extra>",
        # Add thousand separators to the text label
        texttemplate='%{text:,.0f}',
        textposition='inside')  # Show the text label inside the bars

    # Create bar_chart
    fig2 = px.bar(df_group_kh_ten, x='kh_ten',
                  y='size', text='size')
    fig2.update_layout(
        # Increase font size for all text in the plot)
        xaxis_title='Tên khoá học', yaxis_title='Lớp off', showlegend=True, font=dict(size=17), xaxis={'categoryorder': 'total descending'})
    fig2.update_traces(
        hovertemplate="Số lớp off: %{y:,.0f}<extra></extra>",
        # Add thousand separators to the text label
        texttemplate='%{text:,.0f}',
        textposition='inside')  # Show the text label inside the bars
    col1, col2 = st.columns(2)
    col1.subheader("Số lớp off theo tên khoá học")
    col1.plotly_chart(fig2, use_container_width=True)
    col2.subheader("Số giáo viên off theo chi nhánh")
    col2.plotly_chart(fig1, use_container_width=True)

    st.subheader("Chi tiết danh sách giáo viên off")
    st.dataframe(df_kh_ten.set_index('lop_id'), use_container_width=True)
    import io
    buffer = io.BytesIO()
    # Create a Pandas Excel writer using XlsxWriter as the engine.
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Write each dataframe to a different worksheet.
        df_kh_ten.to_excel(writer, sheet_name='Sheet1')
        # Close the Pandas Excel writer and output the Excel file to the buffer
        writer.save()
        st.download_button(
            label="Download chi tiết giáo viên off worksheets",
            data=buffer,
            file_name="gv_off.xlsx",
            mime="application/vnd.ms-excel"
        )
