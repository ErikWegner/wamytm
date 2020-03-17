Development documentation
=========================

Retrieving a token from keycloak
--------------------------------

Grant type: Grant Type  
Callback URL: http://localhost:8000/  
Auth URL: https://localhost:8443/auth/realms/wamytmdev/protocol/openid-connect/auth   
Access Token URL: https://localhost:8443/auth/realms/wamytmdev/protocol/openid-connect/token  
Client ID: wamytm  
Client Secret: 6fd1a212-deed-450c-b28d-3170a0c6102c

Sending a token to the API
--------------------------

Add the header `Authorization` with the value `Bearer keycloak <token>`
