#!/usr/bin/env python
"""更详细的上传诊断"""
import os
import sys
import django
from io import BytesIO
from PIL import Image

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from image_search.views import index

# 检查视图函数
print("[诊断] 检查 index 视图...")
print(f"✓ index 函数: {index}")
print(f"✓ index.__name__: {index.__name__}")

# 列出装饰器
import inspect
print(f"✓ index 源代码位置: {inspect.getfile(index)}")

# 检查URL配置
from image_search import urls
print(f"\n[诊断] URL 配置...")
for pattern in urls.urlpatterns:
    if 'index' in str(pattern.name or ''):
        print(f"✓ 找到: {pattern.pattern} -> {pattern.callback}")

# 测试视图
print(f"\n[诊断] 测试视图函数...")
from django.test import RequestFactory
factory = RequestFactory()

# GET 请求
get_request = factory.get('/')
print(f"✓ GET / 请求:")
try:
    response = index(get_request)
    print(f"  状态码: {response.status_code}")
except Exception as e:
    print(f"  错误: {e}")

# POST 请求
print(f"\n✓ POST / 请求:")
img = Image.new('RGB', (50, 50), color='blue')
img_bytes = BytesIO()
img.save(img_bytes, format='PNG')
img_bytes.seek(0)
img_bytes.name = 'test.png'

post_request = factory.post('/', 
                             {'image': img_bytes, 'topk': '50'},
                             content_type='multipart/form-data')
post_request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'
post_request.META['HTTP_ACCEPT'] = 'application/json'
post_request.META['CSRF_COOKIE'] = 'dummy'

try:
    response = index(post_request)
    print(f"  状态码: {response.status_code}")
    if hasattr(response, 'content'):
        print(f"  响应: {response.content[:200]}")
except Exception as e:
    print(f"  错误: {e}")
    import traceback
    traceback.print_exc()

# 用 TestClient
print(f"\n[诊断] 用 TestClient 测试...")
client = Client(enforce_csrf_checks=False)
img = Image.new('RGB', (50, 50), color='blue')
img_bytes = BytesIO()
img.save(img_bytes, format='PNG')
img_bytes.seek(0)

response = client.post('/', {'image': img_bytes, 'topk': '50'},
                       HTTP_X_REQUESTED_WITH='XMLHttpRequest',
                       HTTP_ACCEPT='application/json')
print(f"✓ 响应状态码: {response.status_code}")
if response.status_code != 200 and response.status_code != 302:
    print(f"✗ 错误: {response.content}")
