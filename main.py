import streamlit as st
import pandas as pd
import re
import io

def normalize_location(location):
    return re.sub(r'\s', '', location).lower()

def process_pickup_info(input_data, default_time, default_car_plate, default_mobile):
    def parse_input(input_data):
        entries = input_data.strip().split('\n')
        customer_list = []
        for entry in entries:
            parts = re.split(r'\s*-\s*', entry.strip())
            person = parts[1]
            location = normalize_location(parts[2]) if len(parts) > 2 else ''
            time = parts[3] if len(parts) > 3 else default_time
            time = re.sub(r'\(.*?\)', '', time).strip().lower()  # Remove remarks and lowercase
            customer_list.append({'Pickup Person': person, 'Pickup time': time, 'Pickup Location': location})
        return customer_list

    def group_by_pickup(customers):
        grouped_customers = {}
        for cust in customers:
            key = (cust['Pickup time'], cust['Pickup Location'])
            if key not in grouped_customers:
                grouped_customers[key] = []
            grouped_customers[key].append(cust['Pickup Person'])
        return grouped_customers

    def create_dataframe(grouped_customers):
        data = []
        for (time, location), persons in grouped_customers.items():
            data.append({
                'Pickup Person': '; '.join(persons),
                'Pickup time': time,
                'Pickup Location': location.capitalize(),
                'Car Plate': default_car_plate,
                'Mobile': default_mobile
            })
        return pd.DataFrame(data)

    customers = parse_input(input_data)
    grouped_customers = group_by_pickup(customers)
    df = create_dataframe(grouped_customers)

    df['Pickup time'] = pd.to_datetime(df['Pickup time'], format='%I:%M%p', errors='coerce')
    df = df.sort_values(['Pickup time', 'Pickup Location'])
    df['Pickup time'] = df['Pickup time'].dt.strftime('%I:%M%p').str.lower()

    return df

default_content = """1- Eric peng-Ritz -9:00AM(Remark Special time)
2- Cai Chunhui -parkhyatt
3- CL Lim - pArkhyatt 
4- Sam Yuen - Park Hyatt - 7:40am
5- Bo Xu - Park Hyatt
6- Arman - ritz
8- Steven - Park Hyatt
8- Shengyang@Meta - Ritz
9- Jolley W - Ritz
110- dana Jensen  - W
11- Abel - parkhyaTT  -           7:40aM
12- Wilkins - RitZ -7:40Am 
15 - Gogo - ritz - 8:30Am"""



st.title('Pickup Information Processor')

# Use a unique key for the first text_area
input_data = st.text_area('Enter pickup information (one entry per line):', height=300, key="input_data_1")
default_time = st.text_input('Enter default pickup time (e.g., 8:00am):', '8:00am')
default_car_plate = st.text_input('Enter default car plate:', '            ')
default_mobile = st.text_input('Enter default mobile number:', '               ')

# Remove the duplicate text_area widget
# input_data = st.text_area('Enter pickup information (one entry per line):', height=300)

if st.button('Process Pickup Information'):
    if input_data:
        result_df = process_pickup_info(input_data, default_time, default_car_plate, default_mobile)
        st.dataframe(result_df)

        # Create a download button for the Excel file
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            result_df.to_excel(writer, sheet_name='Pickup Info', index=False)

        st.download_button(
            label="Download Excel file",
            data=buffer.getvalue(),
            file_name="pickup_info.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning('Please enter pickup information.')
