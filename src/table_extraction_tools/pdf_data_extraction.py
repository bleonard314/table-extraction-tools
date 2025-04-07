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
import re
from enum import Enum, auto
from typing import List, Optional, Union, Dict, Any
import numpy as np
from PIL import Image
from dataclasses import dataclass, field

class PageSelectionMethod(Enum):
    """Enum for different page selection methods"""
    ALL_PAGES = auto()
    EXPLICIT_PAGES = auto()
    KEYWORD_BASED = auto()
    BOOKMARK_BASED = auto()

@dataclass
class PageSelection:
    method: PageSelectionMethod = field(
        default=PageSelectionMethod.ALL_PAGES,
        metadata={"description": "Method used to select PDF pages"}
    )
    page_numbers: List[int] = field(
        default_factory=list,
        metadata={"description": "List of specific page numbers to process"}
    )
    keywords_to_keep: List[str] = field(
        default_factory=list,
        metadata={"description": "Keywords that must be present for page selection"}
    )
    keywords_to_remove: List[str] = field(
        default_factory=list,
        metadata={"description": "Keywords that must not be present for page selection"}
    )
    require_all_keywords: bool = field(
        default=False,
        metadata={"description": "If True, all keywords must match for page selection"}
    )
    bookmark_title: Optional[str] = field(
        default=None,
        metadata={"description": "PDF bookmark title to use for page selection"}
    )

    @classmethod
    def all_pages(cls) -> 'PageSelection':
        """Create a PageSelection instance for processing all pages"""
        return cls(method=PageSelectionMethod.ALL_PAGES)

    @classmethod
    def explicit_pages(cls, pages: List[int]) -> 'PageSelection':
        """Create a PageSelection instance for explicitly listed pages"""
        return cls(
            method=PageSelectionMethod.EXPLICIT_PAGES,
            page_numbers=pages
        )

    @classmethod
    def keyword_based(
        cls,
        keywords_to_keep: List[str],
        keywords_to_remove: Optional[List[str]] = None,
        require_all_keywords: bool = False
    ) -> 'PageSelection':
        """Create a PageSelection instance for keyword-based selection"""
        return cls(
            method=PageSelectionMethod.KEYWORD_BASED,
            keywords_to_keep=keywords_to_keep,
            keywords_to_remove=keywords_to_remove,
            require_all_keywords=require_all_keywords
        )

    @classmethod
    def bookmark_based(cls, bookmark_title: str) -> 'PageSelection':
        """Create a PageSelection instance for bookmark-based selection"""
        return cls(
            method=PageSelectionMethod.BOOKMARK_BASED,
            bookmark_title=bookmark_title
        )

    def to_dict(self) -> Dict:
        """Convert the PageSelection instance to a dictionary for YAML storage"""
        return {
            "method": self.method.name,
            "page_numbers": self.page_numbers,
            "keywords_to_keep": self.keywords_to_keep,
            "keywords_to_remove": self.keywords_to_remove,
            "require_all_keywords": self.require_all_keywords,
            "bookmark_title": self.bookmark_title
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'PageSelection':
        """Create a PageSelection instance from a dictionary"""
        return cls(
            method=PageSelectionMethod[data.get("method", "ALL_PAGES")],
            page_numbers=data.get("page_numbers"),
            keywords_to_keep=data.get("keywords_to_keep"),
            keywords_to_remove=data.get("keywords_to_remove"),
            require_all_keywords=data.get("require_all_keywords", False),
            bookmark_title=data.get("bookmark_title")
        )

@dataclass
class ColumnFilter:
    """Configuration for column-specific filtering."""
    column: str
    regex: str

@dataclass
class PostProcessingConfig:
    """Configuration for post-processing of extracted PDF data."""
    explicit_line_numbers: Optional[List[int]] = field(
        default=None,
        metadata={"description": "Specific line numbers to process"}
    )
    column_filters: List[ColumnFilter] = field(
        default_factory=list,
        metadata={"description": "Regular expression filters for specific columns"}
    )
    convert_column_names: bool = field(
        default=False,
        metadata={"description": "Whether to convert column names to snake_case"}
    )
    convert_data_types: bool = field(
        default=True,
        metadata={"description": "Whether to automatically convert data types"}
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            "explicit_line_numbers": self.explicit_line_numbers,
            "column_filters": [{"column": f.column, "regex": f.regex} for f in self.column_filters],
            "convert_column_names": self.convert_column_names,
            "convert_data_types": self.convert_data_types
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PostProcessingConfig':
        """Create configuration from dictionary."""
        column_filters = [ColumnFilter(**f) for f in data.get('column_filters', [])]
        return cls(
            explicit_line_numbers=data.get('explicit_line_numbers'),
            column_filters=column_filters,
            convert_column_names=data.get('convert_column_names', False),
            convert_data_types=data.get('convert_data_types', True)
        )
        
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
                "method": "ALL_PAGES",
                "explicit_pages": None,
                "keywords_to_keep": [],
                "keywords_to_remove": [],
                "require_all_keywords": False,
                "bookmark_title": None
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
        self._page_selection = PageSelection.from_dict(self.config.get('page_selection', {}))
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
    def page_selection(self, value: Union[PageSelection, Dict]):
        if isinstance(value, dict):
            self._page_selection = PageSelection.from_dict(value)
        elif isinstance(value, PageSelection):
            self._page_selection = value
        else:
            raise ValueError("page_selection must be either a PageSelection instance or a dictionary")
        self.config['page_selection'] = self._page_selection.to_dict()

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

    @property
    def column_filters(self):
        return self._post_processing.get('column_filters', [])

    @column_filters.setter
    def column_filters(self, value):
        table_column_names = self._table_column_names

        if value:
            for column_filter in value:
                column_name = column_filter.get('column')
                if column_name not in table_column_names:
                    raise ValueError(f"Column filter name '{column_name}' not found in table_column_names")

        self._post_processing['column_filters'] = value
        self.config['post_processing']['column_filters'] = value

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
    
    def table_columns_from_line(
        self,
        page,
        line_number: Optional[int] = None,
        line_coords: Optional[Dict[str, float]] = None,
        column_justification: Optional[List[str]] = None,
        column_buffers: Optional[List[int]] = None,
        debug: bool = False
    ) -> None:
        """
        Compute the vertical boundaries (column separators) for table columns from a header line in a PDF page.

        Args:
            page: A pdfplumber page (or similar) to extract the line from.
            line_number (int, optional): The line number (1-based) in the page to use for detecting column positions.
            line_coords (dict, optional): A dictionary with 'top' and 'bottom' coordinates of the line.
            column_justification (List[str], optional): A list specifying the justification for each detected column.
                Defaults to all columns being left-justified.
            column_buffers (List[int], optional): A list of pixel buffers (one per column) used to adjust the boundaries.
                Defaults to no buffers.
            debug (bool): If True, draws the word bounding boxes and computed vertical lines on the header image
                for visual debugging.

        Raises:
            ValueError: If neither line_number nor line_coords is provided, or if both are provided.
            ValueError: If the provided column_justification or column_buffers lists do not match the number
                of detected words in the header line.

        Updates:
            The `table_columns` attribute of the configuration is updated with the computed boundary positions.
        """
        if (line_number is None and line_coords is None) or (line_number is not None and line_coords is not None):
            raise ValueError("You must provide either line_number or line_coords, but not both.")

        # Extract all text lines from the page.
        page_text_lines = page.extract_text_lines()

        if line_number is not None:
            if line_number < 1 or line_number > len(page_text_lines):
                raise ValueError(f"line_number must be between 1 and {len(page_text_lines)}; got {line_number}")
            # Get the header line (adjusting for 1-based numbering)
            header_line = page_text_lines[line_number - 1]
            top, bottom = header_line["top"], header_line["bottom"]
        else:
            # Use the provided line coordinates
            top, bottom = line_coords["top"], line_coords["bottom"]

        # Construct the bounding box for the header line using the table_area from the configuration.
        table_area = self.table_area
        line_bbox = (table_area[0], top, table_area[2], bottom)

        # Crop the page to the header line.
        line_page = page.crop(line_bbox)

        # If debugging, convert the cropped area to an image to draw on.
        if debug:
            line_page_image = line_page.to_image(resolution=150)
            line_page_image.reset()

        # Extract words (with their bounding boxes) from the cropped header line.
        line_words = line_page.extract_words(keep_blank_chars=True, y_tolerance=999)
        # Sort the words by their x-coordinate.
        line_words = sorted(line_words, key=lambda word: word["x0"])
        # Update configuration with the detected column names.
        self.table_column_names = [word["text"].strip() for word in line_words]

        # Set default values for column_justification and column_buffers if not provided.
        if column_justification is None:
            column_justification = ["left"] * len(line_words)
        if column_buffers is None:
            column_buffers = [0] * len(line_words)

        # Validate that the provided column configuration lists match the number of detected words.
        if len(column_justification) != len(line_words):
            raise ValueError(
                f"Length of column_justification ({len(column_justification)}) must match "
                f"the number of detected words ({len(line_words)})."
            )
        if len(column_buffers) != len(line_words):
            raise ValueError(
                f"Length of column_buffers ({len(column_buffers)}) must match "
                f"the number of detected words ({len(line_words)})."
            )

        # Optionally draw bounding boxes around each detected word.
        if debug:
            for word in line_words:
                bbox = (word["x0"], word["top"], word["x1"], word["bottom"])
                line_page_image.draw_rect(bbox, fill=None, stroke_width=1)

        # Compute boundaries between adjacent columns.
        boundaries = []
        for idx in range(len(line_words) - 1):
            current_word = line_words[idx]
            next_word = line_words[idx + 1]
            just = column_justification[idx].lower()

            if just == "left":
                # For left-justified columns, use the next word's left edge minus the current column's buffer.
                boundary = next_word["x0"] - column_buffers[idx]
            elif just == "right":
                # For right-justified columns, use the current word's right edge plus the current column's buffer.
                boundary = current_word["x1"] + column_buffers[idx]
            elif just == "center":
                # For center-justified columns, average an adjusted right edge and left edge.
                boundary = ((current_word["x1"] + column_buffers[idx]) +
                            (next_word["x0"] - column_buffers[idx + 1])) / 2
            else:
                # Fallback: use the simple midpoint between the current word’s right edge and the next word’s left edge.
                boundary = (current_word["x1"] + next_word["x0"]) / 2

            boundaries.append(boundary)
            if debug:
                line_page_image.draw_vline(boundary, stroke_width=1)

        # Update the configuration with the computed boundaries.
        self.table_columns = boundaries

        if debug:
            # Display the image with drawn lines for visual confirmation.
            return line_page_image
    
    def metadata_patterns_from_lines(
        self, 
        page, 
        line_numbers: List[int], 
        terminator_text: str = ":", 
        fill_direction: str = "down",
        **kwargs: Dict[str, Any]
        ) -> List[Dict]:
        """
        Create metadata extraction patterns from specific lines in a PDF page.
        
        Args:
            page (pdfplumber.page.Page): The PDF page to extract patterns from
            line_numbers (List[int]): List of line numbers (1-based) to extract patterns from
            terminator_text (str, optional): Text that terminates a metadata field name. Defaults to ":"
            fill_direction (str, optional): Direction to fill extracted values. Defaults to "down"
            
        Returns:
            List[Dict]: List of metadata patterns, each containing:
                - pattern: Regular expression pattern for extracting metadata
                - columns: List of column names extracted from the lines
                - fill_direction: Direction to fill the extracted values
                
        Raises:
            ValueError: If line numbers are invalid or no lines are found in the page
        """
        page_lines = page.extract_text_lines()
        
        # Validate line numbers
        if not line_numbers:
            raise ValueError("No line numbers provided")
        if not all(isinstance(n, int) for n in line_numbers):
            raise ValueError("All line numbers must be integers")
        if max(line_numbers) > len(page_lines):
            raise ValueError(f"Line number {max(line_numbers)} exceeds number of lines in page ({len(page_lines)})")
        if min(line_numbers) < 1:
            raise ValueError("Line numbers must be 1-based (minimum value is 1)")
        
        # Convert to 0-based indexing and get specified lines
        header_lines = [page_lines[n - 1] for n in line_numbers]
        metadata_patterns = []

        for line in header_lines:
            # Extract the bounding box coordinates from the line
            bbox = [line['x0'], line['top'], line['x1'], line['bottom']]
            page_cropped = page.crop(bbox)
            line_words = page_cropped.extract_words(keep_blank_chars=True, **kwargs)
            
            column_names = []
            pattern_parts = []
            
            for idx, word in enumerate(line_words):
                text = word['text'].strip()
                if text.endswith(terminator_text):
                    # Determine if this is the last metadata field in the line
                    is_last_field = idx + 2 == len(line_words)
                    
                    # Use non-greedy match (?.*?) for middle fields, greedy match (.*) for last field
                    pattern_part = text + "\s*(.*)" if is_last_field else text + "\s*(.*?)"
                    pattern_parts.append(pattern_part)
                    
                    # Store column name without terminator
                    column_names.append(text[:-len(terminator_text)].strip())
            
            if pattern_parts:
                pattern = " ".join(pattern_parts)
                metadata_patterns.append({
                    "pattern": pattern,
                    "columns": column_names,
                    "fill_direction": fill_direction
                })
        
        self.metadata_patterns = metadata_patterns
    
    def fixed_text_areas_from_lines(
        self,
        page,
        line_numbers: List[int],
        key_separator: Optional[str] = ":",
        key_line_numbers: Optional[List[int]] = None,
        expand: List[float] = [0, 0, 0, 0],
        **kwargs
    ) -> None:
        """
        Create fixed text areas configuration from specific lines in a PDF page.
        
        Args:
            page (pdfplumber.page.Page): The PDF page to extract areas from
            line_numbers (List[int]): List of line numbers (1-based) containing the text areas
            key_separator (str, optional): Separator to split text into key/value. Defaults to ":"
            key_line_numbers (List[int], optional): List of line numbers containing keys. 
                Must be same length as line_numbers if provided.
            expand (List[float], optional): Amount to expand boundaries [left, top, right, bottom].
                Defaults to [0, 0, 0, 0]
                
        Raises:
            ValueError: If line numbers are invalid or expansion values are incorrect
        """
        # Validate inputs
        if not line_numbers:
            raise ValueError("No line numbers provided")
        if not all(isinstance(n, int) for n in line_numbers):
            raise ValueError("All line numbers must be integers")
        if len(expand) != 4:
            raise ValueError("Expand must be a list of 4 values [left, top, right, bottom]")
        
        page_lines = page.extract_text_lines()
        
        # Validate line numbers against page content
        if max(line_numbers) > len(page_lines):
            raise ValueError(f"Line number {max(line_numbers)} exceeds number of lines in page ({len(page_lines)})")
        if min(line_numbers) < 1:
            raise ValueError("Line numbers must be 1-based (minimum value is 1)")
        
        # Validate key line numbers if provided
        if key_line_numbers:
            if len(key_line_numbers) != len(line_numbers):
                raise ValueError("key_line_numbers must have same length as line_numbers")
            if max(key_line_numbers) > len(page_lines):
                raise ValueError("Invalid key line number")
            if min(key_line_numbers) < 1:
                raise ValueError("Key line numbers must be 1-based")
        
        # Convert to 0-based indexing
        fixed_lines = [page_lines[n - 1] for n in line_numbers]
        key_lines = [page_lines[n - 1] for n in key_line_numbers] if key_line_numbers else None
        
        fixed_text_areas = {}
        
        for line_idx, line in enumerate(fixed_lines):
            # Get bbox for current line
            line_bbox = [line['x0'], line['top'], line['x1'], line['bottom']]
            line_words = page.crop(line_bbox).extract_words(keep_blank_chars=True, return_chars=True, **kwargs)
            
            if key_lines:
                key_bbox = [key_lines[line_idx]['x0'], key_lines[line_idx]['top'], 
                        key_lines[line_idx]['x1'], key_lines[line_idx]['bottom']]
                key_words = page.crop(key_bbox).extract_words(keep_blank_chars=True, return_chars=True, **kwargs)
            else:
                key_words = None
                
            for word_idx, word in enumerate(line_words):
                text = word['text'].strip()
                # Create area with word boundaries
                area = [
                    word['x0'] - expand[0],  # Expand left
                    line['top'] - expand[1],  # Expand top
                    word['x1'] + expand[2],  # Expand right
                    line['bottom'] + expand[3]  # Expand bottom
                ]
                
                # Determine key for the area
                if key_separator and key_separator in text:
                    key = text.split(key_separator)[0].strip()
                    key_idx = len(key.replace(" ", ""))
                    area[0] = word["chars"][key_idx]['x0']
                elif key_words and word_idx < len(key_words):
                    key = key_words[word_idx]['text'].strip()
                else:
                    key = text
                    
                fixed_text_areas[key] = [int(coord) for coord in area]
        
        # Update configuration
        self.fixed_text_areas = fixed_text_areas

    def expand_fixed_text_area(
        self,
        key: str,
        expand: List[float]
    ) -> None:
        """
        Expand the boundaries of a specific fixed text area in the configuration.
        
        Args:
            key (str): The key of the fixed text area to expand
            expand (List[float]): Amount to expand boundaries [left, top, right, bottom]
                Positive values expand the area, negative values contract it
                
        Raises:
            ValueError: If key not found or expansion values are incorrect
            KeyError: If the specified key doesn't exist in fixed_text_areas
        """
        if len(expand) != 4:
            raise ValueError("Expand must be a list of 4 values [left, top, right, bottom]")
        
        if key not in self.fixed_text_areas:
            raise KeyError(f"No fixed text area found with key: {key}")
        
        current_area = self.fixed_text_areas[key]
        expanded_area = [
            current_area[0] - expand[0],  # Expand left
            current_area[1] - expand[1],  # Expand top
            current_area[2] + expand[2],  # Expand right
            current_area[3] + expand[3]   # Expand bottom
        ]
        
        self.fixed_text_areas[key] = [int(coord) for coord in expanded_area]
    
    def remove_fixed_text_area(self, key: Union[str, int]) -> None:
        """
        Remove a fixed text area from the configuration.
        
        Args:
            key: Either the key name (str) or the position (int, 0-based) to remove
                
        Raises:
            KeyError: If string key doesn't exist
            IndexError: If position is out of range
            TypeError: If key is neither string nor integer
        """
        if isinstance(key, str):
            # Remove by key name
            del self.fixed_text_areas[key]
        elif isinstance(key, int):
            # Remove by position
            items = list(self.fixed_text_areas.items())
            if 0 <= key < len(items):
                removed_key = items[key][0]
                del self.fixed_text_areas[removed_key]
            else:
                raise IndexError(f"Position {key} is out of range")
        else:
            raise TypeError("Key must be either a string or integer")
    
    def rename_fixed_text_area(self, old_key: str, new_key: str) -> None:
        """
        Rename a key in the fixed text areas configuration.
        
        Args:
            old_key (str): The current key name
            new_key (str): The new key name to use
                
        Raises:
            KeyError: If old_key doesn't exist
            ValueError: If new_key already exists
        """
        if old_key not in self.fixed_text_areas:
            raise KeyError(f"Key '{old_key}' not found in fixed text areas")
        
        if new_key in self.fixed_text_areas and new_key != old_key:
            raise ValueError(f"Key '{new_key}' already exists in fixed text areas")
        
        # Get the value and remove the old key
        value = self.fixed_text_areas.pop(old_key)
        
        # Add with new key
        self.fixed_text_areas[new_key] = value

class PDFExtraction:
    def __init__(self, pdf_path, config: PDFExtractionConfig):
        self.pdf_path = self._validate_path(pdf_path)
        self.pdf = pdfplumber.open(self.pdf_path)
        self.subset_path = None
        self.config = config
        self.pages_of_interest = []
        self.combined_df = pd.DataFrame()
        self.tables_df = pd.DataFrame()
        self.metadata_df = pd.DataFrame()
        self.fixed_df = pd.DataFrame()
        
        # Optional property for horizontal lines
        self.horizontal_lines = None
    
    def get_pages_of_interest(self) -> List[int]:
        """Determine pages of interest based on the configured selection method"""
        selection = self.config.page_selection

        if selection.method == PageSelectionMethod.ALL_PAGES:
            with pdfplumber.open(self.pdf_path) as pdf:
                self.pages_of_interest = list(range(1, len(pdf.pages) + 1))

        elif selection.method == PageSelectionMethod.EXPLICIT_PAGES:
            self.pages_of_interest = selection.page_numbers

        elif selection.method == PageSelectionMethod.KEYWORD_BASED:
            self.find_keyword_pages()

        elif selection.method == PageSelectionMethod.BOOKMARK_BASED:
            self.find_bookmark_pages()

        return self.pages_of_interest
    
    def get_page_plumber(self, offset = 0):
        """
        Get the pdfplumber Page object for the first page of interest.
        
        Returns:
            pdfplumber.page.Page: The first page of interest as a pdfplumber Page object
            
        Raises:
            ValueError: If no pages of interest have been determined
        """
            
        if not self.pages_of_interest:
            raise ValueError("No pages of interest found in the PDF")
        
        # Open PDF and return first page
        try:
            return self.pdf.pages[self.pages_of_interest[offset] - 1]  # Subtract 1 for 0-based indexing
        except IndexError:
            raise ValueError("Invalid page offset")

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
        keywords_keep = page_selection.keywords_to_keep
        keywords_remove = page_selection.keywords_to_remove
        require_all = page_selection.require_all_keywords
        
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
    
    def find_bookmark_pages(self):
        """
        Find page numbers for specific bookmark sections in the PDF using PyMuPDF and
        store them in the pages_of_interest attribute.
        
        The method searches for bookmarks with the title specified in the configuration's
        page_selection.bookmark_title. It determines the range of pages that fall under
        these bookmarks by looking at the PDF's table of contents structure.
        
        The page ranges are determined by:
        1. Finding the starting page of each matching bookmark
        2. Finding the ending page (either the start of the next bookmark at the same
        or higher level, or the last page of the document)
        
        Returns:
            bool: True if bookmarks were found and pages were identified, False otherwise
        
        Raises:
            ValueError: If bookmark_title is not set in the configuration
            FileNotFoundError: If the PDF file cannot be opened
        """
        # Verify bookmark title is set in configuration
        bookmark_title = self.config.page_selection.bookmark_title
        if not bookmark_title:
            raise ValueError("Bookmark title must be set in page_selection configuration")
        
        try:
            doc = fitz.open(self.pdf_path)
        except Exception as e:
            raise FileNotFoundError(f"Could not open PDF file: {self.pdf_path}") from e
        
        try:
            toc = doc.get_toc()  # Get table of contents (bookmarks)
            if not toc:
                logging.warning(f"No bookmarks found in PDF: {self.pdf_path}")
                return False
            
            # Find all target bookmarks
            target_bookmarks = []
            for i, (level, title, page) in enumerate(toc):
                if title == bookmark_title:
                    target_bookmarks.append((level, page, i))
            
            if not target_bookmarks:
                logging.warning(f"Bookmark '{bookmark_title}' not found in PDF")
                return False
            
            # Determine page ranges for each matching bookmark
            for target_level, start_page, target_index in target_bookmarks:
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
                        # For last bookmark, use the document's last page
                        end_page = doc.page_count
                
                # Append the range of pages to pages_of_interest
                self.pages_of_interest.extend(range(start_page, end_page + 1))
            
            logging.info(f"Found {len(self.pages_of_interest)} pages under bookmark '{bookmark_title}'")
            return True
            
        finally:
            doc.close()
    
    def create_overlay_visualization(self, output_path: Optional[str] = None, alpha: float = 0.3):
        """
        Create an overlay visualization of pages of interest to identify consistent areas.
        
        Args:
            output_path (str, optional): Path to save the output visualization. If None, 
                the visualization will only be returned as an image object.
            alpha (float, optional): Transparency level for each page. Defaults to 0.3
        
        Returns:
            PIL.Image: The final overlaid image
        
        Raises:
            ValueError: If no pages of interest have been determined
        """
        if not self.pages_of_interest:
            raise ValueError("No pages of interest found in the PDF")
                
        # Open the PDF with pdfplumber
        with pdfplumber.open(self.pdf_path) as pdf:
            # Get the first page to determine dimensions
            first_page = pdf.pages[self.pages_of_interest[0] - 1]
            first_image = first_page.to_image()
            width, height = first_image.original.size
            
            # Create a blank white image as the base
            base_image = Image.new('RGBA', (width, height), (255, 255, 255, 255))
            
            # Create a list to store all page images
            page_images = []
            
            # Convert each page to an image and store
            for page_num in self.pages_of_interest:
                page = pdf.pages[page_num - 1]
                page_image = page.to_image()
                # Convert to RGBA to allow transparency
                rgba_image = page_image.original.convert('RGBA')
                page_images.append(rgba_image)
                
            # Overlay all images with transparency
            for img in page_images:
                # Create a new image with transparency
                transparent = Image.new('RGBA', base_image.size, (0, 0, 0, 0))
                transparent.paste(img, (0, 0))
                
                # Adjust alpha for this layer
                data = np.array(transparent)
                data[..., 3] = (data[..., 3] * alpha).astype(np.uint8)
                transparent = Image.fromarray(data)
                
                # Composite the image onto the base
                base_image = Image.alpha_composite(base_image, transparent)
            
            # Save the image if output path is provided
            if output_path:
                base_image.save(output_path)
                
            return base_image
    
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
            "horizontal_strategy": "text",  # "lines"
            "snap_y_tolerance": 7,
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
    def extract_metadata_patterns(page, patterns):
        # Extract text line by line and extract metadata
        meta = [page.search(meta['pattern']) for meta in patterns]
        
        # Check if any metadata was found
        if not any(meta):
            return pd.DataFrame()
        
        # Assuming meta is the list of search results from pdfplumber
        result = []

        # Iterate over each entry in the meta list
        for j, matches in enumerate(meta):
            # Extract the columns from the configuration
            columns = patterns[j]['columns']
            
            # For each match, extract the groups and their y0 positions
            for match in matches:
                groups = match['groups']
                line_position = int(round(match['top'], 0))
                
                # Iterate over each column and group to create a row for each combination
                for col, group in zip(columns, groups):
                    if group:
                        result.append({
                            'Column Name': col,
                            'Column Value': group,
                            'Line Position': line_position
                        })
                        
        return pd.DataFrame(result)

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
                    # for idx, group in enumerate(match.groups()[1:], start = 1):
                    for idx, reg in enumerate(match.regs[1:]):
                        # Determine the number of whitespace characters before the matched pattern
                        start_pos = len(line["text"][0:reg[0]].replace(" ", ""))
                        end_pos = len(line["text"][0:reg[1]].replace(" ", ""))-1
                        
                        # Draw a rectangle around the matched text
                        bbox = [line["chars"][start_pos]['x0'], line['top'], line["chars"][end_pos]['x1'], line['bottom']]
                        page_image.draw_rect(bbox, stroke='green', stroke_width=2)
                    
                    
        # Draw fixed text areas
        for area_name, bbox in self.config.fixed_text_areas.items():
            page_image.draw_rect(bbox, stroke='purple', stroke_width=2)
            # Add text label
            # page_image.draw_text(bbox[:2], area_name, fontsize=12, color='black')
        
        return page_image

    def extract_data_from_pdf(self, output_path=None, log_file_path=None, draw_image_path=None, create_subset=False, crop_meta=True):
        """
        Extract data from a PDF file based on the specified configuration.

        Args:
            output_path (str, optional): Output directory for saving extracted data.
            log_file_path (str, optional): Path to save the extraction log file.
            draw_image_path (str, optional): Path to save diagnostic visualization images.
            crop_meta (bool, optional): Whether to crop page when extracting metadata. Defaults to True.
            create_subset (bool, optional): Whether to create a subset PDF with pages of interest. Defaults to False.
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
            self.pages_of_interest = self.get_pages_of_interest()

        # Create subset PDF if requested
        if create_subset:
            if not self.subset_path and output_path:
                self.subset_path = os.path.join(output_path, os.path.basename(self.pdf_path).replace(".pdf", "_subset.pdf"))
            elif not self.subset_path:
                raise ValueError("Output path must be provided when create_subset is True")
            self.subset_pdf()
            pdf_to_process = self.subset_path
        else:
            pdf_to_process = self.pdf_path

        with pdfplumber.open(pdf_to_process) as pdf:
            # If using original PDF, we need to process specific pages
            # If using subset PDF, we can process all pages sequentially
            pages_to_process = range(len(pdf.pages)) if create_subset else [i-1 for i in self.pages_of_interest]
            
            for i, page_idx in enumerate(pages_to_process, start=1):
                page = pdf.pages[page_idx]
                logging.info(f"Processing page {i}/{len(pages_to_process)}...")
                
                # Extract table from cropped page and convert to dataframe
                page_cropped = page.crop(self.config.table_area) # Check to make sure that cropping does not impact y position
                table = page_cropped.find_table(table_settings)
                extracted_table = table.extract()
                table_df = pd.DataFrame(extracted_table)
                table_df.columns = self.config.table_column_names
                table_df['Line Position'] = [int(round(row.bbox[1], 0)) for row in table.rows]
                table_df = self.apply_column_filters(table_df, self.config.post_processing['column_filters'])
                table_df.insert(0, 'Page Number', self.pages_of_interest[i-1] if not create_subset else i)
                self.tables_df = pd.concat([self.tables_df, table_df], ignore_index=True)
                
                meta_df = self.extract_metadata_patterns(page_cropped if crop_meta else page, self.config.metadata_patterns)
                meta_df.insert(0, 'Page Number', self.pages_of_interest[i-1] if not create_subset else i)
                self.metadata_df = pd.concat([self.metadata_df, meta_df], ignore_index=True)
                
                # Extract fixed position text
                extracted_text = self.extract_fixed_text_areas(page, self.config.fixed_text_areas)
                text_df = pd.DataFrame(extracted_text, index=[0])
                text_df.insert(0, 'Page Number', self.pages_of_interest[i-1] if not create_subset else i)
                self.fixed_df = pd.concat([self.fixed_df, text_df], ignore_index=True)
                
                if draw_image_path:
                    page_image = self.draw_extraction_config(page)
                    page_image.save(draw_image_path.replace(".pdf", f"_page_{i}.png"))
                
                if draw_image_path:
                    page_image = self.draw_extraction_config(page)
                    page_image.save(draw_image_path.replace(".pdf", f"_page_{i}.png"))
        
        logging.info("Extraction completed.")

    def combine_extracted_data(self):
        # Pivot metadata to spread column names into separate columns
        meta_pivot = self.metadata_df.pivot_table(
            index=['Page Number', 'Line Position'],
            columns='Column Name',
            values='Column Value',
            aggfunc='first'
        ).reset_index()

        # Combine metadata with table data
        meta_pivot = pd.concat(
            [self.tables_df[['Page Number', 'Line Position']], meta_pivot],
            ignore_index=True
        ).sort_values(by=['Page Number', 'Line Position']).reset_index(drop=True)

        # Apply ffill within each page, and reset the index to keep 'Page Number'
        meta_pivot = meta_pivot.groupby('Page Number').apply(lambda x: x.ffill()).reset_index(drop=True)

        # Merge combined metadata back to tables
        self.combined_df = self.tables_df.merge(meta_pivot, on=['Page Number', 'Line Position'], how='left')
        self.combined_df = self.combined_df.merge(self.fixed_df, on=['Page Number'])
