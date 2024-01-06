import pandas as pd

def highlight_cell(df, header_row_index, id_columns, data_column_headers):
    # Create a DataFrame to store styles
    style_df = pd.DataFrame('', index=df.index, columns=df.columns)

    # Apply styles for the header row
    style_df.iloc[header_row_index] = 'background-color: lightblue;'

    # Apply styles for ID columns from the header row downwards
    for col in id_columns:
        for row in range(header_row_index, len(df)):
            style_df.iat[row, col] = 'background-color: lightgreen;'
            # For overlapping cells in header row and ID columns
            if col in df.columns and row == header_row_index:
                style_df.at[header_row_index, col] = 'background-color: darkseagreen;'

    # Apply styles for data_column_headers
    for row in data_column_headers:
        for col in range(len(id_columns), len(df.columns)):
            style_df.iat[row, col] = 'background-color: lightcoral;'
            # For overlapping cells in header row and data_column_headers
            if row == header_row_index:
                style_df.iat[row, col] = 'background-color: indianred;'  # A darker shade for overlap

    return style_df