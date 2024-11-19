# from table_extraction_tools.pdf_data_extraction import extract_data_from_pdf, select_rectangle
# import pdfplumber

# pdf_path = "input/Soil Remediation Report_SLC Community Gardens_R1-unlocked-1.pdf"
# pdf = pdfplumber.open(pdf_path)
# page = pdf.pages[51]
# page_image = page.to_image()
# print(select_rectangle(page_image.original))

from table_extraction_tools.pdf_data_extraction import PDFExtractionConfig, PDFExtraction

# Parameters
pdf_path = "examples/pdf_data_extraction/ex3-1_ocrd.pdf"
config_path = "config/pdf_data_extraction/test_america.yaml"

config = PDFExtractionConfig(config_path)
extractor = PDFExtraction(pdf_path, config)
extractor.extract_data_from_pdf()
extractor.combine_extracted_data()
extractor.combined_df.convert_dtypes().to_excel("test.xlsx")


# # Open the pdf as a pdfplumber object
# pdf = pdfplumber.open(pdf_path)
# # Get the first page as an image
# page = pdf.pages[8]
# page_image = page.to_image()

# bbox = (35, 132, 585, 145) # select_rectangle(page_image.original)

# table_settings = {
#     "vertical_strategy": "text",
#     "horizontal_strategy": "text",
#     "snap_y_tolerance": 5,
#     "intersection_x_tolerance": 10,
# }

# page_cropped = page.crop(bbox)
# # extracted_table = page_cropped.extract_table(table_settings)

# # Show extracted table
# image = page_cropped.to_image().debug_tablefinder(table_settings)


# print(bbox)

# Extract data from the pdf
# extract_data_from_pdf(config_path, pdf_path, output_dir="output")