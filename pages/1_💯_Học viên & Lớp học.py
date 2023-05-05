import streamlit as st
import requests
import pandas as pd
from pathlib import Path
import pickle
import streamlit_authenticator as stauth
from datetime import timedelta
import numpy as np

page_title = "Học viên và lớp đang học "
page_icon = "💯"

layout = "wide"
st.set_page_config(page_title=page_title,
                   page_icon=page_icon, layout=layout)
# ------------------------------------------
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
        return (pd.DataFrame((requests.get(link).json())))

    @st.cache_data()
    def rename_lop(dataframe, column_name):
        dataframe[column_name] = dataframe[column_name].replace(
            {1: "Hoa Cúc", 2: "Gò Dầu", 3: "Lê Quang Định", 5: "Lê Hồng Phong"})
        return dataframe

    khoahoc = collect_data('https://vietop.tech/api/get_data/khoahoc')
    khoahoc_me = khoahoc.query("kh_parent_id == 0 and kh_active == 1")
    lophoc = collect_data('https://vietop.tech/api/get_data/lophoc')
    lop_danghoc = lophoc.query(
        "(class_status == 'progress') and deleted_at.isnull()")
    df = lop_danghoc.merge(
        khoahoc_me[['kh_id', 'kh_ten']], left_on='kh_parent', right_on='kh_id')
    lophoc_detals = df.copy()
    # The percentage of kh_ten
    df1 = df.kh_ten.value_counts(
        normalize=True)
    df1 = df1.reset_index()
    df1['kh_ten'] = round(df1['kh_ten'], 2) * 100
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
    df["Percentage %"] = df["Percentage %"]/100
    df = df.style.background_gradient()
    df = df.format({'Percentage %': '{:.2%}'})

    # df = df.set_precision(0)
    st.subheader("Lớp đang học")
    st.dataframe(df, height=250, width=1000)
    st.markdown("---")
    st.subheader("Chi tiết lớp đang học")
    st.dataframe(lophoc_detals[['lop_id', 'lop_cn', 'class_type',
                 'lop_cahoc', 'kh_ten', 'lop_ten', 'lop_buoihoc', 'lop_note']])
    import io
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Write each dataframe to a different worksheet.
        lophoc_detals.to_excel(writer, sheet_name='Sheet1')
        # Close the Pandas Excel writer and output the Excel file to the buffer
        writer.save()
        st.download_button(
            label="Download chi tiết lớp đang học worksheets",
            data=buffer,
            file_name="lop_danghoc_details.xlsx",
            mime="application/vnd.ms-excel"
        )

# ------------------------------------------ Học viên đang học
    hocvien = collect_data(
        'https://vietop.tech/api/get_data/hocvien').query("hv_id != 737 and deleted_at.isnull()")
    orders = collect_data(
        'https://vietop.tech/api/get_data/orders').query("deleted_at.isnull()")
    molop = collect_data('https://vietop.tech/api/get_data/molop')
    molop = molop.query("molop_active == 1")
    # hv đang họccd Au
    hocvien_danghoc = hocvien.merge(orders, on='hv_id')\
        .query("ketoan_active == 1")

    hocvien_danghoc = rename_lop(hocvien_danghoc, 'ketoan_coso')
    df = hocvien_danghoc[['hv_id']].merge(molop, on='hv_id', how='inner')\
        .drop_duplicates("hv_id")\
        .merge(lophoc[['lop_cn', 'lop_id', 'kh_parent']], on='lop_id', how='inner')\
        .merge(khoahoc_me, left_on='kh_parent', right_on='kh_id')
    hv_danghoc_details = df.copy()
    df = df.groupby(["lop_cn", "kh_ten"], as_index=False).size().rename(
        columns={"size": "total_students"})
    df = rename_lop(df, 'lop_cn')
    # The percentage of kh_ten
    df1 = df.groupby("kh_ten", as_index=False)['total_students'].sum()
    df1['Percentage %'] = round(df1['total_students'] /
                                df1['total_students'].sum(), 2) * 100
    df1 = df1.drop("total_students", axis=1)
    df = df.pivot_table(index='kh_ten', values='total_students',
                        columns='lop_cn', aggfunc='sum', margins=True, fill_value=0)
    df = df.reset_index()
    # Merge df and df1

    df = df.merge(df1, on='kh_ten', how='left')
    df = df.fillna(100)
    df = df.set_index("kh_ten")

    df["Percentage %"] = df["Percentage %"]/100
    df = df.style.background_gradient()
    df = df.format({'Percentage %': '{:.2%}'})
    "---"
    # df = df.drop("index", axis=1)
    st.subheader("Học viên đang học")
    st.dataframe(df, height=250, width=1000)
    st.subheader("Chi tiết học viên đang học")
    st.dataframe(hv_danghoc_details[['hv_id', 'ketoan_id', 'lop_id', 'lop_cn',
                 'kh_ten', 'created_at', ]], height=250, width=1000)

# ------------------------------------------------------------------------------Danh sách học viên đang học, bảo lưu, chờ lớp
    df = hocvien[['hv_id', 'hv_fullname', 'hv_email', 'hv_camket', 'hv_coso', 'hv_status']]\
        .merge(orders[['hv_id', 'ketoan_active', 'ketoan_id', 'remaining_time', 'ketoan_price']], on='hv_id')\
        .query('ketoan_active == 0 or ketoan_active == 1 or ketoan_active == 4')\
        # Mapping ketoan_active
    conditions = [(df['ketoan_active'] == 0), df['ketoan_active']
                  == 1, df['ketoan_active'] == 4, df['ketoan_active'] == 5]
    choices = ["Chưa học", "Đang học", "Bảo lưu", "Kết thúc"]
    df['ketoan_active'] = np.select(conditions, choices)
    df = rename_lop(df, 'hv_coso')
    df = df.drop(['hv_status', 'hv_camket'], axis=1)

    "---"
    st.subheader("Danh sách học viên đang học, bảo lưu, chờ lớp")
    st.text(f"Tổng học viên đang học, bảo lưu, chờ lớp {df.shape[0]}")
    st.dataframe(df.set_index("hv_id"), use_container_width=True)

    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Write each dataframe to a different worksheet.
        df.to_excel(writer, sheet_name='Sheet1')
        # Close the Pandas Excel writer and output the Excel file to the buffer
        writer.save()
        st.download_button(
            label="Download danh sách hv đang học, bảo lưu, chờ lớp worksheets",
            data=buffer,
            file_name="danghoc_baluu_cholop.xlsx",
            mime="application/vnd.ms-excel"
        )
