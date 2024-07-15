import streamlit as st
import pandas as pd
import re
import io


def normalize_location(location):
    return re.sub(r'\s', '', location).lower()


def process_pickup_info(input_data, default_time):
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

    def create_dataframes(grouped_customers):
        dataframes = {}
        for (time, location), persons in grouped_customers.items():
            data = {
                'Pickup Person': '; '.join(persons),
                'Pickup time': time,
                'Pickup Location': location.capitalize(),
                'Number of People': len(persons)  # Add this line
            }
            df = pd.DataFrame([data])
            dataframes[(time, location)] = df
        return dataframes

    customers = parse_input(input_data)
    grouped_customers = group_by_pickup(customers)
    dataframes = create_dataframes(grouped_customers)

    for key, df in dataframes.items():
        df['Pickup time'] = pd.to_datetime(df['Pickup time'], format='%I:%M%p', errors='coerce')
        df['Pickup time'] = df['Pickup time'].dt.strftime('%I:%M%p').str.lower()

    return dataframes


def parse_car_plate_and_mobile(input_text):
    lines = input_text.strip().split('\n')
    car_plate = lines[0].strip() if lines else ''
    mobile = lines[1].strip() if len(lines) > 1 else ''
    return car_plate, mobile


st.title('Pickup Information Processor')

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

input_data = st.text_area('Enter pickup information (one entry per line):', value=default_content, height=300,
                          key="input_data_1")
default_time = st.text_input('Enter default pickup time (e.g., 8:00am):', '8:00am')

if 'dataframes' not in st.session_state:
    st.session_state.dataframes = {}

if st.button('Process Pickup Information'):
    if input_data:
        st.session_state.dataframes = process_pickup_info(input_data, default_time)
        st.success("Data processed successfully. Please enter Car Plate and Mobile information for each group below.")

if st.session_state.dataframes:
    merged_dataframes = {}

    for (time, location), df in st.session_state.dataframes.items():
        st.subheader(f"Pickup at {time} from {location.capitalize()}")

        input_text = st.text_area(
            f"Enter Car Plate and Mobile for {time} at {location.capitalize()} (Car Plate on first line, Mobile on second line):",
            height=100,
            key=f"input_{time}_{location}")

        lines = input_text.split('\n')
        car_plate = lines[0].strip() if lines else ''
        mobile = lines[1].strip() if len(lines) > 1 else ''

        if car_plate and mobile:
            df['Car Plate'] = car_plate
            df['Mobile'] = mobile

            # ... rest of the code remains the same

            key = (car_plate, mobile)
            if key in merged_dataframes:
                existing_df = merged_dataframes[key]
                existing_df['Pickup Person'] += f"\n{location.capitalize()}: {df['Pickup Person'].iloc[0]}"
                existing_df['Pickup Location'] += f", {df['Pickup time'].iloc[0]} at {location.capitalize()}"
                existing_df['Number of People'] += df['Number of People'].iloc[0]
                if pd.to_datetime(df['Pickup time'].iloc[0]) < pd.to_datetime(existing_df['Pickup time'].iloc[0]):
                    existing_df['Pickup time'] = df['Pickup time'].iloc[0]
            else:
                df['Pickup Person'] = f"{location.capitalize()}: {df['Pickup Person'].iloc[0]}"
                df['Pickup Location'] = f"{df['Pickup time'].iloc[0]} at {location.capitalize()}"
                merged_dataframes[key] = df

        st.dataframe(df, use_container_width=True)

    if merged_dataframes:
        st.markdown("---")
        st.header("Merged Dataframes")
        for idx, (key, df) in enumerate(merged_dataframes.items()):
            st.subheader(f"Group {idx + 1}")

            # Format the Pickup Person column
            pickup_persons = df['Pickup Person'].iloc[0].split('\n')
            formatted_pickup_persons = []
            for person in pickup_persons:
                location, names = person.split(':', 1)
                num_people = len(names.split(';'))
                formatted_pickup_persons.append(f"{location}: {names.strip()} ({num_people} people)")
            df['Pickup Person'] = '\n'.join(formatted_pickup_persons)

            # Sort and format Pickup Location
            locations = df['Pickup Location'].iloc[0].split(', ')
            sorted_locations = sorted(locations, key=lambda x: pd.to_datetime(x.split(' at ')[0]))
            df['Pickup Location'] = ', '.join(sorted_locations)

            # Apply styling to the dataframe
            styled_df = df.style.set_properties(**{
                'background-color': '#f0f2f6',
                'color': 'black',
                'border-color': 'white'
            })
            styled_df = styled_df.set_table_styles([
                {'selector': 'th', 'props': [('background-color', '#4e73df'), ('color', 'white')]},
                {'selector': 'td', 'props': [('padding', '10px')]},
            ])

            st.dataframe(styled_df, use_container_width=True, height=200)

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Pickup Info', index=False)

            st.download_button(
                label=f"Download Excel file for Group {idx + 1}",
                data=buffer.getvalue(),
                file_name=f"pickup_info_group_{idx + 1}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"download_group_{idx + 1}"
            )

            st.markdown("---")
