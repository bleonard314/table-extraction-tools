import os
import tempfile
from PyPDF2 import PdfReader, PdfWriter
import pandas as pd
from typing import List, Optional, Tuple, Union, Dict
import fitz
import pytesseract
from PIL import Image
import io
import yaml
from utils import extract_pages_with_keywords

class PDFProcessor:
    def __init__(self, fname: str):#, file_path: str):
        # self.file_path = file_path
        self.fname = fname
        self.doc = fitz.open(fname)
    
    def is_searchable(self) -> bool:
        """Check if the PDF contains selectable text."""
        with fitz.open(self.file_path) as doc:
            for page in doc:
                if page.get_text():
                    return True  # Assume the document is searchable if any text is found
        return False
    
    def ocr_pdf(self, output_path: str) -> str:
        """Perform OCR on the PDF and save the text as a new PDF."""
        doc = fitz.open(self.file_path)
        ocr_doc = fitz.open()  # Create a new PDF to store OCR'd text

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap()  # Render page to an image
            img_bytes = pix.tobytes("png")  # Convert the image to PNG bytes
            img = Image.open(io.BytesIO(img_bytes))
            text = pytesseract.image_to_string(img)  # Perform OCR

            # Create a new PDF page with the OCR'd text
            ocr_page = ocr_doc.new_page(width=pix.width, height=pix.height)
            ocr_page.insert_text((0, 0), text)  # Insert OCR'd text at the top-left

        ocr_doc.save(output_path)  # Save the OCR'd PDF
        ocr_doc.close()
        doc.close()
        return output_path
    
    def subset_pdf_by_keywords(self, keywords: List[str], remove_keywords: Optional[List[str]] = None,
                            all_keywords: bool = False, case_sensitive: bool = True, pdfout: Optional[str] = None,
                            log_file: Optional[str] = None, pdf_split_outdir: Optional[str] = None,
                            return_log: bool = False, clean: bool = True) -> Union[str, Tuple[str, Optional[str]]]:
        """
        Subsets PDF lab report by keywords to extract only pages containing analytical lab results.
        Returns paths to both a PDF file with only the pages of interest and a spreadsheet logfile.

        Parameters:
        - fname: Input file name.
        - keywords: Keyword(s) that appear on pages of interest to extract (list of strings; e.g., ["Analytical Results"]).
        - remove_keywords: Keywords that appear on pages that are not of interest to extract (list of strings; e.g., ["Quality Control Samples"]).
        - all_keywords: Only extract pages with all keywords present (Boolean; defaults to False).
        - case_sensitive: Should case-sensitive keywords searches be performed (Boolean; defaults to True).
        - pdfout: Output PDF file name (e.g., "lab_result_pages.pdf"). None (default) creates a temporary file.
        - log_file: Output CSV file name (e.g., "lab_result_pages.csv"). None (default) creates a temporary file.
        - pdf_split_outdir: Output directory for splitting PDF file (e.g., "output"). None (default) splits to a temporary directory.
        - return_log: Return separate log file name? If False (default) only the PDF file name is returned.

        Returns:
        A tuple containing the path(s) to the output PDF and optionally the log CSV file.
        """
        # Create output directories if they don't exist
        if pdf_split_outdir is None:
            pdf_split_outdir = tempfile.mkdtemp()
        else:
            os.makedirs(pdf_split_outdir, exist_ok=True)

        print(f"Using {pdf_split_outdir} to split PDF file.")

        page_numbers = extract_pages_with_keywords(self.file_path, keywords, remove_keywords, all_keywords, case_sensitive)

        # Merge selected pages into a new PDF
        if pdfout is None:
            pdfout = tempfile.mktemp(suffix=".pdf")
        else:
            os.makedirs(os.path.dirname(pdfout), exist_ok=True)

        writer = PdfWriter()
        reader = PdfReader(self.file_path)
        for page_number in page_numbers:
            writer.add_page(reader.pages[page_number - 1])

        with open(pdfout, 'wb') as f_out:
            writer.write(f_out)

        # Create log dataframe
        log_df = pd.DataFrame({
            'file_name': [os.path.basename(self.file_path)] * len(page_numbers),
            'page_num': page_numbers
        })

        if log_file is None:
            log_file = os.path.splitext(pdfout)[0] + ".csv"
        else:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

        log_df.to_csv(log_file, index=False)

        if return_log:
            return pdfout, log_file
        else:
            return pdfout
        
    def load_yaml_config(self, locs: Union[str, Dict]) -> Dict:
        """Load and return the YAML configuration."""
        if isinstance(locs, str):
            with open(locs, 'r') as file:
                return yaml.safe_load(file)
        return locs

    def extract_text_from_area(self, page_num: int, area: List[float], columns: Optional[List[float]] = None) -> List[str]:
        """Extract text from a specified area (and columns if specified) on a PDF page."""
        page = self.doc.load_page(page_num - 1)
        text_blocks = page.get_text("blocks")
        extracted_texts = []

        for block in text_blocks:
            x0, y0, x1, y1, text, _, _ = block
            if x0 >= area[0] and y0 >= area[1] and x1 <= area[2] and y1 <= area[3]:
                if columns:
                    # Further processing for column extraction can be added here
                    pass
                extracted_texts.append(text.strip())
        return extracted_texts

    def extract_lab_results(self, locs: Union[str, Dict], pages: Optional[List[int]] = None,
                            log_file: Optional[str] = None, data_out: Optional[str] = None,
                            return_data: bool = True) -> pd.DataFrame:
        """
        Extract lab report results from pages of interest using configurations provided by `get_data_locs()`.
        """
        locs = self.load_yaml_config(locs)

        if pages is None:
            pages = list(range(1, len(self.doc) + 1))

        extracted_data = []

        for page_num in pages:
            extracted_texts = self.extract_text_from_area(page_num, locs['area'], locs.get('cols'))
            extracted_data.extend(extracted_texts)

        df = pd.DataFrame(extracted_data, columns=['Extracted Text'])

        if data_out:
            df.to_csv(data_out, index=False)
            if not return_data:
                return data_out

        return df

pdf_processor = PDFProcessor("output/ex3-1_ocrd_subset.pdf")
# subset_fname=pdf_processor.subset_pdf_by_keywords(keywords=["Client Sample Results"], remove_keywords=["Table of Contents"], pdfout="output/ex3-1_ocrd_subset.pdf")
pdf_processor.extract_lab_results("input/locs.yaml")

