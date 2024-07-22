import streamlit as st
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
import json

# Initialize Elasticsearch
es = Elasticsearch(hosts=["http://localhost:9200"])

# Load sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Load sample Q&A from JSON
def load_sample_qa(json_path):
    with open(json_path, 'r') as f:
        sample_qa = json.load(f)
    return sample_qa

# Elasticsearch query function using semantic search
def search_corpus(query, threshold=0.85):
    query_embedding = model.encode(query).tolist()
    script_query = {
        "script_score": {
            "query": {
                "match_all": {}
            },
            "script": {
                "source": "cosineSimilarity(params.query_embedding, 'embedding') + 1.0",
                "params": {
                    "query_embedding": query_embedding
                }
            }
        }
    }
    
    response = es.search(
        index="wines_v2",
        body={
            "size": 1,
            "query": script_query
        }
    )
    
    # Check if the best result meets the relevance threshold
    if response['hits']['hits']:
        score = response['hits']['hits'][0]['_score']
        answer = response['hits']['hits'][0]['_source']['answer']
        if score > threshold:
            return answer
    return None

# Streamlit app
def main():
    st.title("Wine Chatbot")
    if 'history' not in st.session_state:
        st.session_state['history'] = []

    # Create a form to submit the question
    with st.form(key='my_form', clear_on_submit=True):
        user_input = st.text_input("You:", key="input")
        submit_button = st.form_submit_button(label='Send')
    
    if submit_button:
        st.session_state['history'].append({'user': user_input})

        # Search sample Q&A first
        sample_qa = load_sample_qa("Sample Question Answers.json")
        predefined_answer = next((qa['answer'] for qa in sample_qa if qa['question'].lower() == user_input.lower()), None)
        
        if predefined_answer:
            answer = predefined_answer
        else:
            # Search corpus using semantic search
            answer = search_corpus(user_input)
            if not answer:
                answer = "Please contact our business directly for more information."

        st.session_state['history'].append({'bot': answer})

    # Display chat history
    for chat in st.session_state['history']:
        if 'user' in chat:
            st.write(f"You: {chat['user']}")
        if 'bot' in chat:
            st.write(f"Bot: {chat['bot']}")

if __name__ == '__main__':
    main()
