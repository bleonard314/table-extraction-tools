import streamlit as st
import pandas as pd
import os

from table_extraction_tools.crosstab_normalization import normalize_crosstab

from config_utils import load_config, apply_config, save_config, get_config, get_config_data
from data_utils import load_example_csv, combine_columns_with_names, get_column_group_names_or_count
from visualization_utils import highlight_cell

# config_keys are the keys of the session_state you want to save/load
config_keys = ["id_columns", "data_column_names", "header_row_index", "data_column_headers", "data_rows", "data_columns"]

# Define the legend
legend = """
#### Legend
- <span style='color: lightblue; font-weight: bold;'>Light Blue</span>: Header Row
- <span style='color: lightgreen; font-weight: bold;'>Light Green</span>: ID Columns (from Header Row downwards)
- <span style='color: lightcoral; font-weight: bold;'>Light Coral</span>: Data Column Headers
- <span style='color: darkseagreen; font-weight: bold;'>Dark Sea Green</span>: Overlapping cells in Header Row and ID Columns
- <span style='color: indianred; font-weight: bold;'>Indian Red</span>: Overlapping cells in Header Row and Data Column Headers
"""

# Initialize layout
st.title("Normalize Crosstab DataFrame")
sidebar = st.sidebar
main_area = st.container()
        
# Sidebar for file upload and basic configurations
with sidebar:
    st.header("Configuration")

    # Example CSV files
    example_files = ["example_01.csv", "example_02.csv"]  # Update with your file names

    # File uploader and example selection for the DataFrame
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    example_selection = st.selectbox("Or choose an example CSV file", [""] + example_files)
                
    # Load the DataFrame
    df = None
    file_loaded = False
    if uploaded_file is not None:
        # Load DataFrame from file
        df = pd.read_csv(uploaded_file, header=None)
        file_loaded = True     
    elif example_selection:
        # Load example from the data folder
        df = load_example_csv(f"data/{example_selection}")
        file_loaded = True
        
    if file_loaded and 'config_applied' not in st.session_state:
        st.session_state['config_applied'] = True
        if uploaded_file:
            # Load default configuration
            config_path = f"config/default.json"
            example_config = load_config(config_path)
            apply_config(example_config)
        
        elif example_selection:
            # Load example configuration
            config_path = f"config/{os.path.splitext(example_selection)[0]}.json"
            example_config = load_config(config_path)
            apply_config(example_config)
            
    # Reset the flag when the selection changes
    if example_selection != st.session_state.get('last_example_selection', ''):
        st.session_state.pop('config_applied', None)
    st.session_state['last_example_selection'] = example_selection

    # Now create the UI elements using session_state for default values
    if df is not None:        
        # Set header row index and ID columns
        header_row_index = st.slider("Select Header Row Index", 0, len(df)-1, key="header_row_index")
        id_columns = st.multiselect("Select ID Columns", options=list(df.columns), key="id_columns")
        
        # Optional names for ID columns within an expander
        with st.expander("Optionally, provide names for each ID column", expanded=False):
            id_column_names = {}
            for col in id_columns:
                name = st.text_input(f"Name for column {col}", key=f"id_columns-name_{col}")
                if name:  # Only add if a name was entered
                    id_column_names[col] = name
        
        data_column_headers = st.multiselect("Select Data Column Headers", options=list(df.index), key="data_column_headers")

        # Optional names for Data Column Headers within an expander
        with st.expander("Optionally, provide names for each Data Column Header", expanded=False):
            data_column_header_names = {}
            for row_index in data_column_headers:
                name = st.text_input(f"Name for row {row_index}", key=f"data_column_headers-name_{row_index}")
                if name:  # Only add if a name was entered
                    data_column_header_names[row_index] = name
        
        # Input for column_group_count
        max_group_count = len(df.columns) - len(id_columns)
        column_group_count = st.number_input("Column Group Count", min_value=1, max_value=max_group_count, value=1)
        
        # Optional names for Column Groups within an expander
        if df is not None:
            with st.expander("Optionally, provide names for Column Groups", expanded=False):
                column_group_names = []
                for i in range(column_group_count):
                    name = st.text_input(f"Name for Column Group {i + 1}", key=f"column_group-name_{i}")
                    column_group_names.append(name)
                
        # Optional input for data_rows as a range
        enable_data_rows = st.checkbox("Enable Data Rows Range Selection", value=False)
        if enable_data_rows:
            data_rows = st.slider("Select Range for Data Rows", 
                                    min_value=0, 
                                    max_value=len(df) - 1, 
                                    value=(0, len(df) - 1))
        else:
            data_rows = None
        
        # Optional input for data_columns selection
        enable_data_columns = st.checkbox("Enable Data Columns Selection", value=False)
        if enable_data_columns:
            all_columns = list(range(len(df.columns)))
            data_columns = st.multiselect("Select Data Columns", options=all_columns, default=all_columns)
        else:
            data_columns = None
        
        # Load configuration button
        st.write("Load Custom Configuration")
        uploaded_config_file = st.file_uploader("Upload a JSON configuration file", type='json')
        if uploaded_config_file is not None:
            custom_config = load_config(uploaded_config_file)
            if custom_config:
                apply_config(custom_config)
                st.success("Configuration loaded successfully.")
            
        # Get current config
        current_config = get_config(
            config_keys=config_keys,
            id_columns=combine_columns_with_names(id_columns, id_column_names),
            data_column_names=get_column_group_names_or_count(column_group_names, column_group_count),
            header_row_index=header_row_index,
            data_column_headers=combine_columns_with_names(data_column_headers, data_column_header_names),
            data_columns=data_columns,
            data_rows=data_rows
        )
        
        # Get config Data
        config_data = get_config_data(current_config)
        
        # Save configuration button
        config_name = st.text_input("Configuration file name", "config.json")
        st.download_button(
            label="Download Configuration File",
            data=config_data,
            file_name=config_name,
            mime="application/json"
        )

# Main area for DataFrame interaction
with main_area:
            
    if df is not None:
        # Apply highlighting
        styled_df = df.style.apply(lambda x: highlight_cell(df, header_row_index, id_columns, data_column_headers), axis=None)
        
        # Display the DataFrame
        st.write("Uploaded DataFrame:")
        st.dataframe(styled_df)
        # st.table(styled_df) # Alternative to dataframe
        
        # Display the legend
        st.markdown(legend, unsafe_allow_html=True)

        # Process DataFrame button
        if st.button('Process DataFrame'):

            # Call function to normalize the DataFrame
            result_df = normalize_crosstab(df, **current_config)

            # Display result
            st.write("Processed DataFrame:")
            st.dataframe(result_df)
            # st.table(result_df) # Alternative to dataframe