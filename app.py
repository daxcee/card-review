# https://docs.cloud.coinbase.com/sign-in-with-coinbase/docs/api-transactions
# https://developers.coinbase.com/docs/wallet/api-key-authentication
# https://medium.com/@samhagin/check-your-balance-on-coinbase-using-python-5641ff769f91
import json
from coinbase.wallet.client import Client
import hmac, hashlib, time, requests, os, codecs
from requests.auth import AuthBase
from dotenv import load_dotenv
import db

load_dotenv()
API_KEY = os.environ.get("API_KEY")
API_SECRET = os.environ.get("API_SECRET")
USDC_ACCOUNT_ID = os.environ.get("USDC_ACCOUNT_ID")

class CoinbaseWalletAuth(AuthBase):
    def __init__(self, api_key, secret_key):
        self.api_key = api_key
        self.secret_key = secret_key

    def __call__(self, request):
        timestamp = str(int(time.time()))
        message = timestamp + request.method + request.path_url + (request.body or '')
        signature = hmac.new(codecs.encode(self.secret_key), codecs.encode(message), hashlib.sha256).hexdigest()

        request.headers.update({
            'CB-ACCESS-SIGN': signature,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-KEY': self.api_key,
            'CB-VERSION': '2019-08-20'
        })
        return request

api_url = "https://api.coinbase.com/v2/"
auth = CoinbaseWalletAuth(API_KEY, API_SECRET)


def create_client():
    client = Client(API_KEY, API_SECRET)
    return client

# GET current user
def get_user(api_url,auth):
    r = requests.get(api_url + "user", auth=auth)
    return r.json()

# https://api.coinbase.com/v2/accounts
def get_accounts(api_url,auth):
    r = requests.get(f'{api_url}accounts', auth=auth)
    return r.json()


def get_auth_info(api_url,auth):
    r = requests.get(f'{api_url}user/auth', auth=auth)
    return r.json()


def save_accounts(client):
    with open('coinbase_accounts.json','w') as f:
        json.dump(client.get_accounts(limit=300),f)


def store_transactions_in_db(conn):
    coinbase_id = ''
    transaction_type = ''
    transaction_value = 0.0
    transaction_date = ''
    client = create_client()
    transactions = client.get_transactions(USDC_ACCOUNT_ID,limit=300)

    coinbase_id_set = set()
    coinbase_ids = db.get_coinbase_ids(conn)
    for id in coinbase_ids:
        coinbase_id_set.add(id[0])

    for transaction in transactions['data']:
        if transaction['id'] not in coinbase_id_set:
            coinbase_id = transaction['id']
            transaction_type = transaction['type']
            transaction_value = float(transaction['amount']['amount'])
            transaction_date = transaction['updated_at']
            db.add_transaction(conn, coinbase_id, transaction_type,transaction_value,transaction_date)


if __name__ == '__main__':
    conn = db.connect()
    db.create_table(conn)
    store_transactions_in_db(conn)