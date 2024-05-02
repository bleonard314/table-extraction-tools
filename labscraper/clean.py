import pandas as pd
import os

def clean_extracted_data(dat, fill_pages=True, filter_name=None, filter_values=None, remove_na_cols=False, 
                         val_to_na=None, data_out=None, rem_non_ascii=True, return_data=True, fill_direction="down"):
    # Read data if it's a path to a file
    if isinstance(dat, str):
        if dat.endswith('.csv'):
            dat = pd.read_csv(dat)
        else:
            raise ValueError("Input file extension should be '.csv'!")

    # Remove non-ASCII characters if required
    if rem_non_ascii:
        dat = dat.applymap(lambda x: x.encode('ascii', 'replace').decode('ascii') if isinstance(x, str) else x)
    
    # Convert specified values to NaN, trim, and squish strings
    if val_to_na:
        dat = dat.replace(val_to_na, pd.NA)
    dat = dat.applymap(lambda x: " ".join(str(x).split()) if isinstance(x, str) else x)
    
    # Fill metadata across pages if specified
    if fill_pages:
        dat = dat.fillna(method=fill_direction, axis=0)
    
    # Filtering data
    if filter_name and filter_values:
        dat = dat[dat[filter_name].isin(filter_values)]
    elif filter_name:
        dat = dat.dropna(subset=[filter_name])
    
    # Remove columns with all NaN values if specified
    if remove_na_cols:
        dat = dat.dropna(axis=1, how='all')

    print(f"Successfully cleaned {len(dat)} rows of results.")

    # Save or return the cleaned data
    if data_out:
        os.makedirs(os.path.dirname(data_out), exist_ok=True)
        if data_out.endswith('.csv'):
            dat.to_csv(data_out, index=False)
        else:
            print("Unsupported file format for data_out. Only .csv is supported.")
            return dat
        
        if not return_data:
            return data_out

    return dat

# Example usage
dat = "path/to/your/extracted_data.csv"  # or pass directly a pandas DataFrame
cleaned_data = clean_extracted_data(dat, filter_name="units", filter_values=["mg/kg", "ug/L"])

# To print or save the cleaned data
print(cleaned_data)
