import pandas as pd
import numpy as np

def normalize_crosstab(df,
    id_columns,
    data_column_names,
    header_row_index=None,
    data_column_headers=None,
    data_rows=None,
    data_columns=None,
    split_columns=None):
    """
    Transforms a cross-tabulated dataframe into a flattened "normalized" format suitable for database ingestion or further analysis.

    Parameters:
    df (pd.DataFrame): The original dataframe containing crosstabbed data.
    id_columns (list of int or dict): Column indices or names in the dataframe that should be preserved in the flattened format.
    data_column_names (list of int): Names of columns in the header row or an integer indicating the number of columns to use from the header row.
    header_row_index (int, optional): The index of the row used for 'id_columns' and 'data_column_names' values if a list of integers is supplied. Defaults to the last row in 'data_column_headers' if not provided.
    data_column_headers (dict of {int: str}): A dictionary mapping indices of rows containing column headers to their names.
    data_rows (list of int, optional): Row indices indicating which rows contain the data to be included in the flattened dataframe. Defaults to all rows after the last header row.
    data_columns (list of int, optional): Column indices that contain the data to be included in the flattened dataframe. Defaults to all columns after 'id_columns'.

    Returns:
    pd.DataFrame: A transformed dataframe in a flat, tabular format.
    """
    # Map value columns to their names
    if not isinstance(id_columns, dict):
        id_columns = {val: df.iloc[header_row_index, val] for val in id_columns}
        
    # Assign names to header rows
    if not isinstance(data_column_headers, dict):
        data_column_headers = {row: df.iloc[row, max(list(id_columns.keys()))] for row in data_column_headers}
    
    # If no header row index is provided, use the last row in data_column_headers
    if header_row_index is None and data_column_headers is not None:
        header_row_index = max(data_column_headers.keys())

    # Default data rows and columns if not provided
    if data_rows is None:
        data_rows = range(max(list(data_column_headers.keys())+[header_row_index]) + 1, len(df))

    if data_columns is None:
        data_columns = range(len(id_columns), df.shape[1])

    # Set names for columns in the header
    if data_column_names is None:
        data_column_names = df.iloc[header_row_index, data_columns].tolist()
    elif isinstance(data_column_names, int):
        data_column_names = df.iloc[header_row_index, data_columns[:data_column_names]].tolist()*len(data_columns)
    elif isinstance(data_column_names, list):
        data_column_names = data_column_names*len(data_columns)

    # Extract and reshape headers
    headers = df.iloc[list(data_column_headers.keys()), data_columns].copy()
    headers = headers.T.ffill().T # Transpose, fill NaN values horizontally, and transpose back
    headers = headers.melt(ignore_index=False).reset_index()
    headers['index'] = headers['index'].map(data_column_headers)
    headers = headers.pivot(index='variable', columns='index', values='value').reset_index()
    headers = headers.rename(columns={'variable': 'column_index'})
    headers['variable'] = data_column_names

    # Extract and reshape body data
    body = df.iloc[data_rows, list(id_columns.keys()) + list(data_columns)].copy()
    body = pd.melt(body, id_vars=id_columns.keys(), var_name='column_index', value_name='value')
    body = body.rename(columns=id_columns)

    # Merge headers and body for final output
    flattened_df = body.join(headers.set_index('column_index'), on='column_index')
    flattened_df = flattened_df.drop(columns=['column_index'])
    flattened_df = flattened_df.pivot_table(index=flattened_df.columns.drop(['value', 'variable']).tolist(), columns='variable', values='value', aggfunc='first').reset_index()
    
    # Splitting the column
    if split_columns is not None:
        flattened_df[split_columns['new_column_names']] = flattened_df[split_columns['name']].str.split(split_columns['split_on'], expand=True)
        flattened_df = flattened_df[flattened_df.columns.drop(split_columns['new_column_names']).tolist() + split_columns['new_column_names']]

    return flattened_df

