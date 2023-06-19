import matplotlib.pyplot as plt
import requests
import pandas as pd
from datetime import date, timedelta
import streamlit as st
import plotly.express as px
import json
from pathlib import Path
import pickle
import streamlit_authenticator as stauth

page_title = "Kiểm soát lớp học"
page_icon = "🎮"
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

    @st.cache_data(ttl=timedelta(days=1))
    def collect_data(link):
        return (pd.DataFrame((requests.get(link).json())))

    @st.cache_data()
    def rename_lop(dataframe, column_name):
        dataframe[column_name] = dataframe[column_name].replace(
            {1: "Hoa Cúc", 2: "Gò Dầu", 3: "Lê Quang Định", 5: "Lê Hồng Phong"})
        return dataframe

    @st.cache_data()
    def exclude(dataframe, columns_name):
        return (dataframe.loc[:, ~dataframe.columns.isin(columns_name)])

    # @st.cache_data()
    # def grand_total(dataframe, column):
    #     # create a new row with the sum of each numerical column
    #     totals = dataframe.select_dtypes(include=[float, int]).sum()
    #     totals[column] = "Grand total"
    #     # append the new row to the dataframe
    #     dataframe = dataframe.append(totals, ignore_index=True)
    #     return dataframe

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

    def kh_ten_converter(dataframe):
        empty = []
        for ten in dataframe.kh_ten:  # Group kh_ten
            if "KÈM" in ten:
                empty.append("KHOÁ KÈM")
            else:
                empty.append("KHOÁ NHÓM")
        dataframe['group_kh_ten'] = empty
        return dataframe

    orders = collect_data(
        'https://vietop.tech/api/get_data/orders').query("deleted_at.isnull()")
    hocvien = collect_data(
        'https://vietop.tech/api/get_data/hocvien').query("hv_id != 737 and deleted_at.isna()")
    hocvien = get_link(hocvien)
    molop = collect_data('https://vietop.tech/api/get_data/molop')
    molop = exclude(molop, columns_name=['id', 'created_at', 'updated_at'])
    users = collect_data('https://vietop.tech/api/get_data/users')
    khoahoc = collect_data('https://vietop.tech/api/get_data/khoahoc')
    khoahoc = exclude(khoahoc, columns_name=['id', 'dahoc'])

    diemdanh_details = collect_data(
        'https://vietop.tech/api/get_data/diemdanh_details')
    diemdanh_details = diemdanh_details.query(
        "phanloai == 1")  # Filter lop chính
    # Get a response
    req = requests.get('https://vietop.tech/api/get_data/lophoc')
    req_json = req.json()  # Convert to list
    lophoc = pd.DataFrame(req_json)  # Convert to pandas dataframe

    def create_chart(type, dataframe, y_axis, x_axis, text):
        fig = type(dataframe, y=y_axis,
                   x=x_axis, text=text)
        # fig.update_xaxes(type='category')
        fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
        fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide',
                          height=4000,
                          width=400, yaxis_title="",
                          legend_title="")
        return fig

    # ------------------------------------------------------------ Tiền giờ của lớp
    lophoc_schedules = collect_data(
        'https://vietop.tech/api/get_data/lophoc_schedules')
    lophoc_schedules = lophoc_schedules[[
        'lop_id', 'teacher_id', 'active']].drop_duplicates("lop_id")
    # Merge lophoc and molop
    molop_orders = pd.merge(
        lophoc, molop[['lop_id', 'ketoan_id', 'molop_active']], on='lop_id', how='inner')
    # Merge orders
    molop_orders_lophoc = pd.merge(
        orders, molop_orders, on='ketoan_id', how='inner')
    # Query molop active
    final = molop_orders_lophoc.query('molop_active == 1')
    # Group by lop_id
    tiengiolop = final.groupby(["lop_id"], as_index=False).agg(
        {'ketoan_id': 'count', 'ketoan_tientrengio': 'sum'})
    # Merge back
    tiengiolop = tiengiolop.merge(molop_orders_lophoc, on='lop_id', how='left')
    tiengiolop = tiengiolop.drop_duplicates(subset='lop_id')
    # merge khoahoc
    tiengiolop = tiengiolop.merge(
        khoahoc, left_on='kh_id_x', right_on='kh_id', how='left')
    # Filter
    tiengiolop = tiengiolop.loc[:, ['created_at_x', 'lop_cahoc', 'kh_ten', 'lop_cn', 'lop_id', 'lop_ten', 'lop_thoigianhoc',
                                    'lop_type', 'lop_status', 'ketoan_id_x', 'ketoan_tientrengio_x']]
    tiengiolop = tiengiolop.merge(lophoc_schedules, on='lop_id')

    # Merge users
    tiengiolop = tiengiolop.merge(
        users[['id', 'fullname']], left_on='teacher_id', right_on='id')
    tiengiolop = tiengiolop.loc[:, ~
                                tiengiolop.columns.isin(['id', 'teacher_id'])]

    # Change columns name
    tiengiolop.columns = ['Ngày mở lớp', 'ca học', 'tên khoá học', 'chi nhánh', 'lớp id',
                          'tên lớp', 'lop_thoigianhoc', 'loại lớp', 'online/offline', 'ketoan_id_x', 'tiền giờ', 'active', 'giao_vien']

    # Mapping
    tiengiolop = rename_lop(tiengiolop, "chi nhánh")

    # Drop used columns
    tiengiolop.drop(['active', 'ketoan_id_x'], axis=1, inplace=True)
    # Convert to excel
    # tiengiolop.to_excel('Danh sách tiền giờ.xlsx', sheet_name='tiengio',engine="xlsxwriter", index=False)
    # st.text("tiengiocualop")
    # st.write(tiengiolop.shape)
    # st.write(tiengiolop)
    tiengio_giaovien = tiengiolop.groupby(
        'giao_vien', as_index=False)['tiền giờ'].sum()

    # ------------------------------------------------------------ Giờ còn lại của từng học viên

    # Group diemdanh by ketoan_id
    diemdanh_compact = orders.merge(diemdanh_details, on='ketoan_id', how='left').\
        groupby("ketoan_id", as_index=False).agg({'giohoc': 'sum'})

    # Merge hocvien, molop, lophoc, users and orders
    df = lophoc.query("(lop_status == 2 or lop_status == 4) and deleted_at.isnull()").\
        merge(molop, on="lop_id", how='inner').query("molop_active == 1").\
        merge(orders, on="ketoan_id").query("ketoan_active == 1").\
        merge(hocvien, left_on="hv_id_y", right_on='hv_id').\
        merge(diemdanh_compact, on='ketoan_id', how='left').\
        merge(khoahoc[['kh_id', 'kh_ten']],
              left_on='kh_id_x', right_on='kh_id', how='left')
    slice = ['hv_id', 'lop_id', 'kh_id_x', 'kh_ten', 'lop_type', 'lop_cn', 'hv_fullname', 'dauvao_overall',
             'remaining_time', 'giohoc', 'ketoan_tientrengio', 'hv_link']
    # Slice
    df = df[slice]
    df = kh_ten_converter(df)
    df['giờ còn lại'] = df['remaining_time'] - df['giohoc']
    # st.text("giờ còn lại từng học viên")
    # st.write(df)
    # st.write(df.shape)
    gioconlai = df

    # ------------------------------------------------------------ Tiền giờ tương lai
    # Merge
    df = tiengiolop.merge(gioconlai, left_on='lớp id', right_on='lop_id')
    df['gio_con_lai'] = df.remaining_time - df.giohoc
    df = df[['lop_id', 'tiền giờ', 'ketoan_tientrengio',
             'hv_fullname', 'gio_con_lai', 'group_kh_ten']]  # .query("lop_id == 40")
    tien_sap_het = []
    for index, row in df.iterrows():
        if row.gio_con_lai <= 20:
            tien_sap_het.append(row.ketoan_tientrengio)
        else:
            tien_sap_het.append(int(0))
    df['tien_sap_het'] = tien_sap_het
    df = df.groupby(['lop_id', 'group_kh_ten'],
                    as_index=False).tien_sap_het.sum()
    # Merge
    df = df.merge(tiengiolop, left_on='lop_id', right_on='lớp id')
    df['tiền giờ tương lai'] = df['tiền giờ'] - df['tien_sap_het']
    df = df[['lop_id', 'tiền giờ tương lai', 'group_kh_ten']]
    # df.to_excel('Tiền giờ tương lai.xlsx', sheet_name='tuonglai',
    #             engine="xlsxwriter", index=False)
    # df.shape
    # st.text("tien gio tuong lai")
    # st.write(df)

    # -------------------------------------------------- merge hiện tại và tương lai
    now_future = tiengiolop.merge(df, left_on='lớp id', right_on='lop_id')
    now_future['diff'] = now_future['tiền giờ'] - \
        now_future['tiền giờ tương lai']
    now_future['diff_percent'] = round((
        now_future['tiền giờ'] - now_future['tiền giờ tương lai']) / now_future['tiền giờ'] * 100, 0)
    now_future['lớp id'] = now_future['lớp id'].astype("str")
    now_future['lớp id'] = "Lớp " + now_future['lớp id']
    now_future = now_future.sort_values("diff_percent", ascending=True)

    # st.write(now_future)
    # st.write(now_future[['chi nhánh', 'lớp id', 'giáo viên2',
    #          'tiền giờ', 'tiền giờ tương lai', 'diff']])

    # Create a select box for phan loai
    with st.form(key='filter_form'):
        col1, col2 = st.columns(2)
        nhom_kem = col1.selectbox(
            label="Select loại lớp:", options=['KHOÁ NHÓM'])
        lop_id = col2.multiselect(label='Select lớp id', options=list(
            now_future.query("group_kh_ten == @nhom_kem")['lop_id'].unique()))
        submit_button = st.form_submit_button(
            label='Filter',  use_container_width=True)

    now_future = now_future.query("group_kh_ten == @nhom_kem")
    # -------------------------------------------------- merge hiện tại và tương lai và tiền giờ từng học viên
    df = now_future.merge(gioconlai, on='lop_id')
    df = df[['lop_id', 'ca học', 'giao_vien', 'hv_fullname',
             'ketoan_tientrengio', 'giờ còn lại']].query('lop_id == @lop_id')
    df = df.set_index("lop_id")
    ""
    st.dataframe(df, use_container_width=True)
    st.subheader(f"Tổng lớp đang học {now_future.shape[0]} lớp")
    # -------------------------------------------------- merge hiện tại và tương lai và tiền giờ từng học viên
    # Create figures
    fig1 = create_chart(px.bar, now_future, 'lớp id',
                        'tiền giờ tương lai', 'tiền giờ tương lai')
    fig2 = create_chart(px.bar, now_future, 'lớp id',
                        'tiền giờ', 'tiền giờ')
    fig3 = px.area(now_future, y="lớp id",
                   x="diff_percent", text='diff_percent')
    fig3.update_layout(
        height=4000,
        width=400, title="Chênh lệch %",
        xaxis_title="Tiền giờ hiện tại", yaxis_title="",
        legend_title="")
    fig3.update_traces(texttemplate='%{text:.2s}', textposition='top left')

    fig2.update_layout(title="Tiền giờ hiện tại",
                       xaxis_title="Tiền giờ hiện tại",)
    fig1.update_layout(title="Tiền giờ tương lai",
                       xaxis_title="Tiền giờ tương lai",)
    # fig3 = create_chart(px.area, now_future, 'lớp id', 'diff_percent', 'diff')
    # Reverse the y-axis
    fig2.update_xaxes(autorange="reversed")
    left_column, mid_column, right_column = st.columns(3)
    left_column.plotly_chart(fig2)
    mid_column.plotly_chart(fig3)
    right_column.plotly_chart(fig1)
