import streamlit as st
import requests
import pandas as pd
from pathlib import Path
import streamlit_authenticator as stauth
from datetime import timedelta
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

page_title = "Quản Lý Lớp Đang Học"
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
    diemdanh_details = collect_data(
        'https://vietop.tech/api/get_data/diemdanh_details')
    lop_danghoc = lophoc.query(
        "(class_status == 'progress') and deleted_at.isnull()")
    molop = collect_data(
        'https://vietop.tech/api/get_data/molop').query('molop_active ==1')

    # Get khoahoc_me's name
    df = lop_danghoc.merge(
        khoahoc_me[['kh_id', 'kh_ten']], left_on='kh_parent', right_on='kh_id')
    # Get the average number of students ------------------------------------------------------------------------------------------
    hv_lop = df.merge(molop[['lop_id']], on='lop_id')
    # Average num of students in each kind of class
    df_avg_hv = hv_lop.groupby(["lop_id", "kh_ten"],
                               as_index=False)['lop_ten'].count()
    df_avg_hv = df_avg_hv.rename(columns={'lop_ten': 'sỉ số'})
    # Get the distribution of average number of students
    df_dis = df_avg_hv.copy()
    # Filter for lop nhom
    df_dis_nhom = df_avg_hv[df_avg_hv['kh_ten'].isin(
        ['Nhóm Premium', 'Nhóm Online'])]

    fig2 = px.histogram(df_dis_nhom, x="sỉ số",)
    fig2.update_traces(go.Histogram(
        x=df_dis_nhom['sỉ số'],
        # hovertemplate="Count học viên: %{y}<extra></extra>",
        text=[
            f"{count}" for count in df_dis_nhom['sỉ số'].value_counts().sort_index()],
        textposition='inside'
    ))

    fig2.update_layout(
        xaxis_title='Hv_bin',
        yaxis_title='Count',
        showlegend=True,
        font=dict(size=20),
        xaxis={'categoryorder': 'total descending'},
        bargap=0.2
    )

    df_avg_hv = df_avg_hv.groupby("kh_ten", as_index=False)['sỉ số'].mean()
    # Round the avg num of students to 2 decimal points
    df_avg_hv['sỉ số'] = round(df_avg_hv['sỉ số'], 1)
    # Rename the column
    df_avg_hv.rename(
        columns={'sỉ số': 'Số học viên trung bình'}, inplace=True)

    # Create bar_chart
    fig1 = px.bar(df_avg_hv, x='kh_ten',
                  y='Số học viên trung bình', text='Số học viên trung bình')
    fig1.update_layout(
        # Increase font size for all text in the plot)
        xaxis_title='', yaxis_title='Trung bình học viên', showlegend=True, font=dict(size=20), xaxis={'categoryorder': 'total descending'})
    fig1.update_traces(
        hovertemplate="Trung bình học viên: %{y:,.0f}<extra></extra>",
        # Add thousand separators to the text label
        texttemplate='%{text:,.0f}',
        textposition='inside')  # Show the text label inside the bars

    # Get the detail spreadsheet
    lophoc_details = df.copy()
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
    st.subheader("Số lớp đang học theo từng loại lớp")
    st.dataframe(df, height=250, width=1000)
    st.subheader("Trung bình số lượng học viên trong từng loại lớp học")
    st.plotly_chart(fig1, use_container_width=True)
    st.subheader("Phân phối số lượng học viên trong các lớp nhóm")
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown("---")
    st.subheader("Chi tiết lớp đang học")
    lophoc_details = lophoc_details[['lop_id', 'lop_cn', 'class_type',
                                     'lop_cahoc', 'kh_ten', 'lop_buoihoc', 'lop_note']].merge(df_dis[['lop_id', 'sỉ số']], on='lop_id', how='left')
    lophoc_details = rename_lop(lophoc_details, 'lop_cn')
    lophoc_details = lophoc_details.reindex(
        columns=['lop_id', 'lop_cn', 'kh_ten', 'sỉ số', 'lop_cahoc', 'lop_buoihoc', 'class_type',
                 'lop_note'])
    st.dataframe(lophoc_details)

    import io
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Write each dataframe to a different worksheet.
        lophoc_details.to_excel(writer, sheet_name='Sheet1')
        # Close the Pandas Excel writer and output the Excel file to the buffer
        writer.save()
        st.download_button(
            label="Download chi tiết lớp đang học worksheets",
            data=buffer,
            file_name="lop_danghoc_details.xlsx",
            mime="application/vnd.ms-excel"
        )
