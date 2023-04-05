import matplotlib.pyplot as plt
import requests
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
import plotly.express as px
from pathlib import Path
import pickle
import streamlit_authenticator as stauth
import plotly.graph_objects as go

page_title = "Học viên mới và kết thúc"
page_icon = "👦🏻"
layout = "wide"
st.set_page_config(page_title=page_title, page_icon=page_icon, layout=layout)
authentication_status = st.session_state['authentication_status']
authenticator = st.session_state['authenticator']
# names = ["Phạm Tấn Thành", "Phạm Minh Tâm", "Vận hành"]
# usernames = ["thanhpham", "tampham", "vietopvanhanh"]

# # Load hashed passwords
# file_path = Path(__file__).parent / 'hashed_pw.pkl'
# with file_path.open("rb") as file:
#     hashed_passwords = pickle.load(file)

# authenticator = stauth.Authenticate(names, usernames, hashed_passwords,
#                                     "sales_dashboard", "abcdef", cookie_expiry_days=1)

# name, authentication_status, username = authenticator.login("Login", "main")

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

    orders = collect_data(
        'https://vietop.tech/api/get_data/orders').query("deleted_at.isnull()")
    leads = collect_data(
        'https://vietop.tech/api/get_data/leads')
    hocvien = collect_data(
        'https://vietop.tech/api/get_data/hocvien').query("hv_id != 737 and deleted_at.isna()")
    orders['date_end'] = orders['date_end'].astype('datetime64[ns]')
    orders_ketthuc = orders[['ketoan_id', 'hv_id', 'ketoan_active', 'date_end']]\
        .query('ketoan_active == 5 and date_end >= @ketoan_start_time and date_end <= @ketoan_end_time')

    orders_conlai = orders[['ketoan_id', 'hv_id']][orders.ketoan_active.isin(
        [0, 1, 4])]  # .query('created_at > "2022-10-01"')
    hv_conlai = hocvien[['hv_id']].merge(orders_conlai, on='hv_id')
    orders_kt_that = orders_ketthuc[~orders_ketthuc['hv_id'].isin(
        hv_conlai['hv_id'])]
    orders_kt_that = orders_kt_that.merge(
        hocvien[['hv_id', 'hv_coso', 'hv_fullname', 'hv_email']], on='hv_id')
    orders_kt_that.drop("ketoan_active", axis=1, inplace=True)
    orders_kt_that['status'] = 'Kết thúc thật'
    # Subset and merge leads
    hocvien['hv_ngayhoc'] = hocvien['hv_ngayhoc'].astype("datetime64[ns]")
    hv_october = hocvien[['hv_id', 'hv_fullname', 'hv_coso', 'hv_ngayhoc']][hocvien.hv_ngayhoc.notnull()]\
        .query('hv_ngayhoc >= @ketoan_start_time and hv_ngayhoc <= @ketoan_end_time')\
        .merge(leads[['hv_id']], on='hv_id', how='left')

    hv_october['status'] = 'Học viên mới'
    # Concat moi va cu
    new_old = pd.concat([orders_kt_that, hv_october])
    new_old = new_old.astype(
        {"date_end": "datetime64[ns]", "hv_ngayhoc": "datetime64[ns]"})
    new_old['date_end_month'] = new_old['date_end'].dt.strftime('%B')
    new_old['hv_ngayhoc_month'] = new_old['hv_ngayhoc'].dt.strftime('%B')

    new = new_old.query("status == 'Học viên mới'")
    old = new_old.query("status == 'Kết thúc thật'")
    # Rename hv_coso
    new = rename_lop(new, 'hv_coso')
    old = rename_lop(old, 'hv_coso')
    # Groupby
    new_group = new.drop_duplicates().groupby(
        ["hv_coso", "hv_ngayhoc_month"], as_index=False).size()
    new_group['status'] = 'mới đăng ký'
    new_group.columns = ['hv_coso', 'date_created', 'num_student', 'status']
    new_total = grand_total(new_group, 'hv_coso')
    new_total = new_total.set_index("hv_coso")
    # Groupby
    old_group = old.drop_duplicates().groupby(
        ["hv_coso", "date_end_month"], as_index=False).size()
    old_group['status'] = 'kết thúc thật'
    old_group.columns = ['hv_coso', 'date_created', 'num_student', 'status']
    old_total = grand_total(old_group, 'hv_coso')
    old_total = old_total.set_index("hv_coso")

    df = pd.concat([new_group, old_group])
    # color_discrete_map={'Gò Dầu': '#07a203', 'Hoa Cúc': '#ffc107', 'Lê Hồng Phong': '#e700aa', 'Lê Quang Định': '#2196f3', 'Grand total': "White"}
    fig1 = px.bar(df, x='hv_coso',
                  y='num_student', text='num_student', color='status', barmode="group")
    fig1.update_layout(
        # Increase font size for all text in the plot)
        xaxis_title='Chi nhánh', yaxis_title='Thực thu kết thúc', showlegend=True, font=dict(size=17), xaxis={'categoryorder': 'total descending'})
    fig1.update_traces(
        hovertemplate="Thực thu kết thúc: %{y:,.0f}<extra></extra>",
        # Add thousand separators to the text label
        texttemplate='%{text:,.0f}',
        textposition='inside')  # Show the text label inside the bars
    ""
    ""
    # Plot a pie chart
    labels = ['Hv_mới', 'Kết thúc thât']
    values = [new_group.iloc[:, 2].sum(), old_group.iloc[:, 2].sum()]
    # pull is given as a fraction of the pie radius
    fig2 = go.Figure(
        data=[go.Pie(labels=labels, values=values, pull=[0, 0.1])])
    fig2.update_layout(
        # Increase the font size of the text
        font=dict(
            size=20
        ))

    st.subheader("Tỷ trọng học viên mới và kết thúc thật toàn Vietop")
    st.plotly_chart(fig2, use_container_width=True)
    # Bar chart
    st.subheader("Số lượng học viên cũ và kết thúc thật theo chi nhánh")
    st.plotly_chart(fig1, use_container_width=True)
    # Create 2 columns
    ""
    col1, col2 = st.columns(2, gap='large')
    col1.subheader("Chi tiết học viên mới")
    col1.dataframe(new.reindex(
        columns=['hv_id', 'hv_fullname', 'hv_coso', 'hv_ngayhoc', 'status']), use_container_width=True)

    col2.subheader("Chi tiết học viên kết thúc thật")

    col2.dataframe(old.reindex(
        columns=['hv_id', 'hv_fullname', 'hv_coso', 'date_end', 'status']), use_container_width=True)
