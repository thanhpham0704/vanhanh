import requests
import pandas as pd
import json
from datetime import date, timedelta
import streamlit as st
import plotly.express as px
from pathlib import Path
import pickle
import streamlit_authenticator as stauth

page_title = "Bảo lưu"
page_icon = "🛟"
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
    "---"

    @st.cache_data(ttl=timedelta(days=1))
    def collect_data(link):
        return(pd.DataFrame((requests.get(link).json())))

    @st.cache_data(ttl=timedelta(days=1))
    def rename_lop(dataframe, column_name):
        dataframe[column_name] = dataframe[column_name].replace(
            {1: "Hoa Cúc", 2: "Gò Dầu", 3: "Lê Quang Định", 5: "Lê Hồng Phong"})
        return dataframe

    @st.cache_data()
    def get_link(dataframe):
        # Get url
        url = "https://vietop.tech/admin/hocvien/view/"
        # Initiate an empty list
        hv_link = []
        # Loop over hv_id
        for id in dataframe.hv_id:
            hv_link.append(url + str(id))
        # Assign new value to a new column
        dataframe['hv_link'] = hv_link
        return dataframe

    orders = collect_data(
        'https://vietop.tech/api/get_data/orders').query("deleted_at.isnull()")
    hocvien = collect_data(
        'https://vietop.tech/api/get_data/hocvien').query("hv_id != 737 and deleted_at.isna()")
    hocvien = get_link(hocvien)
    req = requests.get('https://vietop.tech/api/get_data/history')
    req_json = req.json()
    baoluu_date = pd.DataFrame(json.loads(
        r['history_value']) for r in req_json)
    history = pd.DataFrame(req_json)

    baoluu_date = baoluu_date[baoluu_date.ngayhoclai.notnull(
    ) & baoluu_date.ngaybaoluu.notnull()]
    baoluu_date = baoluu_date[['ketoan_id',
                               'ngayhoclai', 'ngaybaoluu', 'lydo']]
    # Change data types
    baoluu_date = baoluu_date.astype(
        {'ketoan_id': 'int32', 'ngayhoclai': 'datetime64[ns]', 'ngaybaoluu': 'datetime64[ns]'})
    # Format dates
    baoluu_date['ngayhoclai'] = baoluu_date['ngayhoclai'].dt.strftime(
        '%d-%m-%Y')
    baoluu_date['ngaybaoluu'] = baoluu_date['ngaybaoluu'].dt.strftime(
        '%d-%m-%Y')
    # Merge history
    df = history.query("action == 'baoluu' and (object == 'giahan' or object == 'baoluu')").\
        merge(orders.query('ketoan_active == 4'), on='ketoan_id',
              how='inner').drop_duplicates(subset='ketoan_id', keep='last')
    # Merge hocvien
    df = df.merge(hocvien, left_on='hv_id_x', right_on='hv_id')
    # Merge ngaybaoluu
    df = df.merge(baoluu_date, on='ketoan_id', how='inner').drop_duplicates(
        subset='ketoan_id', keep='last')
    # Slice columns
    df = df[['hv_id_x', 'ketoan_id', 'ketoan_coso', 'hv_fullname',
             'ngaybaoluu', 'ngayhoclai', 'object', 'lydo']]
    # Create conlai columns
    df['today'] = date.today().strftime('%Y-%m-%d')
    # Convert string to datetime
    df = df.astype(
        {'today': 'datetime64[ns]', 'ngayhoclai': 'datetime64[ns]', 'ngaybaoluu': 'datetime64[ns]'})
    # Create new columns: con_lai
    df['ngay_con_lai'] = df.ngayhoclai - df.today
    del df['today']
    # sort con_lai desc
    baoluu = df.sort_values("ngay_con_lai", ascending=True)
    # New column names
    baoluu.columns = ['hvbl_id', 'PĐk', 'Chi nhánh', 'Họ Tên', 'Ngày bảo lưu',
                      'Ngày học lại', 'Trạng thái', 'Lý do', 'Còn lại']
    # Change data type
    baoluu['Còn lại'] = baoluu['Còn lại'].dt.days

    # Create group ngày còn lại
    empty = []
    for value in baoluu['Còn lại']:
        if value >= 10:
            empty.append("Sẽ học lại")
        elif value < 10 and value >= 0:
            empty.append("Sắp học lại")
        elif value < 0:
            empty.append("Trễ học lại")
    baoluu['group ngày còn lại'] = empty
    baoluu = rename_lop(baoluu, 'Chi nhánh')
    # Group
    df = baoluu.pivot_table(values='hvbl_id', index='Chi nhánh',
                            columns='group ngày còn lại', aggfunc='count', margins=True)

    baoluu = baoluu.sort_values("Còn lại", ascending=False)
    baoluu = baoluu.reset_index(drop=True)

    # Tổng quan bảo lưu
    st.subheader("Tổng quan bảo lưu")
    st.dataframe(df.style.background_gradient(
    ).set_precision(0), use_container_width=True)
    # st.write(baoluu)
    fig = px.bar(baoluu, y='Họ Tên', x='Còn lại', text='Còn lại',
                 color='group ngày còn lại', color_discrete_map={'Sẽ học lại': 'green', 'Sắp học lại': 'orange', 'Trễ học lại': 'red'})
    fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
    fig.update_layout(uniformtext_minsize=8,
                      uniformtext_mode='hide', height=1500)
    df = baoluu.sort_values("Còn lại", ascending=True)[
        ['Chi nhánh', 'Họ Tên', 'Còn lại', 'Lý do', 'hvbl_id']]
    # st.plotly_chart(fig)
    "---"
    # left_column, right_column = st.columns(2)
    st.subheader("Ngày còn lại trước khi học lại")
    st.warning("Quét khối để zoom in, double click để trở lại")
    st.plotly_chart(fig, use_container_width=True)

    # Bảo lưu count --------------------------------------------------------------
    # Subset baoluu
    solan_baoluu = history.query("object == 'baoluu'")
    # Count baluu
    df1 = solan_baoluu.groupby('hv_id', as_index=False).object.count()
    # Subset giahan
    solan_giahan = history.query("object == 'giahan'")
    # Count gia han
    df2 = solan_giahan.groupby("hv_id", as_index=False).object.count()
    # Merge baoluu and giahan
    df = df1.merge(df2, on='hv_id', how='left')
    # Subset
    df = df[['hv_id', 'object_x', 'object_y']]
    # Fillna of giahan
    df.object_y.fillna(0, inplace=True)
    # Rename columns
    df.rename(columns={'object_x': 'Tổng bảo lưu',
              'object_y': 'Tổng gia hạn'}, inplace=True)
    # Add new column
    df['Tổng bảo lưu và gia hạn'] = df['Tổng bảo lưu'] + df['Tổng gia hạn']
    # Change data types
    df = df.astype(
        {'Tổng gia hạn': "int32", 'Tổng bảo lưu và gia hạn': 'int32'})
    # Assign to a variable
    baoluu_count = df.sort_values("Tổng bảo lưu và gia hạn", ascending=False)
    # subset hocvien baoluu
    hocvien_baoluu = hocvien.query("hv_status == 'hocvien'")[
        ['hv_id', 'hv_fullname', 'hv_coso', 'hv_link']]
    # Merge hocvien
    baoluu_count = baoluu_count.merge(hocvien_baoluu, on='hv_id', how='inner')

    df = baoluu.sort_values("Còn lại", ascending=True)\
        .merge(baoluu_count, left_on='hvbl_id', right_on='hv_id')
    st.subheader("Chi tiết bảo lưu")
    st.dataframe(
        df[['hvbl_id', 'Chi nhánh', 'Họ Tên', 'Còn lại',
            'Tổng bảo lưu', 'Tổng gia hạn', 'Lý do', 'hv_link']].set_index("hvbl_id"), use_container_width=True)
