#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号 API 客户端

提供微信公众号官方 API 的封装，支持：
- Access Token 获取和管理
- 图片素材上传
- 草稿箱管理
- 文章发布

要求：认证的服务号
"""

import json
import os
import re
import time
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlparse
import requests
from dotenv import load_dotenv

# 加载 skill 目录（scripts/ 的父目录）下的 .env 文件
_SKILL_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=_SKILL_DIR / ".env")


class WeChatAPIError(Exception):
    """微信 API 错误"""
    def __init__(self, errcode: int, errmsg: str):
        self.errcode = errcode
        self.errmsg = errmsg
        super().__init__(f"微信 API 错误 [{errcode}]: {errmsg}")


class WeChatAPIClient:
    """微信公众号 API 客户端"""
    
    # API 基础 URL
    API_BASE_URL = "https://api.weixin.qq.com/cgi-bin"
    
    # 错误码说明
    ERROR_CODES = {
        40001: "access_token 过期或无效",
        40013: "AppID 无效",
        40014: "AppSecret 无效",
        41001: "缺少 access_token",
        42001: "access_token 超时",
        45009: "接口调用超过限制",
        48001: "API 功能未授权",
        88000: "没有该接口权限",
        88001: "参数错误",
    }
    
    def __init__(self, appid: Optional[str] = None, appsecret: Optional[str] = None):
        """初始化客户端
        
        Args:
            appid: 公众号 AppID，不提供则从环境变量读取
            appsecret: 公众号 AppSecret，不提供则从环境变量读取
        """
        self.appid = appid or os.getenv('WECHAT_APPID')
        self.appsecret = appsecret or os.getenv('WECHAT_APPSECRET')
        
        if not self.appid or not self.appsecret:
            raise ValueError(
                "未配置 AppID 或 AppSecret。\n"
                "请设置环境变量 WECHAT_APPID 和 WECHAT_APPSECRET，\n"
                "或在初始化时传入参数。"
            )
        
        # Token 缓存
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        
        # Token 缓存文件
        self._token_cache_file = Path.home() / '.wechat_token_cache.json'
        self._load_token_cache()
    
    def _load_token_cache(self):
        """从缓存文件加载 token"""
        if self._token_cache_file.exists():
            try:
                with open(self._token_cache_file, 'r') as f:
                    cache = json.load(f)
                    self._access_token = cache.get('access_token')
                    self._token_expires_at = cache.get('expires_at', 0)
            except Exception as e:
                print(f"⚠️  加载 token 缓存失败: {e}")
    
    def _save_token_cache(self):
        """保存 token 到缓存文件"""
        try:
            cache = {
                'access_token': self._access_token,
                'expires_at': self._token_expires_at
            }
            with open(self._token_cache_file, 'w') as f:
                json.dump(cache, f)
        except Exception as e:
            print(f"⚠️  保存 token 缓存失败: {e}")
    
    def get_access_token(self, force_refresh: bool = False) -> str:
        """获取 access_token
        
        Args:
            force_refresh: 是否强制刷新 token
            
        Returns:
            access_token 字符串
            
        Raises:
            WeChatAPIError: API 调用失败
        """
        # 检查缓存是否有效（留 60 秒缓冲）
        if not force_refresh and self._access_token:
            if time.time() < self._token_expires_at - 60:
                return self._access_token
        
        # 获取新 token
        print("🔄 获取新的 access_token...")
        
        url = f"{self.API_BASE_URL}/token"
        params = {
            'grant_type': 'client_credential',
            'appid': self.appid,
            'secret': self.appsecret
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'errcode' in data:
            raise WeChatAPIError(data['errcode'], data.get('errmsg', '未知错误'))
        
        self._access_token = data['access_token']
        # expires_in 是秒数，默认 7200 秒（2小时）
        self._token_expires_at = time.time() + data.get('expires_in', 7200)
        
        # 保存到缓存
        self._save_token_cache()
        
        print(f"✅ access_token 获取成功，有效期至 {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self._token_expires_at))}")
        
        return self._access_token
    
    def _api_call(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """通用 API 调用方法
        
        Args:
            method: HTTP 方法 (GET, POST)
            endpoint: API 端点（相对于 API_BASE_URL）
            **kwargs: requests 库的其他参数
            
        Returns:
            API 响应数据
            
        Raises:
            WeChatAPIError: API 调用失败
        """
        # 获取 access_token
        token = self.get_access_token()
        
        # 构建完整 URL
        if '?' in endpoint:
            url = f"{self.API_BASE_URL}/{endpoint}&access_token={token}"
        else:
            url = f"{self.API_BASE_URL}/{endpoint}?access_token={token}"
        
        # 发起请求
        if method.upper() == 'GET':
            response = requests.get(url, **kwargs)
        elif method.upper() == 'POST':
            # 如果有 json 参数，确保中文不被转义
            if 'json' in kwargs:
                import json as json_module
                json_data = kwargs.pop('json')
                # 手动序列化 JSON，禁用 ASCII 转义
                kwargs['data'] = json_module.dumps(json_data, ensure_ascii=False).encode('utf-8')
                # 设置正确的 Content-Type
                if 'headers' not in kwargs:
                    kwargs['headers'] = {}
                kwargs['headers']['Content-Type'] = 'application/json; charset=utf-8'
            response = requests.post(url, **kwargs)
        else:
            raise ValueError(f"不支持的 HTTP 方法: {method}")
        
        # 解析响应
        data = response.json()
        
        # 检查错误
        if 'errcode' in data and data['errcode'] != 0:
            errcode = data['errcode']
            errmsg = data.get('errmsg', '未知错误')
            
            # 如果是 token 过期，尝试刷新后重试一次
            if errcode in [40001, 42001]:
                print("⚠️  access_token 已过期，正在刷新...")
                self.get_access_token(force_refresh=True)
                return self._api_call(method, endpoint, **kwargs)
            
            # 提供更友好的错误信息
            error_desc = self.ERROR_CODES.get(errcode, errmsg)
            raise WeChatAPIError(errcode, f"{error_desc} ({errmsg})")
        
        return data
    
    def upload_news_image(self, image_path: str) -> str:
        """上传图文消息内的图片
        
        用于文章正文中的图片，返回图片 URL。
        
        Args:
            image_path: 本地图片路径
            
        Returns:
            图片的 URL
            
        Raises:
            WeChatAPIError: 上传失败
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        
        print(f"📤 上传图片: {image_path}")
        
        with open(image_path, 'rb') as f:
            files = {'media': (os.path.basename(image_path), f, 'image/jpeg')}
            data = self._api_call('POST', 'media/uploadimg', files=files)
        
        url = data.get('url')
        if not url:
            raise WeChatAPIError(50000, "上传图片成功但未返回 URL")
        
        print(f"✅ 图片上传成功: {url}")
        return url
    
    def upload_permanent_material(self, image_path: str, material_type: str = 'image') -> str:
        """上传永久素材（封面图）
        
        Args:
            image_path: 本地图片路径
            material_type: 素材类型 (image, voice, video, thumb)
            
        Returns:
            素材的 media_id
            
        Raises:
            WeChatAPIError: 上传失败
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        
        print(f"📤 上传永久素材（封面图）: {image_path}")
        
        with open(image_path, 'rb') as f:
            files = {'media': (os.path.basename(image_path), f, 'image/jpeg')}
            data = self._api_call(
                'POST',
                f'material/add_material?type={material_type}',
                files=files
            )
        
        media_id = data.get('media_id')
        if not media_id:
            raise WeChatAPIError(50000, "上传素材成功但未返回 media_id")
        
        print(f"✅ 封面图上传成功，media_id: {media_id}")
        return media_id

    def download_image(self, image_url: str, timeout: int = 30) -> Optional[bytes]:
        """下载图片

        Args:
            image_url: 图片 URL
            timeout: 超时时间（秒）

        Returns:
            图片二进制数据，失败返回 None
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(image_url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"⚠️  下载图片失败 {image_url}: {e}")
            return None

    def upload_image_from_url(self, image_url: str) -> Optional[str]:
        """从 URL 下载图片并上传到微信公众号

        Args:
            image_url: 图片 URL

        Returns:
            微信图片 URL，失败返回 None
        """
        # 下载图片
        image_data = self.download_image(image_url)
        if not image_data:
            return None

        # 保存到临时文件
        try:
            # 从 URL 提取文件扩展名
            parsed = urlparse(image_url)
            path = parsed.path.lower()
            if '.png' in path:
                ext = '.png'
                content_type = 'image/png'
            elif '.gif' in path:
                ext = '.gif'
                content_type = 'image/gif'
            elif '.webp' in path:
                ext = '.webp'
                content_type = 'image/webp'
            else:
                ext = '.jpg'
                content_type = 'image/jpeg'

            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                f.write(image_data)
                temp_path = f.name

            try:
                # 上传到微信
                print(f"📤 上传图片: {image_url[:60]}...")
                with open(temp_path, 'rb') as f:
                    files = {'media': (f'image{ext}', f, content_type)}
                    data = self._api_call('POST', 'media/uploadimg', files=files)

                wechat_url = data.get('url')
                if wechat_url:
                    print(f"✅ 图片上传成功: {wechat_url[:60]}...")
                    return wechat_url
                else:
                    print(f"⚠️  上传成功但未返回 URL")
                    return None
            finally:
                # 删除临时文件
                os.unlink(temp_path)

        except Exception as e:
            print(f"⚠️  上传图片失败: {e}")
            return None

    def process_html_images(self, html_content: str) -> Tuple[str, int]:
        """处理 HTML 中的图片，上传到微信并替换链接

        Args:
            html_content: HTML 内容

        Returns:
            (处理后的 HTML, 成功替换的图片数量)
        """
        # 提取所有图片 URL
        img_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
        matches = re.findall(img_pattern, html_content)

        if not matches:
            return html_content, 0

        print(f"\n🖼️  发现 {len(matches)} 张图片，正在处理...")

        success_count = 0
        for original_url in matches:
            # 跳过已经是微信域名的图片
            if 'mmbiz.qpic.cn' in original_url or 'weixin.qq.com' in original_url:
                continue

            # 上传图片到微信
            wechat_url = self.upload_image_from_url(original_url)
            if wechat_url:
                # 替换 HTML 中的图片链接
                html_content = html_content.replace(original_url, wechat_url)
                success_count += 1

        print(f"✅ 成功上传 {success_count}/{len(matches)} 张图片\n")
        return html_content, success_count

    def create_draft(
        self,
        title: str,
        content: str,
        author: str = "",
        digest: str = "",
        cover_image_path: Optional[str] = None,
        thumb_media_id: Optional[str] = None,
        content_source_url: str = "",
        need_open_comment: int = 0,
        only_fans_can_comment: int = 0
    ) -> str:
        """创建草稿
        
        Args:
            title: 文章标题
            content: 文章内容（HTML）
            author: 作者
            digest: 文章摘要
            cover_image_path: 封面图片路径（与 thumb_media_id 二选一）
            thumb_media_id: 封面图的 media_id（与 cover_image_path 二选一）
            content_source_url: 原文链接
            need_open_comment: 是否打开评论（0 否，1 是）
            only_fans_can_comment: 是否仅粉丝可评论（0 否，1 是）
            
        Returns:
            草稿的 media_id
            
        Raises:
            WeChatAPIError: 创建失败
        """
        print(f"📝 创建草稿: {title}")
        
        # 封面图处理：支持两种方式
        # 1. 直接传入 thumb_media_id（使用后台已有图片）
        # 2. 传入 cover_image_path（上传新图片）
        final_thumb_media_id = thumb_media_id
        
        if not final_thumb_media_id:
            if cover_image_path:
                # 上传封面图
                final_thumb_media_id = self.upload_permanent_material(cover_image_path)
            else:
                raise ValueError(
                    "封面图是必填项！\n"
                    "请选择以下方式之一：\n"
                    "1. 使用 --cover-image 参数指定本地图片路径\n"
                    "2. 使用 --thumb-media-id 参数指定后台已有图片的 media_id\n"
                    "建议尺寸：900x383 或 2:1 比例"
                )
        else:
            print(f"✅ 使用已有封面图，media_id: {final_thumb_media_id}")
        
        # 限制标题长度（微信按字节计算，中文3字节/字符，限制192字节约64中文字符）
        # 为安全起见，限制为60个字符
        max_title_len = 60
        if len(title) > max_title_len:
            title = title[:max_title_len-3] + "..."
            print(f"⚠️  标题过长，已截断为: {title}")
        
        # 限制摘要长度（最多 120 字符）
        max_digest_len = 120
        if len(digest) > max_digest_len:
            digest = digest[:max_digest_len-3] + "..."
            print(f"⚠️  摘要过长，已截断")
        
        # 构建文章数据
        article = {
            "title": title,
            "author": author,
            "digest": digest,
            "content": content,
            "content_source_url": content_source_url,
            "thumb_media_id": final_thumb_media_id,
            "need_open_comment": need_open_comment,
            "only_fans_can_comment": only_fans_can_comment
        }
        
        # 创建草稿
        draft_data = {"articles": [article]}
        
        # 调试信息
        print(f"📊 提交数据:")
        print(f"   标题: {article['title']}")
        print(f"   标题长度: {len(article['title'])} 字符")
        print(f"   内容长度: {len(article['content'])} 字节")
        
        data = self._api_call(
            'POST',
            'draft/add',
            json=draft_data,
            headers={'Content-Type': 'application/json'}
        )
        
        media_id = data.get('media_id')
        if not media_id:
            raise WeChatAPIError(50000, "创建草稿成功但未返回 media_id")
        
        print(f"✅ 草稿创建成功！media_id: {media_id}")
        print(f"💡 请在公众号后台查看: https://mp.weixin.qq.com/ → 素材管理 → 草稿箱")
        
        return media_id
    
    def publish_draft(self, media_id: str) -> str:
        """发布草稿
        
        Args:
            media_id: 草稿的 media_id
            
        Returns:
            发布的文章 ID (publish_id)
            
        Raises:
            WeChatAPIError: 发布失败
        """
        print(f"🚀 发布草稿: {media_id}")
        
        publish_data = {"media_id": media_id}
        
        data = self._api_call(
            'POST',
            'freepublish/submit',
            json=publish_data,
            headers={'Content-Type': 'application/json'}
        )
        
        publish_id = data.get('publish_id')
        msg_data_id = data.get('msg_data_id')
        
        print(f"✅ 文章发布成功！")
        if publish_id:
            print(f"   publish_id: {publish_id}")
        if msg_data_id:
            print(f"   msg_data_id: {msg_data_id}")
        
        return publish_id or msg_data_id or media_id
    
    def get_material_list(
        self,
        material_type: str = 'image',
        offset: int = 0,
        count: int = 20
    ) -> Dict[str, Any]:
        """获取永久素材列表
        
        Args:
            material_type: 素材类型 (image, video, voice, news)
            offset: 从第几条开始获取（0 开始）
            count: 获取多少条（最大 20）
            
        Returns:
            素材列表数据，包含 total_count, item_count, item 等字段
            
        Raises:
            WeChatAPIError: 获取失败
        """
        print(f"📋 获取 {material_type} 素材列表...")
        
        # 构建请求数据
        request_data = {
            "type": material_type,
            "offset": offset,
            "count": min(count, 20)  # 微信限制最多 20 条
        }
        
        data = self._api_call(
            'POST',
            'material/batchget_material',
            json=request_data,
            headers={'Content-Type': 'application/json'}
        )
        
        total_count = data.get('total_count', 0)
        item_count = data.get('item_count', 0)
        
        print(f"✅ 成功获取 {item_count} 条素材（共 {total_count} 条）")
        
        return data


def main():
    """命令行测试工具"""
    import argparse
    
    parser = argparse.ArgumentParser(description='微信公众号 API 客户端测试工具')
    parser.add_argument('--test-token', action='store_true', help='测试获取 access_token')
    parser.add_argument('--test-upload', metavar='IMAGE', help='测试上传图片')
    parser.add_argument('--test-draft', metavar='TITLE', help='测试创建草稿')
    parser.add_argument('--cover-image', help='测试草稿的封面图片路径')
    parser.add_argument('--thumb-media-id', help='测试草稿的封面图 media_id')
    parser.add_argument('--list-materials', action='store_true', help='列出所有图片素材')
    parser.add_argument('--material-type', default='image', help='素材类型 (image, video, voice, news)')
    parser.add_argument('--count', type=int, default=20, help='获取数量（最大20）')
    
    args = parser.parse_args()
    
    try:
        client = WeChatAPIClient()
        
        if args.test_token:
            token = client.get_access_token()
            print(f"✅ Token: {token[:20]}...")
        
        elif args.test_upload:
            url = client.upload_news_image(args.test_upload)
            print(f"✅ 图片 URL: {url}")
        
        elif args.test_draft:
            media_id = client.create_draft(
                title=args.test_draft,
                content="<p>这是测试文章内容</p>",
                author="测试",
                digest="测试摘要",
                cover_image_path=args.cover_image,
                thumb_media_id=args.thumb_media_id
            )
            print(f"✅ 草稿 media_id: {media_id}")
        
        elif args.list_materials:
            data = client.get_material_list(
                material_type=args.material_type,
                count=args.count
            )
            
            # 格式化输出
            print("\n" + "=" * 80)
            print(f"素材类型: {args.material_type}")
            print(f"总数量: {data.get('total_count', 0)}")
            print("=" * 80)
            
            items = data.get('item', [])
            for i, item in enumerate(items, 1):
                media_id = item.get('media_id')
                name = item.get('name', '未命名')
                
                # 尝试修复文件名编码问题
                try:
                    # 如果文件名看起来是乱码（包含特殊字符），尝试重新编码
                    if any(ord(c) > 127 for c in name):
                        # 尝试先用 latin1 解码，再用 utf-8 编码
                        name = name.encode('latin1').decode('utf-8', errors='ignore')
                except:
                    # 如果编码转换失败，保持原样
                    pass
                
                update_time = item.get('update_time', 0)
                url = item.get('url', '')
                
                # 转换时间戳
                import datetime
                time_str = datetime.datetime.fromtimestamp(update_time).strftime('%Y-%m-%d %H:%M:%S')
                
                print(f"\n[{i}] {name}")
                print(f"    media_id: {media_id}")
                print(f"    更新时间: {time_str}")
                if url:
                    print(f"    链接: {url}")
            
            print("\n" + "=" * 80)
            print(f"💡 使用 media_id 作为封面图：")
            print(f"   python python/publish_to_wechat.py article.md --api --draft-only --thumb-media-id <media_id>")
        
        else:
            parser.print_help()
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
