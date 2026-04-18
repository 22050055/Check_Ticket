@echo off
set TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4MGM4ZWZiMi1kMTc3LTQwZjEtYmYwYS1mOWNlMTk4YzE2YjYiLCJyb2xlIjoibWFuYWdlciIsImdhdGVfaWQiOm51bGwsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjE3NzY1MjE2Njl9.PyRR0I1RmAiwU1p43uGGdCJf96FDKIyp0HvOfDbI6OQ
curl -s -X GET https://check-ticket-1hyd.onrender.com/api/customer/all -H "Authorization: Bearer %TOKEN%" > customers.json
type customers.json
