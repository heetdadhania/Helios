import os
import requests
from dotenv import load_dotenv

load_dotenv('.env')

admin_pwd = os.getenv('ADMIN_PASSWORD')
resp = requests.post('http://localhost:8000/api/v1/auth/login', json={'email': 'admin@helios.io', 'password': admin_pwd})
token = resp.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

for t in [1, 2, 3, 4, 5]:
    r = requests.get(f'http://localhost:8000/api/v1/oversight/dashboard/{t}?days=7', headers=headers)
    if r.status_code == 200:
        d = r.json().get('revenue_trend', {})
        pts = d.get('points', [])
        sum_rev = sum(float(p.get('total_revenue', 0)) for p in pts)
        sum_orders = sum(int(p.get('total_orders', 0)) for p in pts)
        card_rev = d.get('total_revenue', 0)
        card_orders = d.get('total_orders', 0)
        print(f"Tenant {t} 7d: {len(pts)} points | Card Rev: {card_rev} | Sum Rev: {sum_rev:.2f} | Card Orders: {card_orders} | Sum Orders: {sum_orders}")
