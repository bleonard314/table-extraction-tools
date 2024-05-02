import fitz
def extract_pages_with_keywords(fname, keywords, remove_keywords=None, all_keywords=False, case_sensitive=True):
    """
    Extracts page numbers from a PDF document that contain specified keywords.

    Parameters:
    - fname: Path to the PDF document.
    - keywords: A list of keywords to search for within the PDF document.
    - remove_keywords: A list of keywords that, if found, disqualify a page.
    - all_keywords: Boolean indicating if all keywords must be present on a page.
    - case_sensitive: Boolean indicating if keyword matching should be case-sensitive.

    Returns:
    - A list of page numbers (1-indexed) that match the criteria.
    """
    doc = fitz.open(fname)
    pages_with_keywords = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()

        if not case_sensitive:
            text = text.lower()
            keywords = [keyword.lower() for keyword in keywords]
            if remove_keywords:
                remove_keywords = [keyword.lower() for keyword in remove_keywords]

        if all_keywords and all(keyword in text for keyword in keywords):
            pages_with_keywords.append((page_num + 1, text))  # PyMuPDF is 0-indexed
        elif any(keyword in text for keyword in keywords):
            pages_with_keywords.append((page_num + 1, text))

    if remove_keywords:
        pages_with_keywords = [page for page in pages_with_keywords if not any(keyword in page[1] for keyword in remove_keywords)]

    return [page[0] for page in pages_with_keywords]