from database import SessionLocal
from models import Client
from datetime import datetime

def create_dummy_clients():
    """Create 10 dummy clients for testing purposes"""
    db = SessionLocal()
    try:
        existing_clients = db.query(Client).count()
        if existing_clients > 0:
            print(f"Clients already exist ({existing_clients} found)")
            return
        
        dummy_clients = [
            {
                "full_name": "John Smith",
                "email": "john.smith@example.com",
                "phone_number": "(555) 123-4567",
                "date_of_birth": datetime(1985, 3, 15).date(),
                "sex": "Male",
                "organization": "ACME Corporation",
                "employer": "Tech Solutions Inc",
                "status": "active",
                "risk_score": "Medium"
            },
            {
                "full_name": "Sarah Johnson",
                "email": "sarah.j@example.com",
                "phone_number": "(555) 234-5678",
                "date_of_birth": datetime(1990, 7, 22).date(),
                "sex": "Female",
                "organization": "Global Dynamics",
                "employer": "Marketing Pro LLC",
                "status": "pending",
                "risk_score": "Low"
            },
            {
                "full_name": "Michael Brown",
                "email": "m.brown@example.com",
                "phone_number": "(555) 345-6789",
                "date_of_birth": datetime(1982, 11, 8).date(),
                "sex": "Male",
                "organization": "Innovation Labs",
                "employer": "Data Systems Corp",
                "status": "active",
                "risk_score": "High"
            },
            {
                "full_name": "Emily Davis",
                "email": "emily.davis@example.com",
                "phone_number": "(555) 456-7890",
                "date_of_birth": datetime(1988, 5, 12).date(),
                "sex": "Female",
                "organization": "Future Tech",
                "employer": "Creative Agency",
                "status": "active",
                "risk_score": "Medium"
            },
            {
                "full_name": "David Wilson",
                "email": "d.wilson@example.com",
                "phone_number": "(555) 567-8901",
                "date_of_birth": datetime(1975, 9, 30).date(),
                "sex": "Male",
                "organization": "Enterprise Solutions",
                "employer": "Consulting Group",
                "status": "pending",
                "risk_score": "Low"
            },
            {
                "full_name": "Lisa Anderson",
                "email": "lisa.anderson@example.com",
                "phone_number": "(555) 678-9012",
                "date_of_birth": datetime(1992, 1, 18).date(),
                "sex": "Female",
                "organization": "Digital Ventures",
                "employer": "Software House",
                "status": "active",
                "risk_score": "Medium"
            },
            {
                "full_name": "Robert Taylor",
                "email": "robert.taylor@example.com",
                "phone_number": "(555) 789-0123",
                "date_of_birth": datetime(1980, 4, 25).date(),
                "sex": "Male",
                "organization": "Strategic Partners",
                "employer": "Finance Corp",
                "status": "active",
                "risk_score": "High"
            },
            {
                "full_name": "Jennifer Martinez",
                "email": "jennifer.m@example.com",
                "phone_number": "(555) 890-1234",
                "date_of_birth": datetime(1987, 12, 3).date(),
                "sex": "Female",
                "organization": "Modern Systems",
                "employer": "Healthcare Plus",
                "status": "pending",
                "risk_score": "Low"
            },
            {
                "full_name": "Christopher Lee",
                "email": "chris.lee@example.com",
                "phone_number": "(555) 901-2345",
                "date_of_birth": datetime(1983, 8, 14).date(),
                "sex": "Male",
                "organization": "Advanced Technologies",
                "employer": "Research Institute",
                "status": "active",
                "risk_score": "Medium"
            },
            {
                "full_name": "Amanda White",
                "email": "amanda.white@example.com",
                "phone_number": "(555) 012-3456",
                "date_of_birth": datetime(1991, 6, 7).date(),
                "sex": "Female",
                "organization": "NextGen Solutions",
                "employer": "Design Studio",
                "status": "pending",
                "risk_score": "Low"
            }
        ]
        
        for client_data in dummy_clients:
            client = Client(**client_data)
            db.add(client)
        
        db.commit()
        print("10 dummy clients created successfully")
        
    except Exception as e:
        print(f"Error creating dummy clients: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_dummy_clients()