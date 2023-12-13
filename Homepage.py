import streamlit as st
import requests
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import pickle
import streamlit_authenticator as stauth
import numpy as np
import calendar
import gspread
# %%
# Configure landing page
page_title = "Lương và thực thu"
page_icon = ":chart_with_upwards_trend:"
layout = "wide"

st.set_page_config(page_title=page_title, page_icon=page_icon, layout=layout)
names = ["Phạm Tấn Thành", "Phạm Minh Tâm", "Vận hành", "Kinh doanh"]
usernames = ["thanhpham", "tampham", "vietopvanhanh", 'vietopkinhdoanh']


# Load hashed password
file_path = Path(__file__).parent / 'hashed_pw.pkl'
with file_path.open("rb") as file:
    hashed_passwords = pickle.load(file)

authenticator = stauth.Authenticate(names, usernames, hashed_passwords,
                                    "sales_dashboard", "abcdef", cookie_expiry_days=1)

name, authentication_status, username = authenticator.login("Login", "main")

if authentication_status == False:
    st.error("Username/password is incorrect")

if authentication_status == None:
    st.warning("Please enter your username and password")

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

    # if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = authentication_status
    # if 'authenticator' not in st.session_state:
    st.session_state['authenticator'] = authenticator
    # %% Function and API

    @st.cache_data(ttl=timedelta(days=1))
    def collect_data(link):
        return (pd.DataFrame((requests.get(link).json())))

    @st.cache_data(ttl=timedelta(days=1))
    def collect_filtered_data(table, date_column='', start_time='', end_time=''):
        link = f"https://vietop.tech/api/get_data/{table}?column={date_column}&date_start={start_time}&date_end={end_time}"
        df = pd.DataFrame((requests.get(link).json()))
        df[date_column] = pd.to_datetime(df[date_column])
        return df

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

    @st.cache_data()
    def thucthu_time(dataframe, column):
        df = dataframe.groupby(['lop_cn', column], as_index=False)[
            'price'].sum()
        df.lop_cn = df.lop_cn.replace(
            {1: "Hoa Cúc", 2: "Gò Dầu", 3: "Lê Quang Định", 5: "Lê Hồng Phong"})
        return df

    @st.cache_data()
    def plotly_chart(df, yvalue, xvalue, text, title, y_title, x_title, color=None, discrete_sequence=None, map=None):
        fig = px.bar(df, y=yvalue,
                     x=xvalue, text=text, color=color, color_discrete_sequence=discrete_sequence, color_discrete_map=map)
        fig.update_layout(
            title=title,
            yaxis_title=y_title,
            xaxis_title=x_title,
        )
        fig.update_traces(textposition='auto')
        return fig

    def distribution(df, col, value_name):
        df['1'] = 0.26 * df[col]
        df['2'] = 0.26 * df[col]
        df['3'] = 0.18 * df[col]
        df['5'] = 0.30 * df[col]
        # Subset
        df = df.loc[:, [
            'id_gg', 'Họ và tên', '1', '2', '3', '5']]
        # Lương đào tạo sau khi phân phối
        df = pd.melt(df, id_vars=[
            'id_gg', 'Họ và tên'], var_name='lop_cn', value_name=value_name)
        df['lop_cn'] = df['lop_cn'].astype(
            'int64')
        return df

    orders = collect_data(
        'https://vietop.tech/api/get_data/orders').query("deleted_at.isnull()")
    diemdanh_details = collect_data(
        'https://vietop.tech/api/get_data/diemdanh_details')
    hocvien = collect_data(
        'https://vietop.tech/api/get_data/hocvien').query("hv_id != 737 and deleted_at.isnull()")
    # Mapping hv_camket
    conditions = [hocvien['hv_camket'] == 0, hocvien['hv_camket'] == 1, hocvien['hv_camket'] == 2,
                  hocvien['hv_camket'] == 3, hocvien['hv_camket'] == 4]
    choices = ["Không cam kết", "Cam kết tiêu chuẩn",
               "Huỷ hợp đồng 1", "Huỷ hợp đồng 2", "Cam kết thi thật"]
    hocvien['hv_camket'] = np.select(conditions, choices)
    leads = collect_data(
        'https://vietop.tech/api/get_data/leads')
    leads_test = leads.query("tele_status == 'dathen'")
    leads_test = leads_test[leads_test['coso_status'].isin(
        ['testchuahoc', 'dangkyhoc', 'khonghoc', 'thithu', 'thamkhao'])]
    users = collect_data(
        'https://vietop.tech/api/get_data/users')
    diemthi_meta = collect_data(
        'https://vietop.tech/api/get_data/diemthi_meta')
    diemthi_meta = diemthi_meta[['diemthi_id', 'user_id']]
    diemthi = collect_data('https://vietop.tech/api/get_data/diemthi')
    hv_status = collect_data('https://vietop.tech/api/get_data/hv_status')
    lophoc = collect_data('https://vietop.tech/api/get_data/lophoc')

    # %%
    # Date filter
    now = datetime.now()
    DEFAULT_START_DATE = datetime(now.year, now.month, 1)
    DEFAULT_END_DATE = datetime(now.year, now.month, 1) + timedelta(days=32)
    DEFAULT_END_DATE = DEFAULT_END_DATE.replace(day=1) - timedelta(days=1)

    # Create a form to get the date range filters
    with st.sidebar.form(key='date_filter_form'):
        # col1, col2 = st.columns(2)
        ketoan_start_time = st.date_input(
            "Select start date", value=DEFAULT_START_DATE)
        ketoan_end_time = st.date_input(
            "Select end date", value=DEFAULT_END_DATE)
        submit_button = st.form_submit_button(
            label='Filter',  use_container_width=True)

    # the duration between 2 dates exclude Sunday
    duration = sum(1 for i in range((ketoan_end_time - ketoan_start_time).days + 1)
                   if (ketoan_start_time + timedelta(i)).weekday() != 6)
    # the number of days in a month exclude Sunday
    days_in_month = calendar.monthrange(
        ketoan_start_time.year, ketoan_start_time.month)[1]
    sundays_in_month = sum(1 for day in range(1, days_in_month + 1) if datetime(
        ketoan_start_time.year, ketoan_start_time.month, day).weekday() == 6)
    days_excluding_sundays = days_in_month - sundays_in_month

    # %%
    # Thưởng đạt điểm
    diemthi['created_at'] = pd.to_datetime(diemthi['created_at'])
    # Extract date portion from datetime values
    diemthi['created_at'] = diemthi['created_at'].dt.date
    diemthi_thuong = diemthi[['id', 'hv_id', 'date', 'created_at', 'target', 'diemcandat',
                              'overall', 'type']]\
        .query("created_at >= @ketoan_start_time and created_at <= @ketoan_end_time and (type == 2 or type == 13)")\
        .merge(diemthi_meta, left_on='id', right_on='diemthi_id', how='inner')\
        .merge(users[['fullname', 'id']], left_on='user_id', right_on='id')\
        .merge(hocvien[['hv_id', 'hv_fullname', 'hv_camket', 'diem_camket']], on='hv_id')\
        .sort_values(['created_at'], ascending=True)\
        .drop_duplicates(['hv_id', 'user_id'])
    diemthi_thuong.fillna(0, inplace=True)
    diemthi_thuong.diem_camket = diemthi_thuong.diem_camket.astype("float64")

    try:
        diemthi_thuong.diem_camket = diemthi_thuong.diem_camket.astype(
            "float64")
    except ValueError as e:
        # Extract the problematic value from the error message
        error_value = str(e).split(":")[-1].strip()
        st.warning(f"Có dấu {error_value} trong điểm cam kết")
    # Merge hocvien to get dauvao_overall
    diemthi_thuong = diemthi_thuong.merge(
        hocvien[['hv_id', 'dauvao_overall', 'hv_coso']], on='hv_id')
    diemthi_thuong['thuong_datdiem'] = 0
    # Function to update status based on score and benchmark

    def update_status(row):
        if row['type'] == 2:
            if row['hv_camket'] == 'Cam kết thi thật':
                score_diff = row['overall'] - row['diem_camket']
                status_increase = int(score_diff / 0.5) * 200000
                new_status = row['thuong_datdiem'] + status_increase + 650000
                return max(new_status, 0)  # Ensuring status is not negative
            else:
                score_diff = row['overall'] - row['dauvao_overall']
                status_increase = int(score_diff / 0.5) * 200000
                new_status = row['thuong_datdiem'] + status_increase
                return max(new_status, 0)  # Ensuring status is not negative
        else:
            return row['thuong_datdiem']

    # Apply the update_status function to the dataframe
    diemthi_thuong['thuong_datdiem'] = diemthi_thuong.apply(
        update_status, axis=1)
    diemthi_thuong['thuong_datdiem'] = diemthi_thuong['thuong_datdiem'].fillna(
        0)
    gv_count = diemthi_thuong.sort_values("hv_fullname")\
        .groupby(['hv_id'], as_index=False).size()

    diemthi_thuong_details = diemthi_thuong.merge(gv_count, on='hv_id')

    diemthi_thuong_details['divided_thuong_datdiem'] = diemthi_thuong_details['thuong_datdiem'] / \
        diemthi_thuong_details['size']

    diemthi_thuong_details.drop(
        ['id_x', 'user_id', 'id_y', 'size', 'hv_id', 'diemthi_id'], axis=1, inplace=True)
    diemthi_thuong_details = diemthi_thuong_details.reindex(
        columns=['date', 'created_at', 'fullname', 'hv_fullname', 'hv_coso', 'hv_camket', 'type', 'divided_thuong_datdiem', 'dauvao_overall',  'diem_camket', 'overall'])
    # Mapping
    Subjects = {1: "TĐK - Foundation 1", 2: "Thi thật", 3: "Test lại sau bảo lưu", 4: "TĐK - Foundation 2",
                5: "TĐK - 3.5", 6: "TĐK - 4.0", 7:  "TĐK - 4.5", 8: "TĐLK - 5.0", 9: "TĐK - 5.5", 10: "TĐk - 6.0",
                11: "TĐK - 6.0+", 12: "TĐK - 6.5", 13: "Thi cuối khoá"}
    # Add new columns
    diemthi_thuong_details.loc[:, ("type")
                               ] = diemthi_thuong_details.loc[:, ("type")].map(Subjects)
    diemthi_thuong_group = diemthi_thuong_details.groupby(
        'fullname', as_index=False)['divided_thuong_datdiem'].sum()
    reward_datdiem = diemthi_thuong_group.merge(
        users[['fullname', 'id']], on='fullname').sort_values("divided_thuong_datdiem", ascending=False)
    reward_datdiem['divided_thuong_datdiem'] = round(
        reward_datdiem['divided_thuong_datdiem'], 0)

    # For cac loai chi phi
    total_datdiem = diemthi_thuong_details.groupby('hv_coso', as_index=False)[
        'divided_thuong_datdiem'].sum()
    total_datdiem = rename_lop(total_datdiem, 'hv_coso')

    # %%
    # Thưởng test đầu vào
    # Subset orders
    orders_subset = orders[['hv_id', 'ketoan_price', 'ketoan_tientrengio', 'remaining_time']]\
        .drop_duplicates(subset='hv_id', keep='last')
    orders_subset['tiendadong'] = orders_subset['ketoan_tientrengio'] * \
        orders_subset['remaining_time']
    # Subset and merge leads
    chuyendoi = hocvien[['hv_id', 'hv_fullname', 'user_test', 'user_id', 'hv_coso', 'hv_ngayhoc', 'hv_catest']][hocvien.user_test.notnull()]\
        .merge(leads_test[['hv_id', 'coso_ngaytest', 'lead_test']], on='hv_id', how='left')
    # Convert coso_ngaytest to datetime64[ns]
    chuyendoi['coso_ngaytest'] = chuyendoi['coso_ngaytest'].astype(
        'datetime64[ns]')
    # Convert coso_ngaytest to datetime64[ns]
    chuyendoi['hv_ngayhoc'] = chuyendoi['hv_ngayhoc'].astype('datetime64[ns]')
    # Remove NAN value
    chuyendoi = chuyendoi[~chuyendoi.coso_ngaytest.isna()]
    # Merge users to get gv_fullname
    chuyendoi = chuyendoi.merge(
        users[['id', 'fullname']], left_on='user_test', right_on='id', how='left')
    # Convert datetime to month
    chuyendoi['coso_ngaytest_month'] = chuyendoi['coso_ngaytest'].dt.month
    # Convert datetime to month
    chuyendoi['hv_ngayhoc_month'] = chuyendoi['hv_ngayhoc'].dt.month
    # Total test by month
    test = pd.DataFrame(chuyendoi.groupby(['coso_ngaytest_month', 'user_test', 'fullname'], as_index=True)
                        .size().reset_index(name='test'))

    # Total enrol by month
    enrol = pd.DataFrame(chuyendoi.groupby(['coso_ngaytest_month', 'user_test', 'fullname'], as_index=True)
                         .hv_ngayhoc.count().reset_index(name='enrol'))

    # Merge test and enrol
    test_enrol = test.merge(enrol[['user_test', 'coso_ngaytest_month', 'enrol']], on=[
                            'user_test', 'coso_ngaytest_month'])

    test_enrol['conversion_rate'] = round(
        test_enrol['enrol'] / test_enrol['test'] * 100)
    # Merge orders_subset
    conversion = chuyendoi.merge(
        orders_subset, on='hv_id', how='left', validate='one_to_many')
    # remove phong dao tao and mr bot and null
    conversion = conversion[conversion.fullname.notnull() &
                            ~conversion.user_test.isin([2, 106])]
    # Convert datetime to date
    conversion['coso_ngaytest'] = conversion['coso_ngaytest'].dt.date.astype(
        "datetime64[ns]")

    conversion['hv_ngayhoc'] = conversion['hv_ngayhoc'].astype(
        "datetime64[ns]")
    # Đóng tiền trong ngày
    empty = []
    for index, row in conversion.iterrows():
        if row['hv_ngayhoc'] == row['coso_ngaytest']:
            empty.append("Chốt nóng")
        elif row['hv_ngayhoc'] < row['coso_ngaytest'] + pd.Timedelta(31, 'D'):
            empty.append(
                "Chốt sau")
        else:
            empty.append("Mất deal")

    # Assign new column
    conversion['chot_sale'] = empty
    conversion.fillna(0, inplace=True)

    conversion[['hv_ngayhoc']] = conversion[[
        'hv_ngayhoc']].replace({0: '1999-02-02'})
    # Convert 'hv_ngayhoc' column to pandas DatetimeIndex
    conversion['hv_ngayhoc'] = pd.to_datetime(conversion['hv_ngayhoc'])
    conversion['hv_ngayhoc'] = conversion['hv_ngayhoc'].dt.date
    conversion['coso_ngaytest'] = conversion['coso_ngaytest'].dt.date
    # Test
    conversion_test = conversion \
        .query("(coso_ngaytest >= @ketoan_start_time) and coso_ngaytest <= @ketoan_end_time") \
        .groupby(['user_test', 'fullname', 'hv_ngayhoc', 'coso_ngaytest', 'hv_coso', 'id'], as_index=False).size()
    # Enrol
    conversion_enrol = conversion \
        .query("hv_ngayhoc >= @ketoan_start_time \
            and hv_ngayhoc <= @ketoan_end_time \
            and coso_ngaytest <= @ketoan_end_time") \
        .groupby(['user_test', 'fullname', 'hv_ngayhoc', 'coso_ngaytest', 'hv_coso', 'id'], as_index=False).size()
    conversion_test['status'] = 'test'
    conversion_enrol['status'] = 'enrol'
    total_conversion = pd.concat([conversion_test, conversion_enrol])

    # Filter less then 31 days
    total_conversion = total_conversion[total_conversion['hv_ngayhoc']
                                        <= total_conversion['coso_ngaytest'] + pd.Timedelta(31, 'D')]
    # Groupby fullname and status
    total_conversion = total_conversion.groupby(
        ['id', 'fullname', 'hv_coso', 'status'], as_index=False)['size'].sum()
    total_conversion['thuong'] = total_conversion['size'] * 50000

    # total_conversion.thuong_test.sum()
    total_conversion_pivot = total_conversion.pivot_table(values=['size', 'thuong'], index=['fullname', 'id', 'hv_coso'],
                                                          columns='status', margins=False, fill_value=0).reset_index()
    # Rename the columns
    total_conversion_pivot.columns = ['_'.join(col).strip(
    ) if col[1] else col[0] for col in total_conversion_pivot.columns]

    total_conversion_pivot['thuong_test_enrol'] = total_conversion_pivot['thuong_enrol'] + \
        total_conversion_pivot['thuong_test']

    reward_test_enrol = total_conversion_pivot.merge(
        users[['fullname', 'id']], on='fullname')
    reward_test_enrol_total = grand_total(reward_test_enrol, 'fullname')

    # ------------------------------------------------------------------------------------------------------------------------
    # Create hv_leads
    hv_leads = hocvien[['hv_id', 'hv_fullname']].merge(
        leads[['hv_id', 'coso_ngaytest']], on='hv_id')
    hv_leads['coso_ngaytest'] = hv_leads['coso_ngaytest'].astype(
        "datetime64[ns]")
    hv_leads['coso_ngaytest'] = pd.to_datetime(
        hv_leads['coso_ngaytest']).dt.date
    df = conversion.merge(hv_leads, on=[
        'hv_fullname', 'coso_ngaytest'],  how='left')
    df = df.merge(users[['id', 'fullname']],
                  left_on='user_id', right_on='id', how='left')
    df = rename_lop(df, 'hv_coso')
    df = df.query(
        "(coso_ngaytest >= @ketoan_start_time) and coso_ngaytest <= @ketoan_end_time")
    df = df[['id_x', 'fullname_x', 'hv_fullname', 'fullname_y', 'hv_coso', 'coso_ngaytest',
             'hv_ngayhoc', 'hv_catest', 'lead_test', 'tiendadong', 'chot_sale']]
    conversion = df.rename(columns={'fullname_x': 'gv_fullname',
                                    'fullname_y': 'ec_fullname'})
    conversion = conversion.query(
        "(coso_ngaytest >= @ketoan_start_time) and coso_ngaytest <= @ketoan_end_time")

    total_reward = total_conversion.groupby(
        ['hv_coso'], as_index=False)['thuong'].sum()
    total_reward = rename_lop(total_reward, 'hv_coso')

    # %%
    # Main dashboard
    # "---------------" Thông tin lương giáo viên
    sa = gspread.service_account(
        filename='taichinh-380507-b8f84e9ee681.json')
    sh = sa.open("Nhân sự")
    worksheet = sh.worksheet("Giáo viên")
    salary = pd.DataFrame(worksheet.get_all_records())
    salary = salary.replace("", np.nan).dropna(subset='id_gg')
    salary = salary.replace('\.', '', regex=True)
    salary = salary.astype({'Lương theo hợp đông': 'float', 'Thâm niên': 'float',
                           'Chức danh': "float", 'Tổng lương': 'float', 'date_affected': 'datetime64[ns]'})
    # salary.info()
    # salary = salary.sort_values("date_affected", ascending=False)\
    #     .drop_duplicates(subset='id_gg')
    salary = salary.sort_values("date_affected", ascending=False)\
        .query("date_affected <= @ketoan_end_time")\
        .drop_duplicates("id_gg")
    salary.fillna(0, inplace=True)
    # Thong tin luong
    salary['salary_ngay_cong'] = round(
        salary['Tổng lương'] * duration/days_excluding_sundays, 0)
    salary.fillna(0, inplace=True)
    salary.drop(['STT', 'Mã giáo viên', 'Tổng lương'], axis=1, inplace=True)
    salary.rename(columns={"Lương theo hợp đông": "hopdong", "Thâm niên": "thamnien",
                           'Chức danh': 'chucdanh', 'Ngày': 'ngay', 'Tối': 'toi', 'Cuối tuần': 'cuoituan',
                           'Trợ giảng': 'trogiang', 'BHXH': 'bhxh', 'Chế độ': 'working_status', 'Bậc giáo viên': 'level', 'Tổng ngày nghỉ phép': 'ngaynghi_total',
                           'Tổng ngày công thực tế': 'ngaycong_real_total'}, inplace=True)

    # "------------------"
    gv_diemdanh = collect_filtered_data(
        table='diemdanh', date_column='date_created', start_time=ketoan_start_time, end_time=ketoan_end_time)
    gv_diemdanh['date_created'] = pd.to_datetime(gv_diemdanh['date_created'])

    sh = sa.open("Nhân sự")
    worksheet = sh.worksheet("Overtime")
    offline_overtime = pd.DataFrame(worksheet.get_all_records())
    offline_overtime['date_affected'] = pd.to_datetime(
        offline_overtime['date_affected'])
    offline_overtime['date_affected'] = offline_overtime['date_affected'].dt.date

    offline_overtime = offline_overtime.query(
        "date_affected <= @ketoan_end_time")
    offline_overtime = offline_overtime.sort_values("date_affected", ascending=False)\
        .drop_duplicates(subset='Họ và tên')
    offline_overtime.drop("date_affected", axis=1, inplace=True)

    # Define the start and end times of the day
    start_time = pd.to_datetime('2000-01-01 06:00:00').time()
    end_time = pd.to_datetime('2000-01-01 18:00:00').time()
    ca1 = pd.to_datetime('2000-01-01 06:30:00').time()
    ca2 = pd.to_datetime('2000-01-01 10:30:00').time()
    ca3 = pd.to_datetime('2000-01-01 13:30:00').time()
    ca4 = pd.to_datetime('2000-01-01 15:30:00').time()
    ca5 = pd.to_datetime('2000-01-01 18:00:00').time()
    # tren office khong cos 19:45
    ca6 = pd.to_datetime('2000-01-01 19:30:00').time()
    # Create a function that takes a time and returns "Morning" or "Evening" depending on whether the time falls within the specified range

    @st.cache_data()
    def time_of_day(time):
        if (time >= start_time) & (time < end_time):
            return "Sáng"
        else:
            return "Tối"
    # Create a function that takes a time and returns "Morning" or "Evening" depending on whether the time falls within the specified range

    @st.cache_data()
    def day_of_week(day):
        if (day == 5) | (day == 6):
            return "weekend"
        else:
            return "weekdays"
    # Create a function that takes a time and returns "Morning" or "Evening" depending on whether the time falls within the specified range

    @st.cache_data()
    def cahoc_converter(ca):
        if (ca >= ca1) & (ca < ca2):
            return 1
        elif (ca >= ca2) & (ca < ca3):
            return 2
        elif (ca >= ca3) & (ca < ca4):
            return 3
        elif (ca >= ca4) & (ca < ca5):
            return 4
        elif (ca >= ca5) & (ca < ca6):
            return 5
        elif (ca >= ca6):
            return 6

    # "---------------" Bảng lương giáo viên

    overtime_melt = offline_overtime.melt(
        id_vars=['id_gg', 'Họ và tên', 'WORKING_STATUS'], var_name='Column Name', value_name='overtime_status')
    overtime_melt['day_of_week'], overtime_melt['cahoc'] = overtime_melt['Column Name'].str.split(
        'Ca ', 1).str
    overtime_melt['day_of_week'].replace(
        {'T2': 0, 'T3': 1, 'T4': 2, 'T5': 3, 'T6': 4, 'T7': 5, 'T8': 6}, inplace=True)
    overtime_melt['overtime_status'].replace(
        {0: 'in', 'a': 'out'}, inplace=True)
    # Convert 5 and 6 into "Cuối tuần"
    overtime_melt['weekend_or_not'] = overtime_melt['day_of_week'].apply(
        day_of_week)
    # Convert ca into Sáng or Tối
    overtime_melt['time_of_day'] = ['Sáng' if i in [
        '1', '2', '3', '4'] else 'Tối' for i in overtime_melt['cahoc']]
    # Drop unnecessary columns
    overtime_melt.drop(
        ['Column Name'], axis=1, inplace=True)
    overtime_melt['cahoc'] = overtime_melt['cahoc'].astype(int)
    overtime_melt.rename(
        columns={'WORKING_STATUS': 'working_status'}, inplace=True)

    # "---------------" Lương overtime của giáo viên

    diemdanh = gv_diemdanh.merge(users[['fullname', 'id']], left_on='giaovien', right_on='id', how='inner')\
        .sort_values("created_at", ascending=False)
    # diemdanh['cahoc'].replace({0: 'không học', 1: 'ca1', 2: 'ca2', 3: 'ca3', 4:'ca4', 5:'ca5', 6:'ca6', 7:'ca 1.5 giờ', 8: 'ca 2.5 giờ', 9: 'ca 3.0 giờ', 10: 'ca 1 giờ', 11: 'ca 1.75 giờ', 12: 'ca 2 giờ'}, inplace = True)
    diemdanh = diemdanh[['lop_id', 'sogio', 'cahoc', 'phanloai',
                        'date_created', 'created_by', 'id',
                         'updated_by', 'created_at', 'fullname']]
    # Convert the date column to datetime
    diemdanh['created_at'] = pd.to_datetime(diemdanh['created_at'])
    # Extract the time component of each datetime value
    diemdanh['created_at_time'] = diemdanh['created_at'].dt.time
    # Create a new column that indicates the day of the week
    diemdanh['day_of_week'] = diemdanh['created_at'].dt.dayofweek
    # Create a boolean mask that indicates whether each time is within the specified time frame
    diemdanh["time_of_day"] = diemdanh['created_at_time'].apply(time_of_day)
    # Convert 5 and 6 into "Cuối tuần"
    diemdanh['weekend_or_not'] = diemdanh["day_of_week"].apply(day_of_week)
    diemdanh = diemdanh[['id', 'fullname', 'sogio', 'cahoc', 'phanloai',
                        'created_at', 'day_of_week', 'created_at_time', 'time_of_day', 'weekend_or_not', 'date_created',
                         'lop_id']]
    diemdanh['cahoc'] = diemdanh['created_at_time'].apply(cahoc_converter)
    # Sum giohoc according to fullname, time of day and weekend or not
    diemdanh_sum_giohoc = diemdanh.groupby(
        ["id", "fullname", "cahoc", 'phanloai', 'day_of_week', "time_of_day", "weekend_or_not", 'lop_id'], as_index=False)['sogio'].sum()
    # Get lopcn from lophoc
    diemdanh_lop_cn = diemdanh_sum_giohoc.merge(
        lophoc[['lop_id', 'lop_cn']], on='lop_id')

    # "---------------"
    sal_diem = diemdanh_lop_cn.merge(
        salary, left_on='id', right_on='id_gg', how='outer')
    # Merge diemdanh and overtime
    sal_diem_over = sal_diem\
        .merge(overtime_melt, on=['id_gg', 'Họ và tên', 'cahoc', 'day_of_week', 'time_of_day', 'weekend_or_not'], how='outer', validate='many_to_many')
    # Drop duplicates
    sal_diem_over.drop_duplicates(inplace=True)
    # Fill na
    sal_diem_over.fillna(0, inplace=True)
    # Calculate luong ngay cong
    empty = []
    for index, value in sal_diem_over.iterrows():
        if value['weekend_or_not'] == 'weekend' and value['overtime_status'] == 'out':
            empty.append(value['cuoituan'] * value['sogio'])
        elif value['time_of_day'] == 'Tối' and value['overtime_status'] == 'out':
            empty.append(value['toi'] * value['sogio'])
        elif value['time_of_day'] == 'Sáng' and value['overtime_status'] == 'out':
            empty.append(value['ngay'] * value['sogio'])
        elif value['phanloai'] == 0:
            empty.append(value['trogiang'] * value['sogio'])
        else:
            empty.append(0)
    sal_diem_over['salary_gio_cong'] = empty

    # Slicing columns
    sal_diem_over = sal_diem_over.loc[:, ['lop_cn', 'id_gg', 'Họ và tên', 'working_status_x', 'cahoc', 'phanloai', 'overtime_status',
                                          'time_of_day', 'day_of_week', 'weekend_or_not', 'sogio',
                                          'ngay', 'toi', 'cuoituan', 'trogiang', 'salary_gio_cong', 'salary_ngay_cong']]
    sal_diem_over_group_lop = sal_diem_over.groupby(['id_gg', 'Họ và tên', 'lop_cn', 'working_status_x', 'overtime_status', 'salary_ngay_cong'], as_index=False)['sogio', 'salary_gio_cong'].sum()\
        .query("overtime_status == 'out'")
    # Sum luong_gio_cong according to fullname
    sal_diem_over_group = sal_diem_over.groupby(['id_gg', 'Họ và tên', 'working_status_x', 'overtime_status', 'salary_ngay_cong'], as_index=False)['sogio', 'salary_gio_cong'].sum()\
        .query("overtime_status == 'out'").sort_values("salary_gio_cong", ascending=False)
    sal_diem_over_details = sal_diem_over.drop('salary_ngay_cong', axis=1)\
        .query("overtime_status == 'out'")

    # ----------------------# Phân phối lương cứng theo chi nhánh
    df = sal_diem_over.groupby(['lop_cn', 'id_gg', 'Họ và tên', 'working_status_x', 'overtime_status',
                                'salary_ngay_cong'], as_index=False)['sogio', 'salary_gio_cong'].sum()
    df = df.query('overtime_status != "out"')
    df_sum = df.groupby('id_gg', as_index=False)['sogio'].sum()
    df_proportion = df_sum.merge(df, on='id_gg')
    df_proportion['proportion_sogio'] = df_proportion['sogio_y'] / \
        df_proportion['sogio_x']
    # Fillna value with 1 incase 0 divided by 0
    df_proportion['proportion_sogio'] = df_proportion['proportion_sogio'].fillna(
        1)
    df_proportion['salary_ngay_cong_divided'] = df_proportion['proportion_sogio'] * \
        df_proportion['salary_ngay_cong']
    # Giáo viên ngoại trừ phòng đào tạo
    daotao = ['Mai Minh Trung', 'Trần Thị Thanh Nga', 'Nguyễn Thị Thu Hà',
              'Huỳnh Trương Hồng Châu Long', 'Nguyễn Huy Hoàng', 'Nguyễn Quang Huy']
    df_proportion_nodaotao = df_proportion[~df_proportion['Họ và tên'].isin(
        daotao)]

    # Subset
    df_proportion_nodaotao = df_proportion_nodaotao[[
        'id_gg', 'Họ và tên', 'lop_cn', 'salary_ngay_cong_divided']]
    # Riêng phòng đào tạo
    df_proportion_daotao = salary[salary['Họ và tên'].isin(daotao)]

    df_proportion_daotao = distribution(
        df_proportion_daotao, 'salary_ngay_cong', 'salary_ngay_cong_divided')
    # Concat luong đào tạo and lương giáo viên
    salary_gv_dt = pd.concat([df_proportion_daotao, df_proportion_nodaotao])
    salary_gv_dt['salary_ngay_cong_divided'] = round(
        salary_gv_dt['salary_ngay_cong_divided'], 2)
    salary_gv_dt = salary_gv_dt.sort_values(
        "salary_ngay_cong_divided", ascending=False)

    # %%
    # Thưởng khác
    sa = gspread.service_account(
        filename='taichinh-380507-b8f84e9ee681.json')
    sh = sa.open("Nhân sự")
    worksheet = sh.worksheet("Thưởng GV khác")
    reward_other = pd.DataFrame(worksheet.get_all_records())
    # salary = salary.replace("", np.nan).dropna(subset = 'Mã giáo viên')
    reward_other = reward_other.replace('\.', '', regex=True)

    reward_other = reward_other.astype(
        {'Số tiền': 'float', 'date_affected': 'datetime64[ns]'})
    reward_other.columns = ['id_gg', 'Họ và tên', 'thuong_amount',
                            'note', 'reward_type', 'date_affected']
    reward_other = reward_other.query(
        "date_affected >= @ketoan_start_time and date_affected <= @ketoan_end_time")
    reward_other_gv = reward_other.groupby(["id_gg", "Họ và tên"], as_index=False)[
        'thuong_amount'].sum()

    reward_other = reward_other.groupby(
        ['id_gg', 'Họ và tên', 'reward_type', 'date_affected'], as_index=False)['thuong_amount'].sum()

    reward_other = distribution(
        reward_other, 'thuong_amount', 'thuong_amount_divided')
    reward_other_total = reward_other.groupby('lop_cn', as_index=False)[
        'thuong_amount_divided'].sum()

    reward_other_total = rename_lop(reward_other_total, 'lop_cn')

    # ----------------------# Thực thu
    # hv đang họccd
    hocvien_danghoc = hocvien.merge(orders, on='hv_id')\
        .query("ketoan_active == 1")\
        .groupby('ketoan_coso', as_index=False).size().rename(columns={"size": "total_students"})
    hocvien_danghoc = rename_lop(hocvien_danghoc, 'ketoan_coso')
    # Lop dang hoc
    lop_danghoc = lophoc.query(
        "(lop_status == 2 or lop_status == 4) and deleted_at.isnull()")\
        .groupby('lop_cn', as_index=False).size().rename(columns={"size": "total_classes"})
    lop_danghoc.lop_cn = lop_danghoc.lop_cn.replace(
        {1: "Hoa Cúc", 2: "Gò Dầu", 3: "Lê Quang Định", 5: "Lê Hồng Phong"})
    ""
    # "------------------"
    # %% Thực thu

    diemdanh_details['date_created'] = diemdanh_details['date_created'].astype(
        "datetime64[ns]")

    thucthu = diemdanh_details.query(
        'date_created >= @ketoan_start_time and date_created <= @ketoan_end_time')\
        .groupby(['ketoan_id', 'lop_id', 'gv_id', 'date_created'], as_index=False)['price', 'giohoc'].sum()\
        .merge(lophoc, on='lop_id', how='left')\
        .merge(users[['fullname', 'id']], left_on='gv_id', right_on='id', how='left')

    thucthu_all = diemdanh_details.query("date_created >= '2023-01-01'")\
        .groupby(['ketoan_id', 'lop_id', 'gv_id', 'date_created', 'price'], as_index=False)['giohoc'].sum()\
        .merge(lophoc, on='lop_id')\
        .merge(users[['fullname', 'id']], left_on='gv_id', right_on='id')

    thucthu['date_created_month'] = thucthu['date_created'].dt.month_name()
    thucthu_all['date_created_month'] = thucthu_all['date_created'].dt.month_name()

    new_order = ['January', 'February', 'March', 'April', 'May', 'June',
                 'July', 'August', 'September', 'October', 'November', 'December']
    # Reorder months
    thucthu_all['date_created_month'] = pd.Categorical(
        thucthu_all['date_created_month'], categories=new_order, ordered=True)
    # Groupby giaovien
    thucthu_gv = thucthu.groupby(['id', 'fullname'], as_index=False)[
        'price'].sum()
    # Groupby cn
    thucthu_cn = thucthu.groupby(['lop_cn'], as_index=False)['price'].sum()
    thucthu_cn_rename = thucthu.groupby(
        ['lop_cn'], as_index=False)['price'].sum()
    thucthu_cn_rename = rename_lop(thucthu_cn_rename, 'lop_cn')

    # Thực thu theo giáo viên và chi nhánh
    thucthu_details = thucthu.groupby(
        ['id', 'fullname', 'lop_cn'], as_index=False)['price'].sum()
    # "_______________"

    thucthu_diemdanh_ngay = thucthu_time(thucthu, 'date_created')
    thucthu_diemdanh_ngay = thucthu_diemdanh_ngay.pivot(
        index='date_created', columns='lop_cn', values='price')
    thucthu_diemdanh_month = thucthu_time(thucthu_all, 'date_created_month')
    # Thực thu điểm danh theo ngày và tháng
    fig9 = px.bar(thucthu_diemdanh_ngay, x=thucthu_diemdanh_ngay.index, y=thucthu_diemdanh_ngay.columns, barmode='stack',
                  color_discrete_sequence=['#07a203', '#ffc107', '#e700aa', '#2196f3'])

    fig10 = px.bar(thucthu_diemdanh_month, x="date_created_month",
                   y="price", color="lop_cn", barmode="group", color_discrete_sequence=['#ffc107', '#07a203', '#2196f3', '#e700aa'], text="price")
    # update the chart layout
    fig9.update_layout(title='Thực thu điểm danh theo ngày',
                       xaxis_title='Ngày', yaxis_title='Thực thu điểm danh')
    fig10.update_layout(title='Thực thu điểm danh theo tháng trong năm 2023',
                        xaxis_title='Tháng', yaxis_title='Thực thu', showlegend=True)
    fig10.update_traces(
        hovertemplate="Thực thu điểm danh: %{y:,.0f}<extra></extra>")
    # "_______________"
    fig1 = plotly_chart(thucthu_cn_rename, 'lop_cn', 'price', thucthu_cn_rename['price'].apply(lambda x: format(x, ',')),
                        "Thực thu theo chi nhánh", 'Chi nhánh', 'Thực thu')

    # "_______________" Tính tổng lương

    fixed_salary_cn = salary_gv_dt.groupby("lop_cn", as_index=False)[
        'salary_ngay_cong_divided'].sum()
    overtime_salary_cn = sal_diem_over_group_lop.groupby("lop_cn", as_index=False)[
        'salary_gio_cong'].sum()
    overtime_fixed_salary_cn = fixed_salary_cn.merge(
        overtime_salary_cn, on='lop_cn')
    # Add thuong dat diem to thucthu
    overtime_fixed_salary_cn = rename_lop(overtime_fixed_salary_cn, 'lop_cn')

    # %%
    # Add thuong to thucthu
    overtime_fixed_salary_cn = overtime_fixed_salary_cn.merge(total_reward, left_on='lop_cn', right_on='hv_coso', how='outer')\
        .merge(total_datdiem, on='hv_coso', how='outer')\
        .merge(reward_other_total[['lop_cn', 'thuong_amount_divided']], on='lop_cn', how='outer')

    # %%
    overtime_fixed_salary_cn.fillna(0, inplace=True)
    overtime_fixed_salary_cn['total_expenses'] = overtime_fixed_salary_cn['salary_ngay_cong_divided'] + \
        overtime_fixed_salary_cn['salary_gio_cong'] + overtime_fixed_salary_cn['thuong'] + overtime_fixed_salary_cn['divided_thuong_datdiem'] \
        + overtime_fixed_salary_cn['thuong_amount_divided']

    thucthu_cn = rename_lop(thucthu_cn, 'lop_cn')
    salary_thucthu = overtime_fixed_salary_cn.merge(thucthu_cn, on='lop_cn')
    # Create grand total
    salary_thucthu_grand_total = grand_total(salary_thucthu, 'lop_cn')
    # Create percent (total_expense: Tổng chi phí giáo viên, price: 'Tổng thực thu điểm danh)
    # salary_thucthu_grand_total['percent'] = salary_thucthu_grand_total['total_expenses'] / \
    #     salary_thucthu_grand_total.price * 100
    # salary_thucthu_grand_total['percent'] = round(
    #     salary_thucthu_grand_total['percent'], 2)

    # %%
    salary_thucthu_grand_total.drop("hv_coso", axis=1, inplace=True)

    salary_thucthu_grand_total.columns = \
        ['Chi nhánh', 'Tổng lương ngày công',
         'Tổng lương giờ công', 'Tổng thưởng đầu vào', 'Tổng thưởng đạt điểm', 'Tổng thưởng khác', 'Tổng chi phí giáo viên', 'Tổng thực thu điểm danh']

    # %%

    # "_______________"
    thucthu_hocvien_lop = thucthu_cn_rename.merge(
        hocvien_danghoc, left_on='lop_cn', right_on='ketoan_coso')\
        .merge(lop_danghoc, on='lop_cn')
    thucthu_hocvien_lop['thucthu_div_hocvien'] = round(
        thucthu_hocvien_lop['price'] / thucthu_hocvien_lop['total_students'], 0)
    thucthu_hocvien_lop['thucthu_div_lophoc'] = round(
        thucthu_hocvien_lop['price'] / thucthu_hocvien_lop['total_classes'], 0)

    # "_______________"
    overtime_salary_cn_gv = sal_diem_over_group_lop.groupby(
        ['id_gg', 'Họ và tên', "lop_cn", "working_status_x"], as_index=False)['salary_gio_cong'].sum()
    df = overtime_salary_cn_gv.merge(
        salary_gv_dt, on=['lop_cn', 'Họ và tên', 'id_gg'], how='outer')
    df.fillna(0, inplace=True)
    df['fixed_overtime'] = df['salary_gio_cong'] + \
        df['salary_ngay_cong_divided']
    df = rename_lop(df, 'lop_cn')
    gv_thucthu_cs = df.merge(thucthu_cn, on='lop_cn')
    gv_thucthu_cs['percent'] = round(gv_thucthu_cs['fixed_overtime'] /
                                     gv_thucthu_cs['price'] * 100, 2)
    # "_______________"
    gv_thucthu_gv = gv_thucthu_cs.groupby(['id_gg', 'Họ và tên'], as_index=False)['fixed_overtime'].sum()\
        .merge(thucthu_gv, left_on='id_gg', right_on='id', how='left')
    gv_thucthu_gv['percent'] = round(gv_thucthu_gv['fixed_overtime'] /
                                     gv_thucthu_gv['price'] * 100, 2)

    gv_thucthu_gv = gv_thucthu_gv.merge(salary, left_on='id', right_on='id_gg')

    # Fulltime
    df = gv_thucthu_gv
    df1 = df[df["working_status"] == "Fulltime"].sort_values(
        by="percent", ascending=True)
    df1['fullname'] = df1['fullname'] + " (" + df['level'] + ")"

    # Parttime
    df2 = df[df["working_status"] == "Partime"].sort_values(
        by="percent", ascending=True)
    df2['fullname'] = df2['fullname'] + " (" + df['level'] + ")"
    # Plotly graphs

    fig3 = plotly_chart(df1.sort_values(
        "percent", ascending=True), 'fullname', 'percent', df1["percent"].apply(
        lambda x: '{:.2%}'.format(x/100)),
        "Fulltime - Tỷ lệ Tổng chi phí / thực thu", '', 'Tỷ lệ')
    fig3.update_layout(
        height=1000,  # set the height of the plot to 600 pixels
        width=800)


# Plotly graphs
    fig3_1 = plotly_chart(df2.sort_values(
        "percent", ascending=True), 'fullname', 'percent', df2["percent"].apply(
        lambda x: '{:.2%}'.format(x/100)),
        "Parttime - Tỷ lệ Tổng chi phí / thực thu", '', 'Tỷ lệ')
    fig3_1.update_layout(
        height=1000,  # set the height of the plot to 600 pixels
        width=800)

    # "_______________" thực thu chuyển phí

    # Filter orders
    orders_chuyenphi = orders.query("ketoan_active == 5")[["ketoan_id", "hv_id", "ketoan_details", "ketoan_coso", "ketoan_sogio", "ketoan_price",
                                                           "ketoan_tientrengio", "remaining_time", "kh_id"]]
    # Filter hv_status
    hv_status_chuyenphi = hv_status[['ketoan_id', 'status', 'lop_id', 'note', 'is_price', 'created_at']]\
        .query("status ==7")
    # Filter hocvien
    hocvien_chuyenphi = hocvien[['hv_id', 'hv_fullname']]
    # Merge hv_status and orders
    chuyenphi = hv_status_chuyenphi.merge(
        orders_chuyenphi, on='ketoan_id', how='left')
    # Merge hocvien_chuyephi
    chuyenphi = chuyenphi.merge(hocvien_chuyenphi, on='hv_id', how='left')
    chuyenphi = chuyenphi[['created_at', 'hv_fullname',
                           'ketoan_coso', 'note', 'is_price']]
    # Add column Phi Chuyen
    chuyenphi['phí chuyển'] = chuyenphi.is_price * 0.1
    # Add column Tien con lai sau phi
    chuyenphi['còn lại sau phí'] = chuyenphi.is_price - \
        chuyenphi['phí chuyển']
    # Change data type
    chuyenphi = chuyenphi.astype(
        {'created_at': 'datetime64[ns]'})
    # Sort
    chuyenphi = chuyenphi.sort_values(by='created_at', ascending=False)
    chuyenphi = chuyenphi.query(
        "created_at >= @ketoan_start_time and created_at <= @ketoan_end_time")
    # Rename columns
    # chuyenphi.columns = [["created_at", "Họ tên", "ketoan_coso", "Ghi chú", "Học phí chuyển", "Phí chuyển", "Còn lại sau phí"]]
    chuyenphi = chuyenphi.groupby('ketoan_coso', as_index=False)[
        'phí chuyển'].sum()

    chuyenphi = rename_lop(chuyenphi, 'ketoan_coso')

    # "_______________" Thực thu kết thúc
    # Filter ketthuc
    orders_ketthuc = orders.query("ketoan_active == 5 and deleted_at.isnull()")
    # Merge orders_ketthuc and diemdanh_details
    df = diemdanh_details[['ketoan_id', 'giohoc']]\
        .merge(orders_ketthuc, on='ketoan_id', how='right').groupby(
        ['ketoan_id', 'ketoan_coso', 'remaining_time', 'ketoan_tientrengio', 'date_end'], as_index=False).giohoc.sum()
    # Add 2 more columns
    df['gio_con_lai'] = df.remaining_time - df.giohoc
    df['thực thu kết thúc'] = df.gio_con_lai * df.ketoan_tientrengio
    # Convert to datetime
    df['date_end'] = pd.to_datetime(df['date_end'])
    # Filter gioconlai > 0 and time
    thucthu_ketthuc = df.query("gio_con_lai > 0")\
        .query("date_end >= @ketoan_start_time and date_end <= @ketoan_end_time")
    thucthu_ketthuc = thucthu_ketthuc.merge(
        orders[['hv_id', 'ketoan_id']], on='ketoan_id')
    thucthu_ketthuc = thucthu_ketthuc.groupby("ketoan_coso", as_index=False)[
        'thực thu kết thúc'].sum()
    thucthu_ketthuc = rename_lop(thucthu_ketthuc, 'ketoan_coso')
    # "_______________"

    overtime_salary = sal_diem_over_group.query('working_status_x != "Ngoài giờ"')\
        .merge(salary[['Họ và tên', 'working_status']], left_on='Họ và tên', right_on='Họ và tên')
    overtime_salary['out_div_total'] = overtime_salary['salary_gio_cong'] / \
        (overtime_salary['salary_ngay_cong'] +
         overtime_salary['salary_gio_cong'])
    overtime_salary = overtime_salary[[
        'Họ và tên', 'salary_ngay_cong', 'salary_gio_cong', 'out_div_total']]
    overtime_salary['out_div_total'] = round(
        overtime_salary['out_div_total'] * 100, 2)
    overtime_salary_fulltime = overtime_salary.query("salary_ngay_cong != 0")

    # "_______________" thucthu điểm danh and chuyen phi

    thucthu_hocvien_lop = thucthu_hocvien_lop.merge(
        chuyenphi, left_on='ketoan_coso', right_on='ketoan_coso', how='left')\
        .merge(thucthu_ketthuc, left_on='ketoan_coso', right_on='ketoan_coso')
    # Renam thucthu => thuc thu diem danh
    thucthu_hocvien_lop = thucthu_hocvien_lop.rename(
        columns={'price': "thực thu điểm danh"})
    # Fillna with 0
    thucthu_hocvien_lop.fillna(0, inplace=True)
    # Add all thucthu
    try:
        thucthu_hocvien_lop['tổng thực thu'] = thucthu_hocvien_lop['phí chuyển'] + \
            thucthu_hocvien_lop['thực thu kết thúc'] + \
            thucthu_hocvien_lop['thực thu điểm danh']
    except KeyError:
        try:
            thucthu_hocvien_lop['tổng thực thu'] = thucthu_hocvien_lop['thực thu kết thúc'] +\
                thucthu_hocvien_lop['thực thu điểm danh']
        except KeyError:
            thucthu_hocvien_lop['tổng thực thu'] = thucthu_hocvien_lop['thực thu điểm danh']

    # Add ty lệ thực thu
    thucthu_hocvien_lop['tỷ trọng tổng thực thu'] = thucthu_hocvien_lop['tổng thực thu'].apply(
        lambda x: round(x/thucthu_hocvien_lop['tổng thực thu'].sum()*100, 2))
    # create a new row with the sum of each numerical column
    totals = thucthu_hocvien_lop.select_dtypes(include=[float, int]).sum()
    totals["lop_cn"] = "Grand total"
    # append the new row to the dataframe
    thucthu_hocvien_lop = thucthu_hocvien_lop.append(
        totals, ignore_index=True)
    # Add % in tỷ trọng tổng thực thu
    thucthu_hocvien_lop["tỷ trọng tổng thực thu"] = thucthu_hocvien_lop["tỷ trọng tổng thực thu"].apply(
        lambda x: '{:.2%}'.format(x/100))
    # get tổng thực thu
    salary_thucthu_grand_total = thucthu_hocvien_lop[['lop_cn', 'tổng thực thu']].merge(
        salary_thucthu_grand_total, left_on='lop_cn', right_on='Chi nhánh')
    salary_thucthu_grand_total['Tổng chi phí giáo viên / tổng các loại thực thu'] = salary_thucthu_grand_total['Tổng chi phí giáo viên'] / \
        salary_thucthu_grand_total['tổng thực thu']
    # "_______________"
    # Create a barplot for Tỷ lệ Tổng chi phí / thực thu theo chi nhánh
    fig2 = plotly_chart(salary_thucthu_grand_total, 'Tổng chi phí giáo viên / tổng các loại thực thu', 'Chi nhánh', salary_thucthu_grand_total["Tổng chi phí giáo viên / tổng các loại thực thu"].apply(
        lambda x: '{:.2%}'.format(x)),
        "Tổng chi phí giáo viên / tổng các loại thực thu", 'Tổng chi phí giáo viên / tổng các loại thực thu', 'Chi nhánh', color='Chi nhánh', map={
        'Hoa Cúc': '#ffc107',
        'Gò Dầu': '#07a203',
        'Lê Quang Định': '#2196f3',
        'Lê Hồng Phong': '#e700aa',
        'Grand total': 'white'
    })
    fig2.update_layout(font=dict(size=17), xaxis={
                       'categoryorder': 'total descending'})
    st.plotly_chart(fig2, use_container_width=True)

    st.info(f'Tổng chi phí giáo viên = tổng lương ngày công + tổng lương giờ công + tổng thưởng đầu vào + tổng thưởng đạt điểm + tổng thưởng khác')
    st.info(
        f'Tổng thực thu  = thực thu điểm danh + thực thu chuyển phí + thực thu kết thúc')
    st.subheader("Các loại thực thu theo chi nhánh")
    # define a function

    @ st.cache_data()
    def thousands_divider(df, col):
        df[col] = df[col].apply(
            lambda x: '{:,.0f}'.format(x))
        return df
    thucthu_hocvien_lop = thousands_divider(
        thucthu_hocvien_lop, 'tổng thực thu')
    thucthu_hocvien_lop = thousands_divider(
        thucthu_hocvien_lop, 'thực thu điểm danh')
    try:
        thucthu_hocvien_lop = thousands_divider(
            thucthu_hocvien_lop, 'thực thu kết thúc')
        thucthu_hocvien_lop = thousands_divider(
            thucthu_hocvien_lop, 'phí chuyển')
        thucthu_hocvien_lop = thucthu_hocvien_lop.set_index("lop_cn")
        thucthu_hocvien_lop.index.names = ['Chi nhánh']
        thucthu_hocvien_lop = thucthu_hocvien_lop.rename(
            columns={"phí chuyển": "thực thu chuyển phí"})
        # Show tables
        st.dataframe(thucthu_hocvien_lop.drop(["ketoan_coso", "total_students", "total_classes", "thucthu_div_hocvien", "thucthu_div_lophoc"],
                                              axis=1).style.background_gradient().set_precision(0), use_container_width=True)
    except KeyError:
        st.warning(
            f"Từ ngày {ketoan_start_time} đến ngày {ketoan_end_time} chưa có data thực thu chuyển phí và thực thu kết thúc")
    st.subheader("Các loại chi phí theo chi nhánh")
    st.dataframe(salary_thucthu_grand_total[['Chi nhánh', 'Tổng lương ngày công',
                                             'Tổng lương giờ công', 'Tổng thưởng đầu vào', 'Tổng thưởng đạt điểm', 'Tổng thưởng khác', 'Tổng chi phí giáo viên']].set_index(
        "Chi nhánh"), use_container_width=True)
    # Show Chi nhanh by 2 columns
    st.plotly_chart(fig10, use_container_width=True)
    st.plotly_chart(fig9, use_container_width=True)

    left_column, right_column = st.columns(2)
    left_column.plotly_chart(fig3, use_container_width=True)
    right_column.plotly_chart(fig3_1, use_container_width=True)

    ""

    fig4 = plotly_chart(overtime_salary_fulltime[['Họ và tên', 'out_div_total']].sort_values(
        "out_div_total", ascending=True), "Họ và tên", 'out_div_total', 'out_div_total',
        "Tỷ lệ lương ngoài giờ / trong giờ của giáo viên fulltime", '', 'Tỷ lệ')
    fig4.update_layout(height=800, width=800)
    st.plotly_chart(fig4)

    # Create session state
    # if "reward_test_enrol" not in st.session_state:
    #     st.session_state['reward_test_enrol'] = reward_test_enrol.rename(
    #             columns={'fullname': "Họ và tên", "id": "id_gg"})
    # if "conversion" not in st.session_state:
    #     st.session_state['conversion'] = conversion

    # if "reward_datdiem" not in st.session_state:
    #     st.session_state['reward_datdiem'] = reward_datdiem.rename(
    #         columns={'fullname': "Họ và tên", "id": "id_gg"})
    # if "reward_other" not in st.session_state:
    #     st.session_state['reward_other'] = reward_other
