import chromadb
from sentence_transformers import SentenceTransformer


# Load the same embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")


# Connect to the existing vector database
client = chromadb.PersistentClient(
    path="vector_db"
)

collection = client.get_collection(
    name="pdf_chunks"
)

def build_retrieval_query(topic, learning_objective=""):
    topic = topic.strip()
    learning_objective = learning_objective.strip()

    if learning_objective:
        return f"Topic: {topic}. Learning objective: {learning_objective}"

    return topic

def search_question(topic, learning_objective="", top_k=3):

    query = build_retrieval_query(topic, learning_objective)

    # Convert the query into a vector
    question_embedding = model.encode(query)

    # Search for the closest chunks
    results = collection.query(
        query_embeddings=[
            question_embedding.tolist()
        ],
        n_results=top_k
    )

    return results

def build_context(results):
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    context_parts = []

    for document, metadata in zip(documents, metadatas):
        page = metadata["page"]

        context_parts.append(
            f"[Page {page}]\n{document}"
        )

    combined_context = "\n\n".join(context_parts)

    return combined_context

def get_source_pages(results):
    metadatas = results["metadatas"][0]

    pages = []

    for metadata in metadatas:
        page = metadata["page"]

        if page not in pages:
            pages.append(page)

    return pages

def print_results(results):
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    print("\n========== Relevant Context ==========\n")

    for i, (document, metadata) in enumerate(
        zip(documents, metadatas),
        start=1
    ):
        print(f"Result {i}")
        print(f"Page: {metadata['page']}")
        print(f"Text:\n{document}")
        print("\n" + "-" * 50 + "\n")


if __name__ == "__main__":

    results = search_question(
        topic="Generic Classes",
        learning_objective="Explain the purpose and benefits of generic classes",
        top_k=3
    )

    context = build_context(results)
    source_pages = get_source_pages(results)

    print("\n========== Combined Context ==========\n")
    print(context)

    print("\n========== Source Pages ==========\n")
    print(source_pages)