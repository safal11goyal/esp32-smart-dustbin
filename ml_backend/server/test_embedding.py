from sentence_transformers import SentenceTransformer


model = SentenceTransformer("all-MiniLM-L6-v2")

embedding = model.encode("GenAI is amazing")
print(len(embedding))
