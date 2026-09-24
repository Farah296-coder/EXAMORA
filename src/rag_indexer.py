import json
import os

import chromadb
import shutil
import embedding_model


# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


# ============================================================
# LOAD EXTRACTED PAGES
# ============================================================

def load_pages(json_path):

    with open(
        json_path,
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(file)


# ============================================================
# CHUNKING
# ============================================================

def chunk_text(
    text,
    chunk_size=500,
    overlap=100,
):

    chunks = []

    if not text:
        return chunks

    start = 0

    while start < len(text):

        end = start + chunk_size

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


def create_chunks(pages):

    all_chunks = []

    for page in pages:

        page_number = page["page"]
        text = page["text"]

        chunks = chunk_text(text)

        for chunk in chunks:

            all_chunks.append(
                {
                    "page": page_number,
                    "text": chunk,
                }
            )

    return all_chunks


# ============================================================
# EMBEDDING MODEL
# ============================================================



# ============================================================
# VECTOR DATABASE
# ============================================================

VECTOR_DB_PATH = os.path.join(
    BASE_DIR,
    "vector_db",
)


def open_collection(path, name="pdf_chunks"):
    """A store written by another Chroma version cannot be opened; start over."""
    try:
        chroma_client = chromadb.PersistentClient(path=path)
        return chroma_client, chroma_client.get_or_create_collection(name=name)
    except Exception as error:
        print(f"Vector store unusable ({error}); rebuilding it from scratch.")

    try:
        from chromadb.api.shared_system_client import SharedSystemClient

        SharedSystemClient._identifier_to_system.clear()
    except Exception:
        pass

    shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path, exist_ok=True)

    chroma_client = chromadb.PersistentClient(path=path)
    return chroma_client, chroma_client.get_or_create_collection(name=name)


client, collection = open_collection(VECTOR_DB_PATH)


# ============================================================
# CLEAR OLD PDF
# ============================================================

def clear_collection():

    try:

        existing = collection.get()

        ids = existing.get("ids", [])

        if ids:

            collection.delete(
                ids=ids
            )

        print(
            f"Removed {len(ids)} old chunks."
        )

    except Exception as e:

        print(
            f"Warning while clearing collection: {e}"
        )


# ============================================================
# STORE CHUNKS
# ============================================================

def store_chunks(
    chunks,
    clear_existing=True,
):

    if not chunks:

        print(
            "No chunks to store."
        )

        return 0

    if clear_existing:

        clear_collection()

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    embeddings = embedding_model.encode(
        texts,
        show_progress_bar=False,
    )

    ids = []
    documents = []
    metadatas = []

    for i, chunk in enumerate(chunks):

        ids.append(
            f"chunk_{i}"
        )

        documents.append(
            chunk["text"]
        )

        metadatas.append(
            {
                "page": chunk["page"]
            }
        )

    collection.upsert(
        ids=ids,
        embeddings=[
            embedding.tolist()
            for embedding in embeddings
        ],
        documents=documents,
        metadatas=metadatas,
    )

    print(
        f"Stored {len(chunks)} chunks successfully."
    )

    return len(chunks)


# ============================================================
# INDEX PDF
# ============================================================

def index_pdf(
    pdf_path,
    extracted_json_path=None,
):

    if not os.path.exists(pdf_path):

        raise FileNotFoundError(
            f"PDF not found: {pdf_path}"
        )

    if extracted_json_path is None:

        extracted_json_path = os.path.join(
            BASE_DIR,
            "output",
            "extracted_text.json",
        )

    # Import here to avoid circular imports
    from pdf_processor import (
        extract_pdf_text,
        save_extracted_text,
    )

    print(
        f"Processing PDF: {pdf_path}"
    )

    # --------------------------------------------------------
    # Extract
    # --------------------------------------------------------

    pages = extract_pdf_text(
        pdf_path
    )

    if not pages:

        raise ValueError(
            "No pages were found in the PDF."
        )

    print(
        f"Extracted {len(pages)} pages."
    )

    # --------------------------------------------------------
    # Save extracted text
    # --------------------------------------------------------

    save_extracted_text(
        pages,
        extracted_json_path,
    )

    # --------------------------------------------------------
    # Create chunks
    # --------------------------------------------------------

    chunks = create_chunks(
        pages
    )

    if not chunks:

        raise ValueError(
            "Could not extract usable text from the PDF."
        )

    print(
        f"Created {len(chunks)} chunks."
    )

    # --------------------------------------------------------
    # Store embeddings
    # --------------------------------------------------------

    stored_count = store_chunks(
        chunks,
        clear_existing=True,
    )

    return {
        "pages": len(pages),
        "chunks": stored_count,
        "extracted_json": extracted_json_path,
    }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    pdf_path = os.path.join(
        BASE_DIR,
        "data",
        "L22_New_Generic Class and Methods.pdf",
    )

    result = index_pdf(
        pdf_path
    )

    print(
        "Embedding/indexing completed!"
    )

    print(result)