from pymongo import MongoClient


client = MongoClient("mongodb+srv://logindb:logindb@cluster0.khjboto.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

db = client.website
collection_name = db["website_collection"]


