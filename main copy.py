from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from pyngrok import ngrok
import os
import hashlib
import uuid
import requests
import time

# MongoDB imports
from config.database import collection_name
from models.model import payment_schema

# Load environment variables
load_dotenv()

app = FastAPI()

# Base directory for templates and static files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Mount static folder and templates folder safely
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# PayU credentials
MERCHANT_KEY = os.getenv("MERCHANT_KEY")
MERCHANT_SALT = os.getenv("MERCHANT_SALT")
PAYU_BASE_URL = os.getenv("PAYU_BASE_URL")
NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN")

# Set Ngrok auth token
ngrok.set_auth_token(NGROK_AUTH_TOKEN)

# Open a tunnel to FastAPI port
public_url = ngrok.connect(8000, bind_tls=True)
print("Ngrok Tunnel URL:", public_url)


# Helper: generate PayU hash
def generate_hash(txnid, amount, productinfo, firstname, email):
    amount = "{:.2f}".format(float(amount))
    hash_string = f"{MERCHANT_KEY}|{txnid}|{amount}|{productinfo}|{firstname}|{email}|||||||||||{MERCHANT_SALT}"
    print("Hash String Sent to PayU:", hash_string)
    return hashlib.sha512(hash_string.encode("utf-8")).hexdigest().lower(), amount


# Helper: get current Ngrok URL dynamically
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


# ----------------- FRONTEND PAGES -----------------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})


@app.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})


@app.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})


@app.get("/refund", response_class=HTMLResponse)
async def refund(request: Request):
    return templates.TemplateResponse("refund.html", {"request": request})


@app.get("/terms", response_class=HTMLResponse)
async def terms(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request})


@app.get("/pay", response_class=HTMLResponse)
async def pay_get(request: Request):
    return templates.TemplateResponse("pay.html", {"request": request})


# ----------------- PAYMENT INITIATION -----------------

@app.post("/pay")
async def pay_post(
    request: Request,
    amount: float = Form(...),
    firstname: str = Form(...),
    email: str = Form(...),
):
    txnid = uuid.uuid4().hex[:20]
    productinfo = 'Test Product'

    # Generate hash
    hashh, amount = generate_hash(txnid, amount, productinfo, firstname, email)

    # Get current Ngrok URL dynamically
    current_url = get_current_ngrok_url()

    payload = {
        "key": MERCHANT_KEY,
        "txnid": txnid,
        "amount": amount,
        "productinfo": productinfo,
        "firstname": firstname,
        "email": email,
        "phone": "9999999999",
        "surl": f"{current_url}/success",
        "furl": f"{current_url}/failure",
        "hash": hashh
    }

    # Save transaction as "initiated"
    collection_name.insert_one(payment_schema(payload, "initiated"))
    print(payload)

    return templates.TemplateResponse(
        "pay_form.html",
        {"request": request, "payload": payload, "payu_url": PAYU_BASE_URL},
    )


# ----------------- PAYU CALLBACKS -----------------

# ----------------- PAYU CALLBACKS -----------------

@app.api_route("/success", methods=["GET", "POST"])
async def success(request: Request):
    if request.method == "POST":
        # PayU server confirmation
        form = await request.form()
        data = dict(form)
        print("🎉 SUCCESS CALLBACK RECEIVED FROM PAYU 🎉", data)

        # Save in DB
        collection_name.insert_one(payment_schema(data, "success"))

        # Respond JSON for server-side log
        return JSONResponse(content={"status": "success", "details": data})

    # User redirect GET → show HTML page
    return templates.TemplateResponse(
        "success.html", {"request": request}
    )


@app.api_route("/failure", methods=["GET", "POST"])
async def failure(request: Request):
    if request.method == "POST":
        # PayU server confirmation
        form = await request.form()
        data = dict(form)
        print("💥 FAILURE CALLBACK RECEIVED FROM PAYU 💥", data)

        # Save in DB
        collection_name.insert_one(payment_schema(data, "failure"))

        return JSONResponse(content={"status": "failure", "details": data})

    # User redirect GET → show HTML page
    return templates.TemplateResponse(
        "failure.html", {"request": request}
    )


# ----------------- GET ALL PAYMENTS -----------------

@app.get("/payments")
async def get_payments():
    payments = list(collection_name.find({}, {"_id": 0}))
    return payments
