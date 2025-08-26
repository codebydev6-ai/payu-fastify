from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from pyngrok import ngrok
import os 
import hashlib
import uuid
import requests
import time



# Import MongoDB and schema
from config.database import collection_name
from models.model import payment_schema

app = FastAPI()
load_dotenv()


NGROK_URL = os.getenv("NGROK_URL")
print(NGROK_URL)
ngrok.set_auth_token("31mFlmCLbexCqua7vgkm1qlFPqR_sYrGdSrXHfL17UKmp15E")

# Test credentials
MERCHANT_KEY = os.getenv("MERCHANT_KEY")
MERCHANT_SALT =  os.getenv("MERCHANT_SALT")
PAYU_BASE_URL =  os.getenv("PAYU_BASE_URL")

def get_current_ngrok_url(retries=5, delay=1):
    for _ in range(retries):
        try:
            tunnels = requests.get("http://127.0.0.1:4040/api/tunnels").json()["tunnels"]
            for t in tunnels:
                if t["proto"] == "https":
                    return t["public_url"]
        except Exception as e:
            print("Ngrok API not ready, retrying...", e)
            time.sleep(delay)
    return public_url  # fallback to previously created tunnel


# Open a tunnel to port 8000
public_url = ngrok.connect(8000)
print("Ngrok Tunnel URL:", public_url)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates= Jinja2Templates(directory="templates")


def generate_hash(txnid, amount, productinfo, firstname, email):
    amount = "{:.2f}".format(float(amount))
    hash_string = f"{MERCHANT_KEY}|{txnid}|{amount}|{productinfo}|{firstname}|{email}|||||||||||{MERCHANT_SALT}"
    print("Hash String Sent to PayU:", hash_string) 
    return hashlib.sha512(hash_string.encode('utf-8')).hexdigest().lower(), amount



@app.get("/", response_class=HTMLResponse)
async def home(request : Request):
    return templates.TemplateResponse("index.html",{"request": request})


@app.get("/about", response_class=HTMLResponse)
async def about(request : Request):
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/contact", response_class=HTMLResponse)
async def contact(request : Request):
    return templates.TemplateResponse("contact.html",{"request": request})


@app.get("/privacy", response_class=HTMLResponse)
async def privacy(request : Request):
    return templates.TemplateResponse("privacy.html",{"request": request})

@app.get("/refund", response_class=HTMLResponse)
async def refund(request : Request):
    return templates.TemplateResponse("refund.html",{"request" : request})

@app.get("/terms", response_class=HTMLResponse)
async def terms(request : Request):
    return templates.TemplateResponse("terms.html",{"request" : request})


@app.get("/pay", response_class=HTMLResponse)
async def pay_get(request : Request):
    print(NGROK_URL)

    return templates.TemplateResponse("pay.html",{"request" : request} )

@app.post("/pay")
def pay(request : Request,amount: float = Form(...), firstname: str = Form(...), email: str = Form(...)):
   

    txnid = str(uuid.uuid4().hex[:20])  # unique transaction id
    productinfo = "Test Product"



    # Generate hash
    hashh, amount = generate_hash(txnid, amount, productinfo, firstname, email)
    print(hashh)
    # current_url = get_current_ngrok_url()
    current_url ="http://43.205.119.12:8000"
    # Prepare payload for PayU form
    payload = {
        "key": MERCHANT_KEY,
        "txnid": txnid,
        "amount": amount,
        "productinfo": productinfo,
        "firstname": firstname,
        "email": email,
        "phone": "99grok99999999",
        "surl": f"{current_url}/success",
        "furl": f"{current_url}/failure",
        "hash": hashh  
    }
     # ✅ Save payload before sending to PayU
    collection_name.insert_one(payment_schema(payload, "initiated"))
    print(payload)
    return templates.TemplateResponse(
        "pay_form.html",
        {"request": request, "payload": payload, "payu_url": PAYU_BASE_URL}
    )

    # Create an auto-submit form
    # form = f"""
    # <html>
    # <body onload="document.forms['payu_form'].submit()">
    #     <form action="{PAYU_BASE_URL}" method="post" name="payu_form">
    #         {''.join([f'<input type="hidden" name="{k}" value="{v}"/>' for k, v in payload.items()])}
    #         <button type="submit">Pay Now</button>
    #     </form>
    # </body>
    # </html>
    # """
    # return HTMLResponse(content=form)


# @app.post("/success")
# async def success(request: Request):
#     form = await request.form()
#     data = dict(form)
#     print("🎉 SUCCESS CALLBACK RECEIVED FROM PAYU 🎉")
#     print("Raw Data:", data)  
#     # Save to MongoDB
#     collection_name.insert_one(payment_schema(data, "success"))
#     return JSONResponse(content={"status": "success","details" : data})


@app.api_route("/success", methods=["GET", "POST"])
async def success_html(request: Request):
    # Handle POST from PayU (server callback)
    if request.method == "POST":
        form = await request.form()
        data = dict(form)
        print("🎉 SUCCESS CALLBACK RECEIVED FROM PAYU 🎉")
        print("Raw Data:", data)

        # Save to MongoDB
        try:
            collection_name.insert_one(payment_schema(data, "success"))
            print("Payment saved to MongoDB")
        except Exception as e:
            print(" Error saving payment:", e)

     # Render HTML page for user
        return templates.TemplateResponse("success.html", {"request": request, "data": data})



@app.post("/failure")
async def failure(request: Request):
    form = await request.form()
    data= dict(form)
    print("data cant send by test side")
    print("Raw Data:", data) 
    
    # Save to MongoDB
    collection_name.insert_one(payment_schema(data, "failure"))
    return JSONResponse(content={"status": "failure","data": data})


@app.get("/payments")
async def get_payments():
    payments = list(collection_name.find({}, {"_id": 0}))  # hide Mongo _id
    print(payments)
    return payments

