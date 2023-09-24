import requests
import pandas as pd
from datetime import datetime, timedelta, date
import streamlit as st
import plotly.express as px
import streamlit_authenticator as stauth

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
    def lop_kem_nhom():
        khoahoc_me = khoahoc.query("kh_parent_id == 0 and kh_active == 1")
        df = lophoc[['kh_parent', 'lop_id']].merge(
        khoahoc_me[['kh_id', 'kh_ten']], left_on='kh_parent', right_on='kh_id')
        # Rename columns
        df.rename(columns={'lop_id': 'lop_id', 'kh_ten': 'khoahoc_me'}, inplace=True)
        return df[['lop_id', 'khoahoc_me']]

    # Get khoahoc
    khoahoc = collect_data('https://vietop.tech/api/get_data/khoahoc')
    # Get a response
    lophoc = collect_filtered_data(
        table='lophoc', date_column='lop_start', start_time=ketoan_start_time, end_time=ketoan_end_time)

    df = lophoc.merge(khoahoc[['kh_id', 'kh_ten']], on='kh_id', how='inner')
    df = df.query("lop_type == 1 and deleted_at.isnull()")
    df['lop_start'] = df['lop_start'].astype("datetime64[ns]")

    # Create Month
    # df['lop_start'] = df['lop_start'].astype("datetime64[ns]")
    # df['lop_start_month'] = df['lop_start'].dt.strftime('%-m')
    # df['lop_start_year'] = df['lop_start'].dt.strftime('%-Y')
    # df['lop_end'] = df['lop_end'].astype("datetime64[ns]")
    # df['lop_end_month'] = df['lop_end'].dt.strftime('%-m')
    # df['lop_end_year'] = df['lop_start'].dt.strftime('%-Y')
    # display(lophoc_2023.head())
    # total class open
    df['lop_start'] = df['lop_start'].dt.date
    df = rename_lop(df, 'lop_cn')
    df = df.groupby(['lop_id', 'lop_cn', 'class_type', 'kh_ten',
                    'lop_start'], as_index=False).size()
    
    df = df.merge(lop_kem_nhom(), on = 'lop_id')
    # df = df.set_index("lop_id")
    df.rename(columns={'kh_ten': 'khoahoc_con'}, inplace=True)
    # Reindex columns
    df = df[['lop_id', 'lop_cn', 'class_type', 'lop_start', 'khoahoc_me', 'khoahoc_con', 'size']]
    #%% 
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
    st.subheader(f"Số lớp khai giảng theo chi nhánh (Tổng {df.shape[0]} lớp)")
    st.plotly_chart(fig1, use_container_width=True)
    #%%
    on_off = st.selectbox(label="Select online / offline:",
                                    options=list(df['class_type'].unique()))
    df_group = df.query("class_type == @on_off").groupby(["lop_cn", "khoahoc_me"], as_index=False)['size'].sum()
    df_group.columns = ['lop_cn', 'khoahoc_me', 'count']
    fig2 = px.bar(df_group, x="lop_cn",
                   y="count", color="khoahoc_me", barmode="group", color_discrete_sequence=['#ffc107', '#07a203', '#2196f3', '#e700aa'], text="count")
    # update the chart layout
    fig2.update_layout(title='Thống kê các loại lớp khai giảng',
                        xaxis_title='Chi nhánh', yaxis_title='Số lớp khai giảng', showlegend=True)
    fig2.update_traces(
        hovertemplate="Số lớp khai giảng: %{y:,.0f}<extra></extra>")
    
    st.plotly_chart(fig2, use_container_width=True)
    "---"
    st.subheader(
        f"Lớp khai giảng theo chi nhánh và loại lớp")
    st.dataframe(df_group, use_container_width=True)
    "---"
    st.subheader(
        f"Chi tiết lớp khai giảng")
    
    st.dataframe(df.drop("size", axis =1), use_container_width=True)
   

