import fitz  # PyMuPDF
import yaml
import os

def get_data_locs(fname, page=1, n_cols=0, nms=None, n_meta=0, n_extra=0, extra_nms=None,
                  hi_def=True, locs=None, yaml_out=None, step_meta=True, top_tol=5):
    dat = {"areas": None, "cols": None, "names": None, "meta": None, "extra": None}

    # Load existing locations if provided
    if isinstance(locs, str):
        _, file_extension = os.path.splitext(locs)
        if file_extension.lower() == '.yaml':
            with open(locs, 'r') as file:
                locs = yaml.safe_load(file)
        else:
            raise ValueError("Input file extension should be 'yaml'.")

    # Assuming locs is a dictionary with user-specified values if directly passed
    if isinstance(locs, dict):
        dat.update(locs)

    # Example for manual area and columns input:
    # dat['area'] = [50, 50, 550, 800]  # Example area: left, bottom, right, top coordinates
    # dat['cols'] = [60, 110, 160, 210, 260]  # Example column boundaries (x-coordinates)

    if 'area' not in locs:
        print("Manually set the area coordinates in the locs dictionary.")
    
    if 'cols' not in locs:
        if n_cols > 0:
            # Simplified automatic column detection
            dat['cols'] = auto_detect_columns(fname, page, dat['area'])

    # Manual setup for names and metadata if not provided
    if 'names' not in locs and nms is not None:
        dat['names'] = nms
    if 'meta' not in locs and n_meta > 0:
        print("Manually set the metadata names in the locs dictionary.")

    # Output to YAML if specified
    if yaml_out:
        with open(yaml_out, 'w') as file:
            yaml.dump(dat, file)
        return yaml_out
    else:
        return dat

def auto_detect_columns(fname, page, area):
    """Simplistic column detection within a specified area on a page."""
    doc = fitz.open(fname)
    page = doc.load_page(page - 1)  # Page numbers in PyMuPDF are 0-based
    
    # Convert area to the PyMuPDF rect format
    rect = fitz.Rect(area)
    
    # Extract text blocks within the area
    blocks = page.get_text("blocks", clip=rect)
    
    # Extract x0 (left boundary) of text blocks
    x0_values = [block[0] for block in blocks]
    
    # Sort and filter unique values as potential column starts
    unique_x0 = sorted(set(x0_values))
    
    return unique_x0

# Usage example
locs = {
    'area': [50, 50, 550, 800]  # Example coordinates to be replaced by actual manual inputs
    # 'cols': [60, 110, 160, 210, 260]  # If columns are known, otherwise they'll be detected
}
fname = "path/to/your/document.pdf"
page = 1
yaml_out = "data_locs.yaml"

locs_output = get_data_locs(fname, page
