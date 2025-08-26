# from bson import ObjectId

# def individual_serial(payment) -> dict:
#     return {
#         "_id": ObjectId(),
#         "status": payment.get("status"),
#         "txnid": payment.get("txnid"),
#         "amount": payment.get("amount"),
#         "firstname": payment.get("firstname"),
#         "email": payment.get("email"),
#         "details": payment.get("details", {})
#     }

# def serial_list(payments) -> list:
#     return [individual_serial(payment) for payment in payments]