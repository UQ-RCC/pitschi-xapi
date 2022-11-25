# pitschi-xapi
eXternal API for Pitschi


To run pitschi: uvicorn pitschi.main:pitschixapi --host 0.0.0.0 --port 8000 --root-path /xapi 

#To run dashboard: uvicorn dashboard.app:pitschi --host 0.0.0.0 --port 8001

# developement instructions
### Steps to run xpi on VM:

1. Follow instructions to install Python on the VM. (If you install Python version 3.4 or later, PIP is included by default, otherwise, install pip)
2. Install uvicorn using "pip install uvicorn" command.
3. Edit pitschixapi.conf to include backend connection settings.
4. Install the required modules given in requirement.txt file using "pip install <module_name>" command
5. Run the project using "uvicorn pitschi.main:pitschixapi --host <VM_IP> --port 8000 --root-path /xapi" 



