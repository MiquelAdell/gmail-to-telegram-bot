# Credentials

get credentials from
https://console.cloud.google.com/apis/credentials?project=project-name
replace credentials-example.json with your credentials file downloaded from the previous link

Download google credentials from google cloud, something like https://console.cloud.google.com/apis/credentials?hl=es-419&project=projectname-123456 and save it as credentials.json.

https://developers.google.com/gmail/api/quickstart/python?hl=es-419

run python main.py

it will open a browser window, login with your google account and allow the app to access your gmail account.

This should create a token.json with the user information

Get bot information form telegram (I used botfather). Copy .env-example to .env and replace the values with your own.

# Dependencies

```
pip install --upgrade -r requirements.txt
```

# Run

```
python main.py
```
