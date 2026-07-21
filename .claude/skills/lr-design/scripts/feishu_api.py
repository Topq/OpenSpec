#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""飞书开放平台API封装 - 用于文档下载和上传"""

import requests
import json
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

class FeishuAPIError(Exception):
    """飞书API调用异常"""
    pass

class FeishuAPI:
    """飞书开放平台API客户端"""

    def __init__(self, app_id: str, app_secret: str, base_url: str = "https://open.feishu.cn"):
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.token_expire_time: float = 0

    def _ensure_token(self):
        """确保token有效，自动刷新"""
        if self.access_token and time.time() < self.token_expire_time - 300:
            return

        url = f"{self.base_url}/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {"app_id": self.app_id, "app_secret": self.app_secret}

        response = requests.post(url, headers=headers, json=data)
        result = response.json()

        if result.get("code") != 0:
            raise FeishuAPIError(f"获取token失败: {result}")

        self.access_token = result["tenant_access_token"]
        self.token_expire_time = time.time() + result.get("expire", 7200)

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """统一的API请求方法，带重试和错误处理"""
        self._ensure_token()

        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.request(method, url, headers=headers, **kwargs)
                result = response.json()

                if result.get("code") == 0:
                    return result

                # Token过期，刷新后重试
                if result.get("code") == 99991663:
                    self.access_token = None
                    self._ensure_token()
                    continue

                # 限流，指数退避
                if result.get("code") == 99991400:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue

                raise FeishuAPIError(f"API调用失败: {result}")

            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    raise FeishuAPIError(f"网络请求失败: {e}")
                time.sleep(2 ** attempt)

        raise FeishuAPIError(f"API调用失败: 重试{max_retries}次后仍失败")

    def parse_document_url(self, url: str) -> Tuple[str, str]:
        """
        解析飞书文档URL，返回 (doc_type, token)
        支持格式:
        - https://{domain}.feishu.cn/wiki/{wiki_token}
        - https://{domain}.feishu.cn/docx/{docx_token}
        """
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')

        if len(path_parts) >= 2:
            doc_type = path_parts[0]  # wiki 或 docx
            token = path_parts[1]
            return doc_type, token

        raise ValueError(f"无法解析文档URL: {url}")

    def get_docx_from_wiki(self, wiki_token: str) -> str:
        """从wiki token获取docx token"""
        result = self._request(
            "GET",
            "/open-apis/wiki/v2/spaces/get_node",
            params={"token": wiki_token}
        )

        node = result.get("data", {}).get("node", {})
        obj_token = node.get("obj_token")
        obj_type = node.get("obj_type")

        if obj_type != "docx":
            raise FeishuAPIError(f"Wiki节点类型不是docx: {obj_type}")

        return obj_token

    def get_document_info(self, document_id: str) -> Dict:
        """获取文档元信息"""
        result = self._request(
            "GET",
            f"/open-apis/docx/v1/documents/{document_id}"
        )

        doc = result.get("data", {}).get("document", {})
        return {
            "document_id": doc.get("document_id"),
            "revision_id": doc.get("revision_id"),
            "title": doc.get("title", "无标题"),
        }

    def get_document_blocks(self, document_id: str) -> List[Dict]:
        """获取文档所有块（自动分页）"""
        all_blocks = []
        page_token = None

        while True:
            params = {"page_size": 500}
            if page_token:
                params["page_token"] = page_token

            result = self._request(
                "GET",
                f"/open-apis/docx/v1/documents/{document_id}/blocks",
                params=params
            )

            items = result.get("data", {}).get("items", [])
            all_blocks.extend(items)

            page_token = result.get("data", {}).get("page_token")
            if not page_token:
                break

        return all_blocks

    def get_document_raw_content(self, document_id: str) -> str:
        """获取文档纯文本内容"""
        result = self._request(
            "GET",
            f"/open-apis/docx/v1/documents/{document_id}/raw_content"
        )

        return result.get("data", {}).get("content", "")

    def download_images(self, file_tokens: List[str], output_dir: Path) -> Dict[str, Path]:
        """
        逐个下载文档图片
        返回: {file_token: local_path}
        """
        self._ensure_token()
        output_dir.mkdir(parents=True, exist_ok=True)

        headers = {"Authorization": f"Bearer {self.access_token}"}
        downloaded = {}

        for file_token in file_tokens:
            url = f"{self.base_url}/open-apis/drive/v1/medias/{file_token}/download"
            try:
                response = requests.get(url, headers=headers, timeout=30)
                if response.status_code != 200:
                    print(f"图片下载失败 {file_token}: HTTP {response.status_code}")
                    continue

                ext = self._guess_image_ext(response.content)
                local_path = output_dir / f"{file_token}{ext}"
                local_path.write_bytes(response.content)
                downloaded[file_token] = local_path

            except Exception as e:
                print(f"图片下载失败 {file_token}: {e}")

        return downloaded

    def _guess_image_ext(self, content: bytes) -> str:
        """根据文件头猜测图片扩展名"""
        if content.startswith(b'\x89PNG'):
            return '.png'
        elif content.startswith(b'\xff\xd8'):
            return '.jpg'
        elif content.startswith(b'GIF89a') or content.startswith(b'GIF87a'):
            return '.gif'
        elif content.startswith(b'WEBP', 8):
            return '.webp'
        return '.png'  # 默认

    def insert_blocks(self, document_id: str, parent_block_id: str,
                      blocks: List[Dict], index: int = -1) -> Dict:
        """
        在 parent_block_id 下插入子块
        index=-1 表示追加到末尾
        """
        result = self._request(
            "POST",
            f"/open-apis/docx/v1/documents/{document_id}/blocks/{parent_block_id}/children",
            json={"children": blocks, "index": index}
        )
        return result.get("data", {})

    def delete_blocks(self, document_id: str, parent_block_id: str,
                      start_index: int, end_index: int) -> Dict:
        """
        批量删除 parent_block_id 的子块（按index范围，左闭右开）
        使用 DELETE + JSON body
        """
        self._ensure_token()
        url = (f"{self.base_url}/open-apis/docx/v1/documents/{document_id}"
               f"/blocks/{parent_block_id}/children/batch_delete")
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        body = {
            "start_index": start_index,
            "end_index": end_index,
            "document_revision_id": -1,
        }
        resp = requests.delete(url, headers=headers, json=body)
        result = resp.json()
        if result.get("code") != 0:
            raise FeishuAPIError(f"delete_blocks 失败: {result}")
        return result.get("data", {})

    def get_sheet_content(self, file_token: str) -> Dict:
        """
        获取嵌入电子表格的内容
        file_token: 文档中sheet块的file_token
        返回第一个工作表的数据（作为二维数组）
        """
        try:
            # 直接使用file_token作为spreadsheet_token尝试访问
            # 获取spreadsheet的sheets列表
            result = self._request(
                "GET",
                f"/open-apis/sheets/v2/spreadsheets/{file_token}/metainfo"
            )

            # 获取第一个sheet的range数据
            # 假设数据在第一个sheet，使用A1:Z100范围
            result = self._request(
                "GET",
                f"/open-apis/sheets/v2/spreadsheets/{file_token}/values_batch_get",
                params={
                    "ranges": "!A1:Z100",  # 获取前100行，最多26列
                    "valueRenderOption": "ToString",
                    "dateTimeRenderOption": "FormattedString"
                }
            )

            value_ranges = result.get("data", {}).get("valueRanges", [])
            if value_ranges:
                values = value_ranges[0].get("values", [])
                return {"rows": values}

        except Exception as e:
            print(f"获取电子表格内容失败: {e}")

        return {"rows": []}

    def upload_file(self, file_path: Path, document_id: str) -> Dict:
        """
        上传文件为文档附件
        返回: {"file_token": "...", "name": "..."}
        """
        self._ensure_token()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        file_size = file_path.stat().st_size

        with open(file_path, 'rb') as f:
            files = {
                'file_name': (None, file_path.name),
                'parent_type': (None, 'docx_file'),
                'parent_node': (None, document_id),
                'size': (None, str(file_size)),
                'file': (file_path.name, f, 'application/octet-stream'),
            }
            url = f"{self.base_url}/open-apis/drive/v1/medias/upload_all"
            response = requests.post(url, headers=headers, files=files)
            result = response.json()

            if result.get("code") != 0:
                raise FeishuAPIError(f"上传文件失败: {result}")

            file_info = result.get("data", {})
            return {
                "file_token": file_info.get("file_token"),
                "name": file_path.name,
            }

def main():
    """CLI工具入口"""
    import argparse

    parser = argparse.ArgumentParser(description="飞书文档API工具")
    parser.add_argument("--app-id", required=True, help="飞书应用ID")
    parser.add_argument("--app-secret", required=True, help="飞书应用密钥")
    parser.add_argument("command", choices=["download", "upload", "info"], help="操作命令")
    parser.add_argument("--url", help="飞书文档URL")
    parser.add_argument("--document-id", help="文档ID")
    parser.add_argument("--output", type=Path, help="输出目录")

    args = parser.parse_args()

    api = FeishuAPI(args.app_id, args.app_secret)

    if args.command == "info":
        if args.url:
            doc_type, token = api.parse_document_url(args.url)
            print(f"文档类型: {doc_type}")
            print(f"Token: {token}")

            if doc_type == "wiki":
                docx_id = api.get_docx_from_wiki(token)
                print(f"Docx ID: {docx_id}")
            else:
                docx_id = token

        elif args.document_id:
            docx_id = args.document_id
        else:
            print("需要提供 --url 或 --document-id")
            return

        info = api.get_document_info(docx_id)
        print(f"标题: {info['title']}")
        print(f"文档ID: {info['document_id']}")
        print(f"修订ID: {info['revision_id']}")

if __name__ == "__main__":
    main()
