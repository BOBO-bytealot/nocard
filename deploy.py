#!/usr/bin/env python3
"""
小卡共享 COS 部署脚本
用法: python3 deploy.py
自动上传 index.html 到 COS 静态网站，强制设对 Content-Type，干掉 Content-Disposition
"""
import os, sys
from qcloud_cos import CosConfig, CosS3Client

# ── 配置区 ──
REGION = 'ap-guangzhou'
BUCKET = 'nocardanymore-1449768639'
LOCAL_FILE = os.path.join(os.path.dirname(__file__), 'index.html')
COS_KEY = 'index.html'

# 密钥 — 优先从环境变量读取
SECRET_ID = os.environ.get('COS_SECRET_ID', '')
SECRET_KEY = os.environ.get('COS_SECRET_KEY', '')

# 内容类型映射表
MIME_MAP = {
    '.html': 'text/html; charset=utf-8',
    '.css':  'text/css; charset=utf-8',
    '.js':   'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png':  'image/png',
    '.jpg':  'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif':  'image/gif',
    '.svg':  'image/svg+xml',
    '.ico':  'image/x-icon',
}

def get_content_type(filename):
    ext = os.path.splitext(filename)[1].lower()
    return MIME_MAP.get(ext, 'application/octet-stream')

def main():
    if not SECRET_ID or not SECRET_KEY:
        print('❌ 请先设置环境变量:')
        print('   export COS_SECRET_ID=你的SecretId')
        print('   export COS_SECRET_KEY=你的SecretKey')
        print('   然后重新运行: python3 deploy.py')
        sys.exit(1)

    if not os.path.exists(LOCAL_FILE):
        print(f'❌ 文件不存在: {LOCAL_FILE}')
        sys.exit(1)

    content_type = get_content_type(LOCAL_FILE)
    file_size = os.path.getsize(LOCAL_FILE)

    config = CosConfig(Region=REGION, SecretId=SECRET_ID, SecretKey=SECRET_KEY)
    client = CosS3Client(config)

    print(f'📤 上传: {LOCAL_FILE} → {COS_KEY}')
    print(f'   Content-Type: {content_type}')
    print(f'   大小: {file_size:,} bytes')

    with open(LOCAL_FILE, 'rb') as f:
        resp = client.put_object(
            Bucket=BUCKET,
            Key=COS_KEY,
            Body=f,
            ContentType=content_type,
            # 关键：不设 ContentDisposition，也要确保元数据里没有残留
            Metadata={},
        )

    print(f'✅ 上传成功')
    print(f'   ETag: {resp.get("ETag", "N/A")}')
    print(f'🌐 访问: https://{BUCKET}.cos-website.{REGION}.myqcloud.com/')

    # 额外保险：清理可能残留的 Content-Disposition 自定义头
    try:
        # 先查当前自定义头
        head = client.head_object(Bucket=BUCKET, Key=COS_KEY)
        headers_to_delete = {}
        for k in head:
            if k.lower().startswith('x-cos-meta-'):
                headers_to_delete[k] = ''
        # 如果有残留的 content-disposition 相关 meta，清掉
        if headers_to_delete:
            print('🧹 清理残留的自定义元数据...')
            # 用复制对象的方式清掉所有自定义 meta
            copy_source = {'Bucket': BUCKET, 'Key': COS_KEY, 'Region': REGION}
            client.copy_object(
                Bucket=BUCKET,
                Key=COS_KEY,
                CopySource=copy_source,
                CopyStatus='Replaced',
                ContentType=content_type,
                MetadataDirective='Replaced',  # 替换掉所有旧 meta
                Metadata={},
            )
            print('   ✅ 元数据已清理')
    except Exception as e:
        print(f'   ⚠️ 清理步骤跳过: {e}')

    print('\n💡 提示: 如果浏览器还是下载，等 1-2 分钟 CDN 缓存刷新后再试')

if __name__ == '__main__':
    main()
