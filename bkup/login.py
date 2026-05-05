from kiteconnect import KiteConnect

api_key = "hqszgobglsa0drch"
api_secret = "8xnttgisqub0vbb6j5xxdd7wkkczk66u"

kite = KiteConnect(api_key=api_key)

print("\n1. Open this URL in browser:\n")
print(kite.login_url())

print("\n2. Login and complete 2FA")
print("3. After redirect (even if page fails), COPY request_token from URL")

request_token = input("\nPaste request_token here ONLY: ").strip()

# generate access token immediately
data = kite.generate_session(request_token, api_secret=api_secret)

access_token = data["access_token"]

print("\n=======================")
print("ACCESS TOKEN:")
print(access_token)
print("=======================\n")