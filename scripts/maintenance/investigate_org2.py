import os
import requests
import json
from dotenv import load_dotenv

load_dotenv('.env')

admin_pwd = os.getenv('ADMIN_PASSWORD')
resp = requests.post('http://localhost:8000/api/v1/auth/login', json={'email': 'admin@helios.io', 'password': admin_pwd})
token = resp.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

# Get 7-day dashboard for tenant 2
resp_7d = requests.get('http://localhost:8000/api/v1/oversight/dashboard/2?days=7', headers=headers)
print('HTTP Status:', resp_7d.status_code)
data_7d = resp_7d.json()
trend = data_7d.get('revenue_trend', {})
print('\n=== Revenue Trend 7D Metadata ===')
print('days:', trend.get('days'))
print('total_revenue (Card):', trend.get('total_revenue'))
print('total_orders (Card):', trend.get('total_orders'))
print('data_as_of:', trend.get('data_as_of'))

points = trend.get('points', [])
print(f'\n=== Raw Points Count: {len(points)} ===')
sum_rev = 0.0
sum_orders = 0
for i, p in enumerate(points):
    print(f"Point {i+1}: date={p.get('date')}, total_revenue={p.get('total_revenue')}, total_orders={p.get('total_orders')}, avg_order_value={p.get('avg_order_value')}, total_quantity={p.get('total_quantity')}")
    sum_rev += float(p.get('total_revenue', 0.0))
    sum_orders += int(p.get('total_orders', 0))

print(f'\nSum of points revenue: {sum_rev:.2f} vs Card total_revenue: {trend.get("total_revenue")}')
print(f'Sum of points orders: {sum_orders} vs Card total_orders: {trend.get("total_orders")}')
