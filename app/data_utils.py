import pandas as pd

def load_example_csv(file_name):
    """ Load an example CSV file """
    return pd.read_csv(file_name, header=None)

def combine_columns_with_names(columns, names):
    if not names or all(name == '' for name in names.values()):
        return columns
    return {col: names.get(col, col) for col in columns}

def get_column_group_names_or_count(column_group_names, column_group_count):
    # If names are provided and not empty, return the names
    if column_group_names and any(name.strip() for name in column_group_names):
        return [name.strip() for name in column_group_names if name.strip()]
    
    # If no names are provided, return a list of numbers based on column_group_count
    return [f"Group {i+1}" for i in range(column_group_count)]