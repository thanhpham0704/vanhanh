import streamlit as st
import requests
import pandas as pd
from pathlib import Path
import pickle
import streamlit_authenticator as stauth
from datetime import timedelta

page_title = "Học viên và lớp đang học "
page_icon = "💯"

layout = "wide"
st.set_page_config(page_title=page_title,
                   page_icon=page_icon, layout=layout)
# ------------------------------------------
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
                right: 10px;
            }
            </style>
            """,
        unsafe_allow_html=True
    )
    st.title(page_title + " " + page_icon)
    "---"

# ------------------------------------------ Lớp đang học

    @st.cache_data(ttl=timedelta(days=1))
    def collect_data(link):
        return(pd.DataFrame((requests.get(link).json())))

    @st.cache_data()
    def rename_lop(dataframe, column_name):
        dataframe[column_name] = dataframe[column_name].replace(
            {1: "Hoa Cúc", 2: "Gò Dầu", 3: "Lê Quang Định", 5: "Lê Hồng Phong"})
        return dataframe

    khoahoc = collect_data('https://vietop.tech/api/get_data/khoahoc')
    khoahoc_me = khoahoc.query("kh_parent_id == 0 and kh_active == 1")
    lophoc = collect_data('https://vietop.tech/api/get_data/lophoc')

    lop_danghoc = lophoc.query(
        "(lop_status == 2 or lop_status == 4) and deleted_at.isnull()")
    df = lop_danghoc.merge(
        khoahoc_me[['kh_id', 'kh_ten']], left_on='kh_parent', right_on='kh_id')
    # The percentage of kh_ten
    df1 = df.kh_ten.value_counts(
        normalize=True)
    df1 = df1.reset_index()
    df1['kh_ten'] = round(df1['kh_ten'] * 100)
    # Group by
    df = df.groupby(["lop_cn", "kh_ten"], as_index=False).size()
    df = df.rename(columns={"size": "total_classes"})
    df = rename_lop(df, 'lop_cn')

    df = df.pivot_table(index='kh_ten', values='total_classes',
                        columns='lop_cn', aggfunc='sum', margins=True, fill_value=0, margins_name="All Vietop")
    df = df.reset_index()
    # Merge df and df1
    df = df.merge(df1, left_on='kh_ten', right_on='index', how='left')
    df = df.drop("index", axis=1)
    df = df.fillna(100)
    df = df.rename(
        columns={"kh_ten_y": "Percentage %", "kh_ten_x": "Khoá học"})
    df = df.set_index("Khoá học")
    st.subheader("Lớp đang học")
    st.dataframe(df.style.background_gradient(
    ).set_precision(0), height=250, width=1000)


# ------------------------------------------ Học viên đang học
    hocvien = collect_data(
        'https://vietop.tech/api/get_data/hocvien').query("hv_id != 737 and deleted_at.isnull()")
    orders = collect_data(
        'https://vietop.tech/api/get_data/orders').query("deleted_at.isnull()")
    molop = collect_data('https://vietop.tech/api/get_data/molop')

    # hv đang họccd Au
    hocvien_danghoc = hocvien.merge(orders, on='hv_id')\
        .query("ketoan_active == 1")

    hocvien_danghoc = rename_lop(hocvien_danghoc, 'ketoan_coso')
    df = hocvien_danghoc[['hv_id']].merge(molop, on='hv_id', how='inner')\
        .drop_duplicates("hv_id")\
        .merge(lophoc[['lop_cn', 'lop_id', 'kh_parent']], on='lop_id', how='inner')\
        .merge(khoahoc_me, left_on='kh_parent', right_on='kh_id')

    df = df.groupby(["lop_cn", "kh_ten"], as_index=False).size().rename(
        columns={"size": "total_students"})
    df = rename_lop(df, 'lop_cn')
    # The percentage of kh_ten
    df1 = df.groupby("kh_ten", as_index=False)['total_students'].sum()
    df1['Percentage %'] = round(df1['total_students'] /
                                df1['total_students'].sum() * 100, 2)
    df1 = df1.drop("total_students", axis=1)
    df = df.pivot_table(index='kh_ten', values='total_students',
                        columns='lop_cn', aggfunc='sum', margins=True, fill_value=0)
    df = df.reset_index()
    # Merge df and df1

    df = df.merge(df1, on='kh_ten', how='left')
    df = df.fillna(100)
    df = df.set_index("kh_ten")
    "---"
    # df = df.drop("index", axis=1)
    st.subheader("Học viên đang học")
    st.dataframe(df.style.background_gradient(
    ).set_precision(0), height=250, width=1000)
