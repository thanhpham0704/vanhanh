import requests
import pandas as pd
from datetime import date, timedelta
import streamlit as st
import plotly.express as px
from pathlib import Path
import pickle
import streamlit_authenticator as stauth

page_title = "Chờ lớp"
page_icon = "⏰"
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

    # @st.cache_data()

    def rename_lop(dataframe, column_name):
        dataframe[column_name] = dataframe[column_name].replace(
            {1: "Hoa Cúc", 2: "Gò Dầu", 3: "Lê Quang Định", 5: "Lê Hồng Phong"})
        return dataframe

    # @st.cache_data()

    def exclude(dataframe, columns_name):
        return (dataframe.loc[:, ~dataframe.columns.isin(columns_name)])

    # @st.cache_data()

    def grand_total(dataframe, column):
        # create a new row with the sum of each numerical column
        totals = dataframe.select_dtypes(include=[float, int]).sum()
        totals[column] = "Grand total"
        # append the new row to the dataframe
        dataframe = dataframe.append(totals, ignore_index=True)
        return dataframe

    # @st.cache_data()

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
    molop = collect_data('https://vietop.tech/api/get_data/molop')
    molop = exclude(molop, columns_name=['id', 'created_at', 'updated_at'])
    users = collect_data('https://vietop.tech/api/get_data/users')
    khoahoc = collect_data('https://vietop.tech/api/get_data/khoahoc')
    khoahoc = exclude(khoahoc, columns_name=['id', 'dahoc'])

    # --------------------------------------------------------------Tổng chờ lớp
    # Chờ lớp
    orders_cholop = orders.query("ketoan_active == 0")
    # Lấy thông tin học viên cho ds chờ lớp
    df = orders_cholop.merge(hocvien, on='hv_id', how='left', suffixes=('_orders', '_hocvien'))[['created_at_orders', 'kh_id', 'hv_id', 'user_id', 'ketoan_id', 'hv_coso', 'hv_fullname',
                                                                                                'dauvao_overall', 'hv_muctieu_vt', 'hv_camket', 'lop_giovang',
                                                                                                 'ketoan_price', 'remaining_time', 'ketoan_sogio', 'ketoan_tientrengio', 'ketoan_details', 'hv_link']]
    # Merge users
    df = df.merge(users[['id', 'fullname']],
                  left_on='user_id', right_on='id', how='left')
    # Change column names
    df.columns = \
        ['Ngày tạo', 'kh_id', 'hv_id', 'tuvan_id', 'PĐK', 'Chi nhánh', 'Họ tên',
         'Đầu vào overall', 'Điểm tư vấn', 'cam kết', 'lop_giovang',
         'Học phí', 'Thực giờ', 'Tổng giờ khoá học', 'Tiền/giờ', 'Chi tiết', 'hv_link',
         'tuvan_id2', 'Tư vấn viên']
    # df = exclude(df, columns_name=['tuvan_id', 'tuvan_id2'])
    # Merge khoahoc
    df = df.merge(khoahoc[['kh_id', 'kh_ten']], on='kh_id', how='left')
    # Sort values
    df = df.sort_values("PĐK", ascending=False)
    # Create and inseart column Da thu
    df.insert(df.columns.get_loc("Học phí") + 1, 'Đã thu',
              round((df['Tiền/giờ'] * df['Thực giờ']), -5))
    # Assign df to new variable
    tongcholop = df
    # Merge molop
    df = df.merge(molop, on='hv_id', how='left')
    df = df.groupby(["hv_id", "PĐK"], as_index=False).count()
    # Filter dahoc
    chuahoc = df.query("lop_id == 0").sort_values("PĐK", ascending=False)
    # display(chuahoc.shape)
    # Filter chuahoc
    dahoc = df.query("lop_id > 0").sort_values("PĐK", ascending=False)
    # display(dahoc.shape)
    # Merge back to chuahoc
    df = tongcholop.merge(chuahoc[['hv_id', 'PĐK']], on='PĐK', how='left')
    # Define an empty list
    empty = []
    for index, row in df.iterrows():
        if row.hv_id_x == row.hv_id_y:
            empty.append('Chưa học')
        else:
            empty.append('Đã học')
    # Assign the list to a new column
    df['Phan_loai'] = empty
    df.drop('hv_id_y', axis=1, inplace=True)
    df.dropna(subset='Chi nhánh', inplace=True)
    # Assign to a variable
    tongcholop = df
    tongcholop.rename(columns={'hv_id_x': 'hv_id',
                               'Họ tên': 'fullname'}, inplace=True)

    # --------------------------------------------------------------PĐK 2
    # Dang hoc va baoluu
    orders_dahoc = orders.query("ketoan_active == 1 or ketoan_active == 4")
    # Merge hocvien
    hv_danghoc = orders_dahoc.merge(hocvien, on='hv_id', how='inner')
    # Filter
    pdk2 = dahoc[dahoc.hv_id.isin(hv_danghoc.hv_id)]
    # Merge back to tongcholop
    df = tongcholop.merge(pdk2[['hv_id', 'PĐK']], on='PĐK', how='left')
    empty = []
    for index, row in df.iterrows():
        if row['hv_id_x'] == row['hv_id_y']:
            empty.append('Có PĐK2')
        else:
            empty.append('Không có PĐK2')
    df['PDK2'] = empty
    df = df.fillna('')
    # Create mienphi
    df['free'] = ["free" if i == 0 else "not_free" for i in df['Tiền/giờ']]
    # Convert to date values

    df['Ngày tạo'] = pd.to_datetime(df['Ngày tạo'])

    df['Tháng tạo'] = df['Ngày tạo'].dt.month
    df['Năm tạo'] = df['Ngày tạo'].dt.year
    df['created_at'] = df['Ngày tạo'].dt.strftime('%m-%Y')
    df = rename_lop(df, 'Chi nhánh')
    # df = df.groupby(['Năm tạo', 'Tháng tạo', 'created_at',
    #                 'PDK2', 'Phan_loai', 'free'], as_index=False).size()
    # --------------------------------------------------------------Select box
    # Create a select box for phan loai
    phanloai = st.selectbox(
        label="Select phân loại:",
        options=["All"] + list(df["Phan_loai"].unique()),
        index=0)
    if phanloai == 'All':
        # --------------------------------------------------------------Bảng tổng hợp chờ lớp theo PĐK
        tonghop = df.groupby(
            ['Chi nhánh', 'PDK2'], as_index=False)['hv_id_x'].count()
        tonghop = grand_total(tonghop, 'Chi nhánh')
        tonghop = tonghop.rename(columns={'hv_id_x': 'Tổng học viên chờ lớp'})
        tonghop = tonghop.pivot_table(
            values='Tổng học viên chờ lớp',
            index='Chi nhánh',
            columns='PDK2',
            fill_value=0,
            margins=True,
            margins_name='Grand Total',
            aggfunc='sum'
        )

        # Create a table for visualization
        fig = df.groupby(['Năm tạo', 'Tháng tạo', 'created_at',
                          'PDK2'], as_index=False).size()
        fig = fig.sort_values(['Năm tạo', 'Tháng tạo'], ascending=True)

        fig = fig.rename(columns={'size': 'Số học viên'})
        fig = fig.set_index(["created_at"])
        # st.write(df)
        fig = px.bar(fig.reset_index(), x='Số học viên', y='created_at',
                     color='PDK2', text='Số học viên')
        fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
        fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide',
                          height=1000,
                          width=800)

        st.dataframe(tonghop.style.background_gradient().set_precision(0),
                     use_container_width=True)
        "---"
        # left_column, right_column = st.columns(2)
        st.subheader(
            f"Phân bổ học viên chờ lớp theo tháng {phanloai}")
        st.plotly_chart(fig, use_container_width=True)
        st.subheader(f"Chi tiết học viên {phanloai}")
        st.dataframe(df.loc[:, ['Ngày tạo', 'Chi nhánh', 'fullname', 'Đầu vào overall', 'Điểm tư vấn', 'cam kết', 'Học phí', 'Đã thu',
                                'Thực giờ', 'Tổng giờ khoá học', 'Tiền/giờ', 'Chi tiết', 'Tư vấn viên', 'kh_ten', 'Phan_loai', 'PDK2', 'free', 'hv_link']], use_container_width=True)
        import io
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            # Write each dataframe to a different worksheet.
            df.loc[:, ['Ngày tạo', 'Chi nhánh', 'fullname', 'Đầu vào overall', 'Điểm tư vấn', 'cam kết', 'Học phí', 'Đã thu',
                       'Thực giờ', 'Tổng giờ khoá học', 'Tiền/giờ', 'Chi tiết', 'Tư vấn viên', 'kh_ten', 'Phan_loai', 'PDK2', 'free', 'hv_link']].to_excel(writer, sheet_name='Sheet1')
            # Close the Pandas Excel writer and output the Excel file to the buffer
            writer.save()
            st.download_button(
                label=f"Chi tiết học viên {phanloai}",
                data=buffer,
                file_name="hocvien_cholop_details.xlsx",
                mime="application/vnd.ms-excel"
            )
    else:
        df = df.query("Phan_loai == @phanloai")
        tonghop = df.groupby(
            ['Chi nhánh', 'PDK2'], as_index=False)['hv_id_x'].count()
        tonghop = grand_total(tonghop, 'Chi nhánh')
        tonghop = rename_lop(tonghop, 'Chi nhánh')
        # tonghop = tonghop.set_index("Chi nhánh")
        tonghop = tonghop.rename(columns={'hv_id_x': 'Tổng học viên chờ lớp'})
        tonghop = tonghop.pivot_table(
            values='Tổng học viên chờ lớp',
            index='Chi nhánh',
            columns='PDK2',
            fill_value=0,
            margins=True,
            margins_name='Grand Total',
            aggfunc='sum'
        )

        # Create a table for visualization
        fig = df.groupby(['Năm tạo', 'Tháng tạo', 'created_at',
                          'PDK2'], as_index=False).size()
        fig = fig.sort_values(['Năm tạo', 'Tháng tạo'], ascending=True)

        fig = fig.rename(columns={'size': 'Số học viên'})
        fig = fig.set_index(["created_at"])
        # st.write(df)
        fig = px.bar(fig.reset_index(), x='Số học viên', y='created_at',
                     color='PDK2', text='Số học viên')
        fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
        fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide',
                          height=1000,
                          width=800)

        st.dataframe(tonghop.style.background_gradient().set_precision(0),
                     use_container_width=True)
        # left_column, right_column = st.columns([2, 1])
        st.subheader(
            f"Phân bổ học viên chờ lớp theo tháng {phanloai}")
        st.plotly_chart(fig)
        st.subheader(f"Chi tiết học viên {phanloai}")
        st.dataframe(df.loc[:, ['Ngày tạo', 'Chi nhánh', 'fullname', 'Đầu vào overall', 'Điểm tư vấn', 'cam kết', 'Học phí', 'Đã thu',
                                'Thực giờ', 'Tổng giờ khoá học', 'Tiền/giờ', 'Chi tiết', 'Tư vấn viên', 'kh_ten', 'Phan_loai', 'PDK2', 'free', 'hv_link']], use_container_width=True)
        import io
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            # Write each dataframe to a different worksheet.
            df.loc[:, ['Ngày tạo', 'Chi nhánh', 'fullname', 'Đầu vào overall', 'Điểm tư vấn', 'cam kết', 'Học phí', 'Đã thu',
                       'Thực giờ', 'Tổng giờ khoá học', 'Tiền/giờ', 'Chi tiết', 'Tư vấn viên', 'kh_ten', 'Phan_loai', 'PDK2', 'free', 'hv_link']].to_excel(writer, sheet_name='Sheet1')
            # Close the Pandas Excel writer and output the Excel file to the buffer
            writer.save()
            st.download_button(
                label=f"Chi tiết học viên {phanloai}",
                data=buffer,
                file_name="hocvien_cholop_details.xlsx",
                mime="application/vnd.ms-excel"
            )
