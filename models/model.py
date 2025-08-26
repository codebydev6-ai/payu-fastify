from bson import ObjectId

def payment_schema(data: dict, status: str):
    return {
        "_id": ObjectId(),
        "status": status,
        **data 
    }