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

def process_pickup_info(input_data, default_time):
    def parse_input(input_data):
        entries = input_data.strip().split('\n')
        customer_list = []
        pickup_date = None
        for entry in entries:
            if entry.lower().startswith("pickup time:"):
                pickup_date = re.search(r'\d+(?:st|nd|rd|th)?\s+\w+', entry)
                pickup_date = pickup_date.group() if pickup_date else None
            elif entry[0].isdigit() and "Ex:" not in entry:
                parts = re.split(r'\s*[-~]\s*', entry.strip(), maxsplit=3)
                if len(parts) > 1:
                    person = parts[1]
                    location = normalize_location(parts[2]) if len(parts) > 2 else ''
                    time = parts[3] if len(parts) > 3 else default_time
                    time = re.sub(r'\(.*?\)', '', time).strip().lower()
                    customer_list.append(
                        {'Pickup Person': person, 'Pickup time': time, 'Pickup Location': location, 'Date': pickup_date})
        return customer_list

    def normalize_location(location):
        return location.strip().lower()

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


def merge_dataframes(dataframes, cars_info):
    merged = {}

    for (time, location, date), df in dataframes.items():
        total_people = df['Number of People'].iloc[0]
        people_list = df['Pickup Person'].iloc[0].split('; ')

        for car_info in cars_info.get((time, location), []):
            car_plate, mobile, capacity = car_info
            if not car_plate or not mobile:  # Skip if car_plate or mobile is empty
                continue

            key = (car_plate, mobile, capacity)

            if key not in merged:
                merged[key] = {
                    'Pickup Person': [],
                    'Date': date,
                    'Pickup Location': [],
                    'Car Plate': car_plate,
                    'Mobile': mobile,
                    'Remaining Capacity': capacity
                }

            if merged[key]['Remaining Capacity'] > 0:
                people_for_this_car = people_list[:min(merged[key]['Remaining Capacity'], len(people_list))]
                people_list = people_list[len(people_for_this_car):]

                pickup_time = pd.to_datetime(time, format='%I:%M%p', errors='coerce')

                merged[key]['Pickup Person'].append(
                    f"{location.capitalize()}: {', '.join(people_for_this_car)} ({len(people_for_this_car)} people)")
                merged[key]['Pickup Location'].append(
                    (pickup_time, f"{pickup_time.strftime('%I:%M%p').lower()} at {location.capitalize()}"))
                merged[key]['Remaining Capacity'] -= len(people_for_this_car)

            if not people_list:
                break

    merged_dataframes = []
    for key, entry in merged.items():
        entry['Pickup Person'] = format_pickup_person('\n'.join(entry['Pickup Person']))

        # Sort Pickup Location chronologically and format
        sorted_locations = sorted(entry['Pickup Location'], key=lambda x: x[0])
        entry['Pickup Location'] = '<br>'.join([loc[1] for loc in sorted_locations])

        del entry['Remaining Capacity']
        merged_dataframes.append(pd.DataFrame([entry]))

    return merged_dataframes


st.title('Pickup Information Processor')

if 'input_data' not in st.session_state:
    st.session_state.input_data = """Pickup time: 23th July 8:05~8:10AM
1- Ex: Eric peng-Ritz -9:00AM(Remark Special time)
2- Sam Shi-Westin
3- Nick Guo - park hyatt
4- Nishant Jayant - ritz
5- Paul Chow - Ritz
6- Enki xie - Park Hyatt
7- Jolley W - Ritz
8- Audrey Louchart - Ritz
9- Marc Vivant - Park Hyatt
11- Steven Z. - Park Hyatt"""

if 'default_time' not in st.session_state:
    st.session_state.default_time = '8:00am'

input_data = st.text_area('Enter pickup information (one entry per line):', 
                          height=300, key="input_data_1")
default_time = st.text_input('Enter default pickup time (e.g., 8:00am):', st.session_state.default_time)

if 'dataframes' not in st.session_state:
    st.session_state.dataframes = {}

if 'merged_dataframes' not in st.session_state:
    st.session_state.merged_dataframes = []

if 'cars_info' not in st.session_state:
    st.session_state.cars_info = {}

if st.button('Process Pickup Information'):
    if input_data:
        st.session_state.dataframes = process_pickup_info(input_data, default_time)
        st.session_state.merged_dataframes = []
        st.session_state.cars_info = {}
        st.session_state.input_data = input_data
        st.session_state.default_time = default_time
        st.experimental_rerun()

if st.session_state.dataframes:
    for (time, location, date), df in st.session_state.dataframes.items():
        st.subheader(f"Pickup at {time} from {location.capitalize()} on {date}")

        df_hidden_index = df.style.hide(axis='index')
        styled_df = df_hidden_index.set_properties(**{
            'background-color': '#dceefb',
            'color': 'black',
            'border-color': 'white'
        }).set_table_styles([{
            'selector': 'thead th',
            'props': [('background-color', '#3b9cd9'), ('color', 'white')]
        }, {
            'selector': 'tbody tr:nth-child(even)',
            'props': [('background-color', '#eaf5fc')]
        }, {
            'selector': 'tbody tr:hover',
            'props': [('background-color', '#c4e1f9')]
        }])

        st.markdown(styled_df.to_html(), unsafe_allow_html=True)

        st.markdown("Enter Car Information:")
        num_cars = st.number_input(f"Number of cars for {time} at {location}", min_value=1, value=1,
                                   key=f"num_cars_{time}_{location}")

        cars_info = []
        for i in range(num_cars):
            col1, col2, col3 = st.columns(3)
            with col1:
                car_plate = st.text_input(f"Car Plate #{i + 1}", key=f"car_plate_{time}_{location}_{i}")
            with col2:
                mobile = st.text_input(f"Mobile #{i + 1}", key=f"mobile_{time}_{location}_{i}")
            with col3:
                capacity = st.number_input(f"Capacity #{i + 1}", min_value=1, value=1,
                                           key=f"capacity_{time}_{location}_{i}")
            cars_info.append((car_plate, mobile, capacity))

        st.session_state.cars_info[(time, location)] = cars_info

    st.markdown("---")
    st.subheader("Merge Dataframes")
    if st.button('Merge Dataframes', key="merge_button", help="Click to merge all processed dataframes"):
        st.session_state.merged_dataframes = merge_dataframes(st.session_state.dataframes, st.session_state.cars_info)
        st.success("Dataframes merged successfully.")

    st.markdown("---")
    st.subheader("Merged Dataframes")

    for idx, df in enumerate(st.session_state.merged_dataframes):
        st.markdown(f"### Group {idx + 1}")

        new_pickup_location = st.text_input(f"Edit Pickup Location for Group {idx + 1}",
                                            value=df['Pickup Location'].iloc[0],
                                            key=f"pickup_location_{idx}")

        df.at[0, 'Pickup Location'] = new_pickup_location

        styled_merged_df_no_index = df.style.hide(axis='index')
        styled_merged_df_final = styled_merged_df_no_index.set_properties(**{
            'background-color': '#dceefb',
            'color': 'black',
            'border-color': 'white'
        }).set_table_styles([{
            'selector': 'thead th',
            'props': [('background-color', '#3b9cd9'), ('color', 'white')]
        }, {
            'selector': 'tbody tr:nth-child(even)',
            'props': [('background-color', '#eaf5fc')]
        }, {
            'selector': 'tbody tr:hover',
            'props': [('background-color', '#c4e1f9')]
        }])

        st.markdown(styled_merged_df_final.to_html(), unsafe_allow_html=True)

    if st.session_state.merged_dataframes:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            for idx, df in enumerate(st.session_state.merged_dataframes):
                # Create a copy of the dataframe to modify for Excel export
                export_df = df.copy()

                # Remove HTML formatting from 'Pickup Person' and 'Pickup Location' columns
                export_df['Pickup Person'] = export_df['Pickup Person'].str.replace('<br>', '\n')
                export_df['Pickup Person'] = export_df['Pickup Person'].str.replace('<span class="bold-location">', '')
                export_df['Pickup Person'] = export_df['Pickup Person'].str.replace('</span>', '')

                export_df['Pickup Location'] = export_df['Pickup Location'].str.replace('<br>', '\n')

                # Write the modified dataframe to Excel
                export_df.to_excel(writer, sheet_name=f'Group {idx + 1}', index=False)

                # Adjust column widths
                worksheet = writer.sheets[f'Group {idx + 1}']
                for i, col in enumerate(export_df.columns):
                    max_len = max(export_df[col].astype(str).map(len).max(), len(col)) + 2
                    worksheet.set_column(i, i, max_len)

        st.download_button(
            label="Download Excel file with all groups",
            data=buffer.getvalue(),
            file_name="all_merged_dataframes.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
