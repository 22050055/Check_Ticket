@echo off
set BASE_URL=https://check-ticket-1hyd.onrender.com
echo [1/3] Registering Customer (v4)...
curl -s -X POST %BASE_URL%/api/customer/register -H "Content-Type: application/json" -d @register_test.json
echo.
echo [2/3] Logging in Customer...
curl -s -X POST %BASE_URL%/api/customer/login -H "Content-Type: application/json" -d @register_test.json > customer_resp.json
type customer_resp.json
echo.
