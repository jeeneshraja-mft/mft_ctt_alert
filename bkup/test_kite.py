from kiteconnect import KiteConnect

api_key = "hqszgobglsa0drch"
access_token = "l1w77ZjfbhgpJelEO4gUqd9im6gE5BPX"

kite = KiteConnect(api_key=api_key)
kite.set_access_token(access_token)

# Example instrument token (RELIANCE)
token = 738561

ltp = kite.ltp(token)

print("Live Data:")
print(ltp)