@echo off
set BASE_URL=https://check-ticket-1hyd.onrender.com
echo [Staff Login]...
curl -s -X POST %BASE_URL%/api/auth/login -H "Content-Type: application/json" -d @staff_login.json > staff_resp.json
type staff_resp.json
echo.
echo [Customer Login]...
curl -s -X POST %BASE_URL%/api/customer/login -H "Content-Type: application/json" -d @login_test.json > customer_resp.json
type customer_resp.json
echo.
