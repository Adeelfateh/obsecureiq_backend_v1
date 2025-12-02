from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

# Import database setup
from database import create_tables

# Import all routers
from users import router as users_router, create_default_admin
from assign import router as assign_router
from clientemail import router as clientemail_router
from clientphonenumber import router as clientphonenumber_router
from clientrelativeandassociate import router as clientrelative_router
from clientusername import router as clientusername_router
from clientaddress import router as clientaddress_router
from clientsocial import router as clientsocial_router
from clientresidentialheatmap import router as clientresidential_router
from clientgovernment import router as clientgovernment_router
from facialrecognition import router as facialrecognition_router
from digitalrecog import router as digitalrecog_router
from clientbusiness import router as clientbusiness_router
from clientbrokerscreen import router as clientbrokerscreen_router
from clientbreached import router as clientbreached_router
from documentgeneration import router as documentgeneration_router
from clientserpanalysis import router as clientserpanalysis_router
from clientaianalysis import router as clientaianalysis_router
from clientleakdataset import router as clientleakdataset_router
from clientosintmodule import router as clientosintmodule_router
from clientmatching import router as clientmatching_router
from clientgenerateddocuments import router as clientgenerateddocuments_router

# FastAPI setup
app = FastAPI(
    title="ObscureIQ Backend API",
    description="Complete authentication system with client management",
    version="1.0.0"
)

# Upload directory setup
UPLOAD_DIR = Path("uploads/client_images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins during development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
create_tables()

# Create default admin user
create_default_admin()

# Register all routers with proper tags
app.include_router(users_router, tags=["Authentication & User Management"])
app.include_router(assign_router, tags=["Client Assignment"])
app.include_router(clientemail_router, tags=["Client Emails"])
app.include_router(clientphonenumber_router, tags=["Client Phone Numbers"])
app.include_router(clientrelative_router, tags=["Client Relatives & Associates"])
app.include_router(clientusername_router, tags=["Client Usernames"])
app.include_router(clientaddress_router, tags=["Client Addresses"])
app.include_router(clientsocial_router, tags=["Client Social Media"])
app.include_router(clientresidential_router, tags=["Client Residential & Heatmap"])
app.include_router(clientgovernment_router, tags=["Government Records"])
app.include_router(facialrecognition_router, tags=["Facial Recognition"])
app.include_router(digitalrecog_router, tags=["Digital Recognition"])
app.include_router(clientbusiness_router, tags=["Client Business Information"])
app.include_router(clientbrokerscreen_router, tags=["Broker Screen Records"])
app.include_router(clientbreached_router, tags=["Breached Records"])
app.include_router(documentgeneration_router, tags=["Document Generation"])
app.include_router(clientserpanalysis_router, tags=["SERP Analysis"])
app.include_router(clientaianalysis_router, tags=["AI Analysis"])
app.include_router(clientleakdataset_router, tags=["Leaked Datasets"])
app.include_router(clientosintmodule_router, tags=["OSINT Module Results"])
app.include_router(clientmatching_router, tags=["Client Matching Results"])
app.include_router(clientgenerateddocuments_router, prefix="/api", tags=["Generated Documents"])

# Root endpoint
@app.get("/", tags=["Root"])
def root():
    return {
        "message": "ObscureIQ Backend API is running",
        "version": "1.0.0",
        "status": "active"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)