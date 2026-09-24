import json
import os
import pymupdf


def extract_pdf_text(pdf_path):
    """
    Extract text from every page of a PDF.
    Returns a list of:
    {
        "page": 1,
        "text": "..."
    }
    """

    document = pymupdf.open(pdf_path)

    pages = []

    for page_number, page in enumerate(document, start=1):

        text = page.get_text()

        pages.append(
            {
                "page": page_number,
                "text": text,
            }
        )

    document.close()

    return pages


def save_extracted_text(pages, output_path):
    """
    Save extracted PDF text as JSON.
    """

    os.makedirs(
        os.path.dirname(output_path),
        exist_ok=True,
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            pages,
            file,
            ensure_ascii=False,
            indent=4,
        )


if __name__ == "__main__":

    BASE_DIR = os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )

    pdf_path = os.path.join(
        BASE_DIR,
        "data",
        "L22_New_Generic Class and Methods.pdf",
    )

    output_path = os.path.join(
        BASE_DIR,
        "output",
        "extracted_text.json",
    )

    pages = extract_pdf_text(pdf_path)

    save_extracted_text(
        pages,
        output_path,
    )

    print(
        f"Done! Output saved to: {output_path}"
    )