import fitz  # PyMuPDF
import json
from elasticsearch import Elasticsearch, helpers
from sentence_transformers import SentenceTransformer

# Initialize Elasticsearch
es = Elasticsearch(hosts=["http://localhost:9200"])

# Load sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Extract text from PDF
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text += page.get_text()
    return text

# Load sample Q&A from JSON
def load_sample_qa(json_path):
    with open(json_path, 'r') as f:
        sample_qa = json.load(f)
    return sample_qa

# Preprocess and index the corpus
def preprocess_and_index_corpus(text, sample_qa):
    corpus = []
    for line in text.split('\n'):
        if line.strip():
            corpus.append({"question": line.strip(), "answer": line.strip()})
    
    # Add sample Q&A to corpus
    for qa in sample_qa:
        corpus.append({"question": qa['question'], "answer": qa['answer']})

    # Create Elasticsearch index if it doesn't exist
    if not es.indices.exists(index="wines_v2"):
        es.indices.create(
            index="wines_v2",
            body={
                "mappings": {
                    "properties": {
                        "question": {"type": "text"},
                        "answer": {"type": "text"},
                        "embedding": {"type": "dense_vector", "dims": 384}
                    }
                }
            }
        )

    # Encode the corpus using the sentence transformer model
    for doc in corpus:
        embedding = model.encode(doc['question'])
        doc['embedding'] = embedding.tolist()
    
    actions = [
        {
            "_index": "wines_v2",
            "_source": doc,
        }
        for doc in corpus
    ]
    helpers.bulk(es, actions)

# Path to the PDF file and JSON file
pdf_path = "Corpus.pdf"
json_path = "Sample Question Answers.json"

text = extract_text_from_pdf(pdf_path)
sample_qa = load_sample_qa(json_path)
preprocess_and_index_corpus(text, sample_qa)
