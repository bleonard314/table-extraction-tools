import fitz
import pdfplumber
import PyPDF2
import matplotlib.pyplot as plt
from pathlib import Path
from matplotlib.widgets import RectangleSelector
import pandas as pd
import yaml
import os
import logging

class PDFExtractionConfig:
    def __init__(self, config_path=None):
        # Load configuration from a YAML file
        if config_path:
            with open(config_path, 'r') as file:
                self.config = yaml.safe_load(file)
        else:
            self.config = self.create_blank_config()

        self._load_config_attributes()

    @staticmethod
    def create_blank_config():
        """Generate a blank configuration with default structure."""
        return {
            "page_selection": {
                "explicit_pages": None,
                "require_all_keywords": False,
                "keywords_to_keep": [],
                "keywords_to_remove": []
            },
            "table_area": [0, 0, 0, 0],
            "table_columns": [],
            "table_column_names": [],
            "metadata_patterns": [],
            "fixed_text_areas": {},
            "post_processing": {
                "explicit_line_numbers": None,
                "column_filters": [],
                "convert_column_names": False,
                "convert_data_types": False
            }
        }
    
    def _load_config_attributes(self):
        self._page_selection = self.config.get('page_selection', {})
        self._table_area = self.config.get('table_area', [])
        self._table_columns = self.config.get('table_columns', [])
        self._table_column_names = self.config.get('table_column_names', [])
        self._metadata_patterns = self.config.get('metadata_patterns', [])
        self._fixed_text_areas = self.config.get('fixed_text_areas', {})
        self._post_processing = self.config.get('post_processing', {})

    @property
    def page_selection(self):
        return self._page_selection

    @page_selection.setter
    def page_selection(self, value):
        self._page_selection = value
        self.config['page_selection'] = value

    @property
    def table_area(self):
        return self._table_area

    @table_area.setter
    def table_area(self, value):
        self._table_area = value
        self.config['table_area'] = value

    @property
    def table_columns(self):
        return self._table_columns
    
    @table_columns.setter
    def table_columns(self, value):
        self._table_columns = value
        self.config['table_columns'] = value
    
    @property
    def table_column_names(self):
        return self._table_column_names
    
    @table_column_names.setter
    def table_column_names(self, value):
        self._table_column_names = value
        self.config['table_column_names'] = value
    
    @property
    def metadata_patterns(self):
        return self._metadata_patterns
    
    @metadata_patterns.setter
    def metadata_patterns(self, value):
        self._metadata_patterns = value
        self.config['metadata_patterns'] = value
    
    @property
    def fixed_text_areas(self):
        return self._fixed_text_areas
    
    @fixed_text_areas.setter
    def fixed_text_areas(self, value):
        self._fixed_text_areas = value
        self.config['fixed_text_areas'] = value
    
    @property
    def post_processing(self):
        return self._post_processing
    
    @post_processing.setter
    def post_processing(self, value):
        self._post_processing = value
        self.config['post_processing'] = value

    def save_to_yaml(self, output_path):
        """Save the current configuration to a YAML file."""
        with open(output_path, 'w') as file:
            yaml.safe_dump(self.config, file, sort_keys=False)

    def _validate_area(self, area):
        """Validate that a bounding box is in [x0, y0, x1, y1] format with x0 < x1 and y0 < y1."""
        if not isinstance(area, list) or len(area) != 4:
            raise ValueError("Bounding box must be a list with exactly four coordinates [x0, y0, x1, y1].")
        x0, y0, x1, y1 = area
        if not (isinstance(x0, (int, float)) and isinstance(y0, (int, float)) and
                isinstance(x1, (int, float)) and isinstance(y1, (int, float))):
            raise ValueError("Coordinates must be numeric values.")
        if not (x0 < x1 and y0 < y1):
            raise ValueError("Bounding box coordinates should follow x0 < x1 and y0 < y1.")

    def validate(self):
        # Validate the whole configuration using existing checks
        # This would involve calling _validate_area for relevant attributes etc.
        return True
    
    def select_rectangle(image):
        """
        Allows the user to draw a rectangle on the image using a RectangleSelector.

        Args:
        image (numpy.ndarray): The image to be displayed.

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
        extent = (0, image.width, image.height, 0)
        ax.imshow(image, cmap="gray", extent=extent)
        ax.set_title("Draw a rectangle (click and drag)")

        # Rectangle selector
        RectangleSelector(
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
    
    @staticmethod
    def metadata_patterns_from_lines(page, line_numbers, terminator_text=":", fill_direction="down"):
        page_lines = page.extract_text_lines()
        header_lines = page_lines[line_numbers]
        metadata_patterns = []

        for line in header_lines:
            column_names = []
            page_cropped = page.crop(list(line.values())[1:5])
            line_words = page_cropped.extract_words(keep_blank_chars=True)
            pattern_parts = []
            for idx, word in enumerate(line_words):
                text = word['text']
                if text.endswith(terminator_text):
                    if idx + 1 < len(line_words) and not line_words[idx + 1]['text'].endswith(terminator_text):
                        pattern_parts.append(text + " (.*?)")
                    else:
                        pattern_parts.append(text + " (.*)")
                    column_names.append(text[:-1])  # Remove the trailing terminator_text
            
            if pattern_parts:
                pattern = " ".join(pattern_parts)
                metadata_patterns.append({
                    "pattern": pattern,
                    "columns": column_names,
                    "fill_direction": fill_direction
                })
        
        return(metadata_patterns)
    
    @staticmethod
    def fixed_text_areas_from_lines(page, line_numbers, key_separator=":", key_line_numbers=None, expand=[0,0,0,0]):
        page_lines = page.extract_text_lines()
        fixed_lines = [page_lines[line_number] for line_number in line_numbers]
        if key_line_numbers:
            key_lines = [page_lines[line_number] for line_number in key_line_numbers]
        else:
            key_lines = None
        fixed_text_areas = {}

        for line_idx, line in enumerate(fixed_lines):
            line_words = page.crop(list(line.values())[1:5]).extract_words(keep_blank_chars=True)
            if key_lines:
                key_words = page.crop(list(key_lines[line_idx].values())[1:5]).extract_words(keep_blank_chars=True)
            else:
                key_words = None
            for word_idx, word in enumerate(line_words):
                text = word['text']
                area = [word['x0'], line['top'], word['x1'], line['bottom']]
                if expand:
                    area = [coord + expand[idx] for idx, coord in enumerate(area)]
                if key_separator:
                    key = text.split(key_separator)[0].strip()
                elif key_words:
                    key = key_words[word_idx]['text']
                fixed_text_areas[key] = [int(coord) for coord in area]
        return(fixed_text_areas)

class PDFExtraction:
    def __init__(self, pdf_path, config: PDFExtractionConfig):
        self.pdf_path = self._validate_path(pdf_path)
        self.subset_path = None
        self.config = config
        self.pages_of_interest = []
        self.combined_df = pd.DataFrame()
        self.tables_df = pd.DataFrame()
        self.metadata_df = pd.DataFrame()
        self.fixed_df = pd.DataFrame()
        
        # Optional property for horizontal lines
        self.horizontal_lines = None
    
    @staticmethod
    def _validate_path(path):
        """
        Validate the provided PDF path.

        Args:
            path (str or Path): Path to a file or directory.

        Returns:
            Path: Validated Path object.

        Raises:
            ValueError: If the path does not exist or is not a file.
        """
        path = Path(path)
        if not path.exists():
            raise ValueError(f"The provided path does not exist: {path}")
        if not path.is_file():
            raise ValueError(f"The provided path is not a file: {path}")
        return path

    @staticmethod
    def _find_keyword_text(text, keywords_keep=None, keywords_remove=None, require_all=True):
        """
        Determine if the text contains the required keywords and does not contain excluded keywords.

        Args:
            text (str): The text to search within.
            keywords_keep (list, optional): Keywords to keep in selection.
            keywords_remove (list, optional): Keywords to remove from selection.
            require_all (bool, optional): Require all keywords to match. Defaults to True.

        Returns:
            bool: True if the text meets the criteria, False otherwise.
        """
        # Check if page should be excluded based on keywords_remove
        if keywords_remove and any(keyword in text for keyword in keywords_remove):
            return False

        # Check if all or any keywords_keep are present in the text
        if keywords_keep:
            if require_all:
                if all(keyword in text for keyword in keywords_keep):
                    return True
            else:
                if any(keyword in text for keyword in keywords_keep):
                    return True
        else:
            # If no keywords to keep are provided, consider all pages
            return True
    
    def find_keyword_pages(self, use_pdfplumber=False):
        """
        Find the page numbers containing the specified keywords in a PDF and store them in the pages_of_interest attribute.
        """
        page_selection = self.config.page_selection
        keywords_keep = page_selection.get("keywords_to_keep", [])
        keywords_remove = page_selection.get("keywords_to_remove", [])
        require_all = page_selection.get("require_all_keywords", False)
        
        if use_pdfplumber:
            # Use pdfplumber (slower)
            with pdfplumber.open(self.pdf_path) as pdf:
                total_pages = len(pdf.pages)
                # Iterate over each page
                for page_num, page in enumerate(pdf.pages, start=1):
                    print(f"Processing page {page_num}/{total_pages}...", end="\r")
                    # Extract text from the page
                    text = page.extract_text()
                    if self._find_keyword_text(text, keywords_keep, keywords_remove, require_all):
                        self.pages_of_interest.append(page_num)

        else:
            # Use PyMuPDF (fitz)
            pdf_document = fitz.open(self.pdf_path)

            # Iterate over each page
            for page_num in range(pdf_document.page_count):
                print(f"Processing page {page_num + 1}/{pdf_document.page_count}...", end="\r")

                # Extract text from the page
                page = pdf_document.load_page(page_num)
                text = page.get_text()
                if self._find_keyword_text(text, keywords_keep, keywords_remove, require_all):
                    self.pages_of_interest.append(page_num + 1)  # Adjust to 1-based index
    
    @staticmethod
    def get_bookmark_pages(pdf_path: str, target_title: str):
        """
        Extract page numbers for a specific bookmark section in a PDF using PyMuPDF.
        
        Args:
            pdf_path (str): Path to the PDF file
            target_title (str): Title of the bookmark section to find
            
        Returns:
            List[int]: List of page numbers (1-based) associated with the bookmark section
        """
        doc = fitz.open(pdf_path)
        toc = doc.get_toc()  # Get table of contents (bookmarks)
        
        # Find our target bookmark
        target_level = None
        target_index = None
        
        for i, (level, title, page) in enumerate(toc):
            if title == target_title:
                target_level = level
                target_index = i
                break
        
        if target_index is None:
            doc.close()
            return []
        
        # Get starting page
        start_page = toc[target_index][2]  # Page number is third element
        
        # Find the end page by looking for the next bookmark at same or higher level
        end_page = None
        for level, _, page in toc[target_index + 1:]:
            if level <= target_level:
                end_page = page - 1  # Subtract 1 since next section starts here
                break
        
        # If no end page found (last bookmark in its section)
        if end_page is None:
            if target_index + 1 < len(toc):
                # Use next bookmark's page as end
                end_page = toc[target_index + 1][2] - 1
            else:
                # For last bookmark, just use its starting page
                end_page = start_page
        
        doc.close()
        return list(range(start_page, end_page + 1))
    
    def subset_pdf(self):
        """
        Subset a PDF to only contain the specified pages.
        """
        # Open the input PDF file
        with open(self.pdf_path, "rb") as file:
            # Create a PDF reader object
            pdf_reader = PyPDF2.PdfReader(file)

            # Create a PDF writer object
            pdf_writer = PyPDF2.PdfWriter()

            # Iterate over pages in the input PDF
            for page_num in self.pages_of_interest:
                # Ensure the page number is within the valid range
                if 0 < page_num <= len(pdf_reader.pages):
                    # Get the page from the input PDF
                    page = pdf_reader.pages[page_num - 1]

                    # Add the page to the output PDF
                    pdf_writer.add_page(page)

            # Write the output PDF to a file
            with open(self.subset_path, "wb") as output_file:
                pdf_writer.write(output_file)

    def _get_table_settings(self):
        """
        Get table and line settings for PDF extraction based on configuration.

        Returns:
            tuple: A tuple containing table_settings and line_settings dictionaries.
        """
        bbox = self.config.table_area
        
        table_settings = {
            "vertical_strategy": "explicit",
            "explicit_vertical_lines": [bbox[0]] + self.config.table_columns + [bbox[2]],
            "horizontal_strategy": "text",
            "snap_y_tolerance": 5,
            "intersection_x_tolerance": 999,
        }
        
        # If horizontal lines are provided, add them to the settings
        if self.horizontal_lines:
            table_settings["horizontal_strategy"] = "explicit"
            table_settings["explicit_horizontal_lines"] = self.horizontal_lines
            
        line_settings = table_settings.copy()
        line_settings["explicit_vertical_lines"] = [bbox[0]] + [bbox[2]]
        
        return table_settings, line_settings
        
    @staticmethod
    def extract_metadata_patterns(df_lines, patterns):
        # Initialize empty dataframe to store expanded lines and metadata
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

        return df_metadata

    @staticmethod
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

    @staticmethod
    def extract_fixed_text_areas(page, areas):

        # Initialize a dictionary to store text extracted from the current page
        page_text = {}

        # Extract text from each fixed text area defined in the config
        for area_name, bbox in areas.items():
            
            area_text = page.within_bbox(bbox).extract_text()
            
            # Store the extracted text in the page_text dictionary
            page_text[area_name] = area_text

        return page_text
    
    def draw_extraction_config(self, page):
        import re
        page_image = page.to_image()
        
        # Draw table area
        page_image.draw_rect(self.config.table_area, stroke='red', stroke_width=2)
        
        # Draw table columns
        for idx, x_pos in enumerate(self.config.table_columns):
            page_image.draw_line(((x_pos, 0), (x_pos, page.height)), stroke='blue')
        
        # Draw metadata patterns
        for pattern in self.config.metadata_patterns:
            # Get page lines
            page_lines = page.extract_text_lines()
            for line in page_lines:
                # Use the regular expression pattern to match text
                match = re.search(pattern["pattern"], line["text"])
                if match:
                    for idx, group in enumerate(match.groups()[1:], start = 1):
                        # Determine the number of whitespace characters before the matched pattern
                        start_pos = len(line["text"][0:match.start(idx)].replace(" ", ""))
                        end_pos = len(line["text"][0:match.end(idx)].replace(" ", ""))-1
                        
                        # Draw a rectangle around the matched text
                        bbox = [line["chars"][start_pos]['x0'], line['top'], line["chars"][end_pos]['x1'], line['bottom']]
                        page_image.draw_rect(bbox, stroke='green', stroke_width=2)
                    
                    
        # Draw fixed text areas
        for area_name, bbox in self.config.fixed_text_areas.items():
            page_image.draw_rect(bbox, stroke='purple', stroke_width=2)
            # Add text label
            # page_image.draw_text(bbox[:2], area_name, fontsize=12, color='black')
        
        return page_image

    def extract_data_from_pdf(self, output_path=None, log_file_path=None, draw_image_path=None, crop_meta=True):
        """
        Extract data from a PDF file based on the specified configuration.

        Args:
        output_dir (str, optional): Output directory for saving extracted data.
        log_file_path (str, optional): Path to save the extraction log file. Defaults to None.
        """        
        # Set output path if not provided and create output directory if it doesn't exist
        if not output_path:
            output_path = self.pdf_path.parent
        else:
            # Validate output directory
            output_path = self._validate_path(output_path)
            output_path.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        if log_file_path:
            logging.basicConfig(filename=log_file_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        else:
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
                
        table_settings, line_settings = self._get_table_settings()
        
        if not self.pages_of_interest:
            self.find_keyword_pages() # Find pages with keywords
        if not self.subset_path:
            self.subset_path = os.path.join(output_path, os.path.basename(self.pdf_path).replace(".pdf", "_subset.pdf"))
            self.subset_pdf() # Subset PDF with pages of interest

        with pdfplumber.open(self.subset_path) as pdf:
            total_pages = len(pdf.pages)
            for page_num, page in enumerate(pdf.pages, start=1):
                logging.info(f"Processing page {page_num}/{total_pages}...")
                
                # Extract table from cropped page and convert the extracted data to a dataframe with column names
                page_cropped = page.crop(self.config.table_area)
                extracted_table = page_cropped.extract_table(table_settings)
                table_df = pd.DataFrame(extracted_table[0:]) # Convert to dataframe
                table_df.columns = self.config.table_column_names
                table_df = self.apply_column_filters(table_df, self.config.post_processing['column_filters'])
                table_df.insert(0, 'Line Number', table_df.index+1) # Add line number (row index) as first column of dataframe
                table_df.insert(0, 'Page Number', page_num) # Add page number as first column of dataframe
                self.tables_df = pd.concat([self.tables_df, table_df], ignore_index=True)
                
                # Extract text line by line from the cropped page and extract metadata using patterns from the config file
                if crop_meta:
                    extracted_lines = page_cropped.extract_table(line_settings)
                else:
                    extracted_lines = page.extract_table(line_settings)
                lines_df = pd.DataFrame(extracted_lines, columns=['text']) # Convert to dataframe
                meta_df = self.extract_metadata_patterns(lines_df, self.config.metadata_patterns)
                meta_df.insert(0, 'Page Number', page_num) # Add page number as first column of dataframe
                self.metadata_df = pd.concat([self.metadata_df, meta_df], ignore_index=True) # Concatenate metadata dataframe
                
                # Extract fixed position text from the page
                extracted_text = self.extract_fixed_text_areas(page, self.config.fixed_text_areas)
                text_df = pd.DataFrame(extracted_text, index=[0])
                text_df.insert(0, 'Page Number', page_num) # Add page number as first column of dataframe
                self.fixed_df = pd.concat([self.fixed_df, text_df], ignore_index=True) # Concatenate fixed text dataframe
                
                if draw_image_path:
                    page_image = self.draw_extraction_config(page)
                    page_image.save(draw_image_path.replace(".pdf", f"_page_{page_num}.png"))
        
        logging.info("Extraction completed.")

    def combine_extracted_data(self):
        meta_pivot = self.metadata_df.pivot_table(index=['Page Number', 'Line Number'], columns='Column Name', values='Column Value', aggfunc='first').reset_index()
        meta_pivot = pd.concat([self.tables_df[['Page Number', 'Line Number']], meta_pivot], ignore_index=True).sort_values(by=['Page Number', 'Line Number']).reset_index(drop=True)
        meta_pivot = meta_pivot.ffill()
        self.combined_df = self.tables_df.merge(meta_pivot, on=['Page Number', 'Line Number'], how='left')
        self.combined_df = self.combined_df.merge(self.fixed_df, on=['Page Number'])
