# pitschi-xapi
eXternal API for Pitschi


Torun pitschi: uvicorn pitschi.main:pitschixapi --host 0.0.0.0 --port 8000 --root-path /xapi 

To run dashboard: uvicorn dashboard.app:pitschixapi --host 0.0.0.0 --port 8001 --root-path /xapi