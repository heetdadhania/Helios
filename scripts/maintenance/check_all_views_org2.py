import os
import requests
import json
from dotenv import load_dotenv

load_dotenv('.env')

admin_pwd = os.getenv('ADMIN_PASSWORD')
resp = requests.post('http://localhost:8000/api/v1/auth/login', json={'email': 'admin@helios.io', 'password': admin_pwd})
token = resp.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

for days_param in [7, 30, 0]:
    param_str = f"?days={days_param}" if days_param > 0 else ""
    resp = requests.get(f"http://localhost:8000/api/v1/oversight/dashboard/2{param_str}", headers=headers)
    data = resp.json()
    trend = data.get('revenue_trend', {})
    card_rev = trend.get('total_revenue', 0.0)
    card_orders = trend.get('total_orders', 0)
    points = trend.get('points', [])
    sum_rev = sum(float(p.get('total_revenue', 0.0)) for p in points)
    sum_orders = sum(int(p.get('total_orders', 0)) for p in points)
    print(f"\n=== VIEW {days_param}D (Points count: {len(points)}) ===")
    print(f"Card Total Revenue: {card_rev} | Plotted Points Sum Revenue: {sum_rev:.2f} | Match: {round(sum_rev, 2) == round(card_rev, 2)}")
    print(f"Card Total Orders: {card_orders} | Plotted Points Sum Orders: {sum_orders} | Match: {sum_orders == card_orders}")
    # Check if there are missing days in the range!
    if days_param > 0 and len(points) > 0:
        print(f"Date range: {points[0]['date']} to {points[-1]['date']}")
