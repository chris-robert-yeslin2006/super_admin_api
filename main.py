from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, organizations, admins, students, analytics

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(admins.router)
app.include_router(students.router)
app.include_router(analytics.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the API"}