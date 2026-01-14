from app import app, db
from model import User

with app.app_context():
    print("\nXXX DATABASE REPORT XXX")
    
    # 1. Get ALL users
    all_users = User.query.all()
    print(f"Total Users Found: {len(all_users)}")
    
    # 2. List them out
    for user in all_users:
        print(f" -> ID: {user.id} | Name: {user.username} | Role: '{user.role}'")
        
    print("XXXXXXXXXXXXXXXXXXXXXXX\n")