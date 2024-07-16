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
            time = re.sub(r'\(.*?\)', '', time).strip().lower()
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
                'Number of People': len(persons)
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


def merge_dataframes(dataframes):
    merged = {}
    for (time, location), df in dataframes.items():
        key = (df['Car Plate'].iloc[0], df['Mobile'].iloc[0])
        if key not in merged:
            merged[key] = df.copy()
        else:
            merged[key][
                'Pickup Person'] += f"\n{location.capitalize()}: {df['Pickup Person'].iloc[0]} ({df['Number of People'].iloc[0]} people)"
            merged[key]['Pickup Location'] += f", {df['Pickup time'].iloc[0]} at {location.capitalize()}"
            merged[key]['Number of People'] += df['Number of People'].iloc[0]
            if pd.to_datetime(df['Pickup time'].iloc[0]) < pd.to_datetime(merged[key]['Pickup time'].iloc[0]):
                merged[key]['Pickup time'] = df['Pickup time'].iloc[0]
    return list(merged.values())


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

        # Single input field for both Car Plate and Mobile
        input_text = st.text_area(
            f"Enter Car Plate and Mobile for {time} at {location.capitalize()} (Car Plate on first line, Mobile on second line):",
            height=100,
            key=f"input_{time}_{location}")

        car_plate, mobile = parse_car_plate_and_mobile(input_text)

        if car_plate and mobile:
            df['Car Plate'] = car_plate
            df['Mobile'] = mobile

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

        st.dataframe(df, width=1000, height=150)

    # Add this after your input section
    st.markdown("---")
    st.markdown("<br>", unsafe_allow_html=True)

    # Then add the header for Merged Dataframes
    st.markdown("<br>", unsafe_allow_html=True)

    st.subheader("Merged Dataframes")

    # Custom CSS for table styling
    st.markdown("""
    <style>
        .dataframe td {
            white-space: pre-wrap;
        }
        .bold-location {
            font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)

    for idx, (key, df) in enumerate(merged_dataframes.items()):
        st.write(f"Group {idx + 1}")


        # Format the Pickup Person column with bold location names and line breaks
        def format_pickup_person(person):
            parts = person.split(':', 1)
            if len(parts) == 2:
                location, names = parts
                num_people = len(names.split(';'))
                return f'<span class="bold-location">{location.strip()}:</span> {names.strip()} ({num_people} people)'
            else:
                return person.strip()


        pickup_persons = df['Pickup Person'].iloc[0].split('\n')
        formatted_pickup_persons = [format_pickup_person(person) for person in pickup_persons]
        df['Pickup Person'] = '<br>'.join(formatted_pickup_persons)

        # Sort and format Pickup Location
        locations = df['Pickup Location'].iloc[0].split(', ')
        sorted_locations = sorted(locations, key=lambda x: pd.to_datetime(x.split(' at ')[0]))
        df['Pickup Location'] = '<br>'.join(sorted_locations)

        # Prepare DataFrame for Excel export (without HTML formatting)
        export_df = df.copy()
        export_df['Pickup Person'] = export_df['Pickup Person'].str.replace('<br>', '\n')
        export_df['Pickup Person'] = export_df['Pickup Person'].str.replace('<span class="bold-location">', '')
        export_df['Pickup Person'] = export_df['Pickup Person'].str.replace('</span>', '')
        export_df['Pickup Location'] = export_df['Pickup Location'].str.replace('<br>', ', ')

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            export_df.to_excel(writer, sheet_name='Pickup Info', index=False)

        # Place the download button here, before the dataframe display
        st.download_button(
            label=f"Download Excel file for Group {idx + 1}",
            data=buffer.getvalue(),
            file_name=f"pickup_info_group_{idx + 1}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"download_group_{idx + 1}"
        )

        # Display the dataframe
        st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)

        st.markdown("---")