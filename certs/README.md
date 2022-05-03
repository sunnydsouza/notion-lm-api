## Instructions
Please generate and save the `server.crt` and `server.key` files in this directory

Generate the certificate and key using below -
```
# Reference https://stackoverflow.com/questions/29458548/can-you-add-https-functionality-to-a-python-flask-web-server/52295688#52295688
pip install pyopenssl

openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
```