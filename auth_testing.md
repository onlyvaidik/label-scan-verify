# Custom Email/Password JWT Authentication Playbook

Custom email/password authentication with JWT tokens for FastAPI + React + MongoDB web apps.

Step 1: MongoDB Verification
mongosh
use test_database
db.users.find({role: "admin"}).pretty()

Step 2: API Testing
curl -c cookies.txt -X POST http://localhost:8001/api/auth/login -H "Content-Type: application/json" -d '{"email":"admin@metrology.gov.in","password":"AdminMetrology@2026"}'
cat cookies.txt
curl -b cookies.txt http://localhost:8001/api/auth/me