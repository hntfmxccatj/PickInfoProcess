import streamlit as st
import pandas as pd
import re
import io

def normalize_location(location):
    return re.sub(r'\s', '', location).lower()

def format_pickup_person(person):
    lines = person.split('\n')
    formatted_lines = []
    for line in lines:
        parts = line.split(':', 1)
        if len(parts) == 2:
            location, names_and_count = parts
            formatted_lines.append(f'<span class="bold-location">{location.strip()}:</span> {names_and_count.strip()}')
    return '<br>'.join(formatted_lines)

def format_pickup_location(location, times):
    locations = location.split('\n')
    sorted_locations = sorted(zip(times, locations), key=lambda x: x[0])
    return '<br>'.join([loc for _, loc in sorted_locations])

def process_pickup_info(input_data, default_time):
    def parse_input(input_data):
        entries = input_data.strip().split('\n')
        customer_list = []
        pickup_date = None
        for entry in entries:
            if entry.startswith("Pickup time:"):
                pickup_date = entry.split("Pickup time:")[1].strip()
            elif entry[0].isdigit():
                parts = re.split(r'\s*-\s*', entry.strip())
                person = parts[1]
                location = normalize_location(parts[2]) if len(parts) > 2 else ''
                time = parts[3] if len(parts) > 3 else default_time
                time = re.sub(r'\(.*?\)', '', time).strip().lower()
                customer_list.append({'Pickup Person': person, 'Pickup time': time, 'Pickup Location': location, 'Date': pickup_date})
        return customer_list

    def group_by_pickup(customers):
        grouped_customers = {}
        for cust in customers:
            key = (cust['Pickup time'], cust['Pickup Location'], cust['Date'])
            if key not in grouped_customers:
                grouped_customers[key] = []
            grouped_customers[key].append(cust['Pickup Person'])
        return grouped_customers

    def create_dataframes(grouped_customers):
        dataframes = {}
        for (time, location, date), persons in grouped_customers.items():
            data = {
                'Pickup Person': '; '.join(persons),
                'Pickup time': time,
                'Pickup Location': location.capitalize(),
                'Number of People': len(persons),
                'Date': date
            }
            df = pd.DataFrame([data])
            dataframes[(time, location, date)] = df
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
    for (time, location, date), df in dataframes.items():
        if 'Car Plate' in df.columns and 'Mobile' in df.columns:
            key = (df['Car Plate'].iloc[0], df['Mobile'].iloc[0])
            pickup_time = pd.to_datetime(df['Pickup time'].iloc[0])

            if key not in merged:
                merged[key] = {
                    'Pickup Person': f"{location.capitalize()}: {df['Pickup Person'].iloc[0]} ({df['Number of People'].iloc[0]} people)",
                    'Pickup time': pickup_time,
                    'Pickup Location': f"{pickup_time.strftime('%I:%M%p').lower()} at {location.capitalize()}",
                    'Number of People': df['Number of People'].iloc[0],
                    'Car Plate': key[0],
                    'Mobile': key[1],
                    'Pickup Times': [pickup_time],
                    'Date': df['Date'].iloc[0]
                }
            else:
                existing_entry = merged[key]
                existing_entry['Pickup Person'] += f"\n{location.capitalize()}: {df['Pickup Person'].iloc[0]} ({df['Number of People'].iloc[0]} people)"
                existing_entry['Pickup Location'] += f"\n{pickup_time.strftime('%I:%M%p').lower()} at {location.capitalize()}"
                existing_entry['Number of People'] += df['Number of People'].iloc[0]
                existing_entry['Pickup Times'].append(pickup_time)
                existing_entry['Pickup time'] = min(existing_entry['Pickup Times'])

    # Format and create DataFrames
    merged_dataframes = []
    for entry in merged.values():
        entry['Pickup Person'] = format_pickup_person(entry['Pickup Person'])
        entry['Pickup Location'] = format_pickup_location(entry['Pickup Location'], entry['Pickup Times'])
        entry['Pickup time'] = entry['Pickup time'].strftime('%I:%M%p').lower()  # Format as "08:00am"
        del entry['Pickup Times']
        merged_dataframes.append(pd.DataFrame([entry]))

    return merged_dataframes

def parse_car_plate_and_mobile(input_text):
    lines = input_text.strip().split('\n')
    car_plate = lines[0].strip() if lines else ''
    mobile = lines[1].strip() if len(lines) > 1 else ''
    return car_plate, mobile

st.title('Pickup Information Processor')

default_content = """Pickup time: 23th July
1- Eric peng-Ritz -9:00AM(Remark Special time)
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

input_data = st.text_area('Enter pickup information (one entry per line):', value=default_content, height=300, key="input_data_1")
default_time = st.text_input('Enter default pickup time (e.g., 8:00am):', '8:00am')

if 'dataframes' not in st.session_state:
    st.session_state.dataframes = {}

if 'merged_dataframes' not in st.session_state:
    st.session_state.merged_dataframes = []

if st.button('Process Pickup Information'):
    if input_data:
        st.session_state.dataframes = process_pickup_info(input_data, default_time)
        st.session_state.merged_dataframes = []
        st.success("Data processed successfully. Please enter Car Plate and Mobile information for each group below.")

if st.session_state.dataframes:
    for (time, location, date), df in st.session_state.dataframes.items():
        st.subheader(f"Pickup at {time} from {location.capitalize()} on {date}")

        # Single input field for both Car Plate and Mobile
        input_text = st.text_area(
            f"Enter Car Plate and Mobile for {time} at {location.capitalize()} (Car Plate on first line, Mobile on second line):",
            height=100,
            key=f"input_{time}_{location}_{date}")

        car_plate, mobile = parse_car_plate_and_mobile(input_text)

        if car_plate and mobile:
            st.session_state.dataframes[(time, location, date)]['Car Plate'] = car_plate
            st.session_state.dataframes[(time, location, date)]['Mobile'] = mobile

            # Update merged dataframes
            st.session_state.merged_dataframes = merge_dataframes(st.session_state.dataframes)

        st.dataframe(df, width=1200)

    st.markdown("---")
    st.markdown("<br>", unsafe_allow_html=True)

    st.subheader("Merged Dataframes")

    st.markdown("""
    <style>
        .styled-table {
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 0.9em;
            font-family: sans-serif;
            min-width: 400px;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);
        }
        .styled-table thead tr {
            background-color: #009879;
            color: #ffffff;
            text-align: left;
        }
        .styled-table th,
        .styled-table td {
            padding: 12px 15px;
        }
        .styled-table tbody tr {
            border-bottom: 1px solid #dddddd;
        }
        .styled-table tbody tr:nth-of-type(even) {
            background-color: #f3f3f3;
        }
        .styled-table tbody tr:last-of-type {
            border-bottom: 2px solid #009879;
        }
        .bold-location {
            font-weight: bold;
            color: #009879;
        }
        .group-header {
            font-size: 1.2em;
            font-weight: bold;
            margin-top: 20px;
            margin-bottom: 10px;
            color: #009879;
        }
    </style>
    """, unsafe_allow_html=True)

    for idx, df in enumerate(st.session_state.merged_dataframes):
        df = df.drop("Number of People", axis=1)

        new_order = ['Pickup Person', 'Date', 'Pickup time', 'Pickup Location', 'Car Plate', 'Mobile']
        df = df[new_order]

        st.markdown(f"<div class='group-header'>Group {idx + 1}</div>", unsafe_allow_html=True)

        # Allow user to edit Pickup time and Pickup Location
        new_pickup_time = st.text_input(f"Edit Pickup Time for Group {idx + 1}", value=df.at[0, 'Pickup time'],
                                        key=f"time_{idx}")
        new_pickup_location = st.text_input(f"Edit Pickup Location for Group {idx + 1}",
                                            value=df.at[0, 'Pickup Location'], key=f"location_{idx}")

        # Update dataframe based on user input
        df.at[0, 'Pickup time'] = new_pickup_time
        df.at[0, 'Pickup Location'] = new_pickup_location

        # Prepare DataFrame for Excel export (without HTML formatting)
        export_df = df.copy()
        export_df['Pickup Person'] = export_df['Pickup Person'].str.replace('<br>', '\n')
        export_df['Pickup Person'] = export_df['Pickup Person'].str.replace('<span class="bold-location">', '')
        export_df['Pickup Person'] = export_df['Pickup Person'].str.replace('</span>', '')
        export_df['Pickup Location'] = export_df['Pickup Location'].str.replace('<br>', '\n')

        # Display the dataframe with the new styling
        html_table = df.to_html(escape=False, index=False, classes='styled-table')
        st.write(html_table, unsafe_allow_html=True)

        st.markdown("---")

    # Button to download all merged dataframes in one Excel file
    if st.session_state.merged_dataframes:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            for idx, df in enumerate(st.session_state.merged_dataframes):
                df = df.drop("Number of People", axis=1)

                new_order = ['Pickup Person', 'Date', 'Pickup time', 'Pickup Location', 'Car Plate', 'Mobile']
                df = df[new_order]

                export_df = df.copy()
                export_df['Pickup Person'] = export_df['Pickup Person'].str.replace('<br>', '\n')
                export_df['Pickup Person'] = export_df['Pickup Person'].str.replace('<span class="bold-location">', '')
                export_df['Pickup Person'] = export_df['Pickup Person'].str.replace('</span>', '')
                export_df['Pickup Location'] = export_df['Pickup Location'].str.replace('<br>', '\n')
                export_df.to_excel(writer, sheet_name=f'Group {idx + 1}', index=False)

        st.download_button(
            label="Download Excel file with all groups",
            data=buffer.getvalue(),
            file_name="all_merged_dataframes.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_all"
        )
