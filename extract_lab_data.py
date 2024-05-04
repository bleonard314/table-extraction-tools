# Load the template config file

from src.pdf_data_extractor.pdf_data_extractor import extract_data_from_pdf, select_rectangle

# Parameters
base_path = "//integral-corp.com/data/CF1100-CF3999/CF3493_JaitePaperMill_LW/Library/EECA and Appendices/"
pdf_path = base_path + "TAB 16 - Appendix B-4-Site Investigation Lab Reports-2016 Field Activities.pdf"
# pdf_path = "input/gi_combined.pdf"
config_path = "input/test_america.yaml"

# Extract data from the pdf
# extract_data_from_pdf(config_path, pdf_path, output_dir="output")
extract_data_from_pdf(config_path, pdf_path, output_dir="lab_pdf_scraper")