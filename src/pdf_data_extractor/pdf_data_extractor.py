import fitz
import pdfplumber
import PyPDF2
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector
import pandas as pd
import yaml
import inflection
import os
import logging

def find_keyword_pages(
    pdf_path,
    keywords_keep=None,
    keywords_remove=None,
    require_all=True,
    use_pdfplumber=False,
):
    """
    Find the page numbers containing the specified keywords in a PDF.

    Args:
    pdf_path (str): Path to the PDF file.
    keywords_keep (list, optional): A list of keywords to search for.
                                    If provided, pages must contain all these keywords.
    keywords_remove (list, optional): A list of keywords.
                                      Pages containing any of these keywords will be excluded.
    require_all (bool, optional): If True, all keywords must be present on a page.
                                  If False, any of the keywords can be present on a page.
                                  Defaults to True.
    use_pdfplumber (bool, optional): If True, use pdfplumber for PDF parsing. If False, use PyMuPDF (fitz).
                                      Defaults to True.

    Returns:
    list: A list of page numbers containing the keywords.
    """
    keyword_pages = []

    if use_pdfplumber:
        # Use pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            # Iterate over each page
            for page_num, page in enumerate(pdf.pages, start=1):
                print(f"Processing page {page_num}/{total_pages}...", end="\r")
                # Extract text from the page
                text = page.extract_text()

                # Check if page should be excluded based on keywords_remove
                if keywords_remove and any(
                    keyword in text for keyword in keywords_remove
                ):
                    continue

                # Check if all or any keywords_keep are present in the text
                if keywords_keep:
                    if require_all:
                        if all(keyword in text for keyword in keywords_keep):
                            keyword_pages.append(page_num)
                    else:
                        if any(keyword in text for keyword in keywords_keep):
                            keyword_pages.append(page_num)
                else:
                    # If no keywords to keep are provided, consider all pages
                    keyword_pages.append(page_num)
    else:
        # Use PyMuPDF (fitz)
        pdf_document = fitz.open(pdf_path)

        # Iterate over each page
        for page_num in range(pdf_document.page_count):
            print(
                f"Processing page {page_num + 1}/{pdf_document.page_count}...", end="\r"
            )

            # Extract text from the page
            page = pdf_document.load_page(page_num)
            text = page.get_text()

            # Check if page should be excluded based on keywords_remove
            if keywords_remove and any(keyword in text for keyword in keywords_remove):
                continue

            # Check if all or any keywords_keep are present in the text
            if keywords_keep:
                if require_all:
                    if all(keyword in text for keyword in keywords_keep):
                        keyword_pages.append(page_num + 1)  # Adjust to 1-based index
                else:
                    if any(keyword in text for keyword in keywords_keep):
                        keyword_pages.append(page_num + 1)  # Adjust to 1-based index
            else:
                # If no keywords to keep are provided, consider all pages
                keyword_pages.append(page_num + 1)  # Adjust to 1-based index

    return keyword_pages


def subset_pdf(pdf_path, pages_of_interest, output_path):
    """
    Subset a PDF to only contain the specified pages.

    Args:
    pdf_path (str): Path to the input PDF file.
    pages_of_interest (list): List of page numbers to keep in the subset PDF.
    output_path (str): Path to save the subset PDF.
    """
    # Open the input PDF file
    with open(pdf_path, "rb") as file:
        # Create a PDF reader object
        pdf_reader = PyPDF2.PdfReader(file)

        # Create a PDF writer object
        pdf_writer = PyPDF2.PdfWriter()

        # Iterate over pages in the input PDF
        for page_num in pages_of_interest:
            # Ensure the page number is within the valid range
            if 0 < page_num <= len(pdf_reader.pages):
                # Get the page from the input PDF
                page = pdf_reader.pages[page_num - 1]

                # Add the page to the output PDF
                pdf_writer.add_page(page)

        # Write the output PDF to a file
        with open(output_path, "wb") as output_file:
            pdf_writer.write(output_file)


def select_rectangle(image, display_resolution=100):
    """
    Allows the user to draw a rectangle on the image using a RectangleSelector.

    Args:
    image (numpy.ndarray): The image to be displayed.
    display_resolution (int, optional): The display resolution of the image. Defaults to 100.

    Returns:
    list: A list containing the coordinates of the drawn rectangle in the format [x1, y1, x2, y2].
    """
    # Global variable to store rectangle coordinates
    rect_coords = None

    # Function to handle the rectangle selection event
    def onselect(eclick, erelease):
        nonlocal rect_coords
        # Correctly capture the coordinates respecting the order
        x1, y1 = int(eclick.xdata), int(eclick.ydata)
        x2, y2 = int(erelease.xdata), int(erelease.ydata)
        rect_coords = [x1, y1, x2, y2]
        print(f"Rectangle from ({x1}, {y1}) to ({x2}, {y2})")

    # Create a figure and axis
    fig, ax = plt.subplots(figsize=(15, 10))

    # Display the image
    dpi = display_resolution
    extent = (0, image.width, image.height, 0)
    ax.imshow(image.original, cmap="gray", extent=extent)
    ax.set_title("Draw a rectangle (click and drag)")

    # Rectangle selector
    rect_selector = RectangleSelector(
        ax,
        onselect,
        useblit=True,
        button=[1],  # Only left mouse button
        minspanx=5,
        minspany=5,
        spancoords="pixels",
        interactive=True,
    )

    plt.show()

    # Apply scaling to the coordinates
    x0, x1 = sorted([rect_coords[0], rect_coords[2]])
    top, bottom = sorted([rect_coords[1], rect_coords[3]])

    # Create a bounding box
    bbox = (x0, top, x1, bottom)

    return bbox


def display_bbox(image, bbox, display_resolution=100, show=True):
    """
    Display a bounding box on the image.

    Args:
    image (numpy.ndarray): The image to be displayed.
    bbox (list): The bounding box coordinates in the format [x1, y1, x2, y2].
    display_resolution (int, optional): The display resolution of the image. Defaults to 100.
    """
    # Create a figure and axis
    fig, ax = plt.subplots(figsize=(15, 10))

    # Display the image
    dpi = display_resolution
    extent = (0, image.width, image.height, 0)
    ax.imshow(image.original, cmap="gray", extent=extent)

    # Add the bounding box to the image
    rect = plt.Rectangle(
        (bbox[0], bbox[1]),
        bbox[2] - bbox[0],
        bbox[3] - bbox[1],
        edgecolor="r",
        facecolor="none",
    )
    ax.add_patch(rect)

    if show:
        plt.show()
    else:
        return fig, ax


def expand_dataframe_with_metadata(df_lines, patterns):
    """
    Expand a DataFrame with metadata columns based on configured patterns.

    Args:
    df_line (pandas.DataFrame): The DataFrame containing lines of metadata text.
    patterns (list): A list of dictionaries, each specifying a pattern to extract metadata.

    Returns:
    pandas.DataFrame: The expanded DataFrame with metadata columns.
    pandas.DataFrame: The DataFrame containing extracted metadata.
    """
    # Initialize empty dataframe to store expanded lines and metadata
    df_expanded = pd.DataFrame()
    df_metadata = pd.DataFrame()

    # Apply each configured pattern to extract data into new columns
    for item in patterns:
        # Extract data based on the pattern and assign column names based on the config
        temp_columns = df_lines["text"].str.extract(item["pattern"])
        temp_columns.columns = item["columns"]

        # Filter to only non-null values and populate metadata dataframe
        for column in temp_columns.columns:
            temp_df = temp_columns[column].dropna()
            df_metadata = pd.concat(
                [
                    df_metadata,
                    pd.DataFrame(
                        {
                            "Line Number": temp_df.index+1,
                            "Column Name": column,
                            "Column Value": temp_df.values,
                        }
                    ),
                ]
            )

        # Fill down the values to replace NaNs if fill direction is down
        if item["fill_direction"] == "down":
            temp_df = temp_columns.ffill().infer_objects(copy=False)
        else:
            temp_df = temp_columns.bfill().infer_objects(copy=False)

        # Concatenate the extracted columns to the expanded dataframe
        df_expanded = pd.concat([df_expanded, temp_df], axis=1)

    return df_expanded, df_metadata


def apply_column_filters(df, column_filters):
    """
    Apply column filters to a DataFrame based on the specified configurations.

    Args:
    df (pandas.DataFrame): The DataFrame to be filtered.
    column_filters (list): A list of dictionaries, each specifying a column filter.

    Returns:
    pandas.DataFrame: The filtered DataFrame.
    """
    # Create a copy of the dataframe for filtering
    df_filtered = df.copy()

    # Apply filters from configuration
    for column_filter in column_filters:
        column = column_filter["column"]
        regex = column_filter["regex"]
        df_filtered = df_filtered[df_filtered[column].str.match(regex)]

    return df_filtered

def extract_fixed_text_areas(page, areas):

    # Initialize a dictionary to store text extracted from the current page
    page_text = {}

    # Extract text from each fixed text area defined in the config
    for area_name, bbox in areas.items():
        area_text = page.within_bbox(bbox).extract_text()
        
        # Store the extracted text in the page_text dictionary
        page_text[area_name] = area_text

    return page_text

def extract_data_from_pdf(config_path, pdf_path, output_dir="output", write_overly=False, log_file_path=None):
    """
    Extract data from a PDF file based on the specified configuration.

    Args:
    config_path (str): Path to the YAML configuration file.
    pdf_path (str): Path to the PDF file.
    output_dir (str, optional): Output directory for saving extracted data. Defaults to "lab_pdf_scraper".
    log_file_path (str, optional): Path to save the extraction log file. Defaults to None.
    multithreading (bool, optional): Enable multithreading. Defaults to False.

    Returns:
    pandas.DataFrame: DataFrame containing the extracted data.
    """
    # Setup logging
    if log_file_path:
        logging.basicConfig(filename=log_file_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Open the config '.yaml' file and load the configuration
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)

    # Set bounding box and add left and right margins from the bounding box to the column locations
    bbox = config["table_area"]
    
        # Define the table settings
    table_settings = {
        "vertical_strategy": "explicit",
        "explicit_vertical_lines": [bbox[0]] + config['table_columns'] + [bbox[2]],
        "horizontal_strategy": "text",
        "snap_y_tolerance": 5,
        "intersection_x_tolerance": 10,
    }

    # Define the line settings (same as table_settings but without the explicit_vertical_lines)
    line_settings = table_settings.copy()
    line_settings["explicit_vertical_lines"] = [bbox[0]] + [bbox[2]]

    # Find pages with keywords
    keywords_keep = config["page_selection"]["keywords_to_keep"]
    keywords_remove = config["page_selection"]["keywords_to_remove"]
    require_all = config["page_selection"]["require_all_keywords"]
    pages_with_keywords = find_keyword_pages(pdf_path, keywords_keep, keywords_remove, require_all)

    # Create output directory if it doesn't exist
    output_dir_path = os.path.join(output_dir, os.path.splitext(os.path.basename(pdf_path))[0])
    os.makedirs(output_dir_path, exist_ok=True)

    # Create output path by adding "_subset" before the file extension and saving to the output dir
    output_path = os.path.join(output_dir_path, os.path.basename(pdf_path).replace(".pdf", "_subset.pdf"))
    subset_pdf(pdf_path, pages_with_keywords, output_path)

    # Initialize dataframe for extracted data
    df_extracted = pd.DataFrame()
    
    # Initialize dataframes for normalized data tables, metadata headers, and fixed text areas
    df_tables = pd.DataFrame()
    df_headers = pd.DataFrame()
    df_fixed = pd.DataFrame()

    with pdfplumber.open(output_path) as pdf:
        total_pages = len(pdf.pages)
        for page_num, page in enumerate(pdf.pages, start=1):
            logging.info(f"Processing page {page_num}/{total_pages}...")
            
            # If write overlay is set to True, write the overlay image to the output directory (placeholder)
            # if write_overly:
            #     overlay_image = page.to_image()
            #     overlay_image.save(os.path.join(output_dir_path, f"page_{page_num}_overlay.png"), format="PNG")
            
            # Extract table from cropped page and convert the extracted data to a dataframe with column names
            page_cropped = page.crop(bbox)
            extracted_table = page_cropped.extract_table(table_settings)
            df_table = pd.DataFrame(extracted_table[0:])
            df_table.columns = config['table_column_names']
            df_table.insert(0, 'Line Number', df_table.index+1) # Add line number (row index) as first column of dataframe
            df_table.insert(0, 'Page Number', page_num) # Add page number as first column of dataframe
            df_tables = pd.concat([df_tables, df_table], ignore_index=True)
            
            # Extract text line by line from the cropped page and concat with dataframe
            extracted_lines = page_cropped.extract_table(line_settings)
            df_lines = pd.DataFrame(extracted_lines, columns=['text'])
                        
            # Expand the dataframe with metadata using patterns from the config file
            df_expanded, df_metadata = expand_dataframe_with_metadata(df_lines, config['metadata_patterns'])
            df_metadata.insert(0, 'Page Number', page_num) # Add page number as first column of dataframe
            df_headers = pd.concat([df_headers, df_metadata], ignore_index=True) # Concatenate metadata dataframe
            
            # Extract fixed position text from the cropped page
            extracted_text = extract_fixed_text_areas(page, config['fixed_text_areas'])
            df_text = pd.DataFrame(extracted_text, index=[0])
            
            # Combine the extracted data into a single dataframe
            df_combined = pd.concat([df_expanded, df_table], axis=1) # Combine the expanded dataframe with the table dataframe
            df_combined = pd.concat([df_combined, pd.concat([df_text] * len(df_combined), ignore_index=True)], axis=1) # Combine the combined dataframe with the fixed text dataframe
            df_combined.insert(0, 'Source Page Number', pages_with_keywords[page_num-1]) # Add page number as first column of dataframe
            df_text.insert(0, 'Page Number', page_num) # Add page number as first column of dataframe
            df_fixed = pd.concat([df_fixed, df_text], ignore_index=True) # Concatenate fixed text dataframe
            df_extracted = pd.concat([df_extracted, df_combined], ignore_index=True) # Concatenate the combined dataframe

    # Create dataframe matching "Page Number" to "Source Page Number"
    df_pages = pd.DataFrame(pages_with_keywords, columns=['Source Page Number'])
    df_pages['Page Number'] = df_pages.index + 1
    df_pages = df_pages[['Page Number', 'Source Page Number']]

    # Save the extracted data to a CSV file and an Excel file
    output_basepath = os.path.join(output_dir_path, os.path.splitext(os.path.basename(pdf_path))[0])
    df_extracted.to_csv(output_basepath + "_extracted.csv", index=False)
    df_extracted.to_excel(output_basepath + "_extracted.xlsx", index=False)
    df_extracted.to_pickle(output_basepath + "_extracted.pkl")
    
    # If there are any column filters, apply them
    if 'column_filters' in config['post_processing']:
        df_cleaned = apply_column_filters(df_extracted, config['post_processing']['column_filters'])
        df_tables = apply_column_filters(df_tables, config['post_processing']['column_filters'])

    # If convert column names to snake case is set to True, convert the column names to snake case
    if config['post_processing']['convert_column_names']:
        df_cleaned.columns = [inflection.underscore(col) for col in df_combined.columns]
        df_tables.columns = [inflection.underscore(col) for col in df_tables.columns]
        df_headers.columns = [inflection.underscore(col) for col in df_headers.columns]
        df_fixed.columns = [inflection.underscore(col) for col in df_fixed.columns]
        df_pages.columns = [inflection.underscore(col) for col in df_pages.columns]
    
    # Try to automatically convert column data types
    if config['post_processing']['convert_data_types']:
        df_cleaned = df_cleaned.convert_dtypes()
        df_tables = df_tables.convert_dtypes()
        df_fixed = df_fixed.convert_dtypes()        
        
    # Save the cleaned data to a CSV file, an Excel file, and a Pickle file
    df_cleaned.to_csv(output_basepath + "_cleaned.csv", index=False)
    df_cleaned.to_excel(output_basepath + "_cleaned.xlsx", index=False)
    df_cleaned.to_pickle(output_basepath + "_cleaned.pkl")

    # Write tables and headers to separate Excel Worksheets within the same Excel file
    with pd.ExcelWriter(output_basepath + "_normalized.xlsx") as writer:
        df_tables.to_excel(writer, sheet_name='Tables', index=False)
        df_headers.to_excel(writer, sheet_name='Headers', index=False)
        df_fixed.to_excel(writer, sheet_name='Fixed', index=False)
        df_pages.to_excel(writer, sheet_name='Pages', index=False)
    
    # Combine the tables and headers in a list and write to a Pickle file
    pd.to_pickle([df_tables, df_headers, df_pages], output_basepath + "_normalized.pkl")   
    
    logging.info("Extraction completed.")
    return df_cleaned, df_tables, df_headers