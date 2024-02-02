import tabula
import yaml
import pandas as pd
from PyPDF2 import PdfReader, PdfWriter
import re

def extract_tables_from_pdf(pdf_path, output_path, start_page, end_page, title_regex): 
    # Create a PDF reader object
    reader = PdfReader(pdf_path)

    # Create a PDF writer object
    writer = PdfWriter()

    # Extract text from each page to find table titles
    table_titles = []
    for i in range(start_page - 1, end_page):
        page = reader.pages[i]
        page_text = page.extract_text()
        title_match = re.search(title_regex, page_text, re.DOTALL)
        table_title = title_match.group(0) if title_match else "Unknown Title"
        table_title = clean_text(table_title)
        table_titles.append(table_title)
        writer.add_page(page)

    # Create a temporary PDF file with the specified pages
    temp_pdf_path = "temp_extracted_pages.pdf"
    with open(temp_pdf_path, "wb") as f:
        writer.write(f)

    # Extract tables from the temporary PDF file
    tables = tabula.read_pdf(temp_pdf_path, pages="all", multiple_tables=True, lattice=True, pandas_options={'header': None}, area=(0, 0, 100, 100), columns=(0, 100))
    
    # Remove any empty tables
    tables = [table for table in tables if len(table) > 0]
    
    # Error if the number of tables extracted does not match the number of table titles
    if len(tables) != len(table_titles):
        raise Exception(f"Number of tables extracted ({len(tables)}) does not match the number of table titles ({len(table_titles)}).")
    
    # Combine the tables into a single DataFrame
    for i, table in enumerate(tables):
        table.to_csv(f"{output_path}_{i+1}.csv", index=False)
        
    print(f"Extracted {len(tables)} tables.")

# Define a function to shift a row to the right (adjust the logic as per your data)
def shift_row_right(row):
    # Create a new row with an initial None value and then the existing row values except the last one
    new_row = pd.Series([None] * len(row), index=row.index)
    for i in range(1, len(row)):
        new_row.iloc[i] = row.iloc[i - 1]
    return new_row

def clean_text(text):
    # Remove line breaks (\n and \r), replace them with a space
    text = text.replace('\n', ' ').replace('\r', ' ')
    # Remove line breaks and extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove leading and trailing whitespace
    text = text.strip()
    return text

def clean_data(cell):
    if isinstance(cell, str):
        cell = clean_text(cell)
    return cell
