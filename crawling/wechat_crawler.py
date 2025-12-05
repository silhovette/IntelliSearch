#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号统一爬虫 - 整合版
一键获取公众号内容链接和文章内容
"""

import json
import logging
import os
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
from urllib3.exceptions import InsecureRequestWarning

# Selenium相关
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# BeautifulSoup
from bs4 import BeautifulSoup

# 禁用SSL警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class WeChatCrawler:
    """微信公众号统一爬虫类"""

    def __init__(self, config_file: str = "crawling/wechat_config.json"):
        """初始化爬虫"""
        self.config_file = config_file
        self.config = self._load_config()
        self.session = self._setup_session()
        self.driver = None

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            "accounts": {
                "SAI青年号": {
                    "fakeid": "Mzk0Nzc0NTY1Mg==",
                    "description": "SAI青年公众号"
                },
                "上海交通大学人工智能学院": {
                    "fakeid": "MzkwNTY3MjU0Nw==",
                    "description": "上海交通大学人工智能学院公众号"
                }
            },
            "auth": {
                "cookie": "None",
                "token": "None"
            },
            "settings": {
                "base_dir": "/Users/xiyuanyang/Desktop/Dev/IntelliSearch/articles",
                "headless": True,
                "wait_time": 10,
                "request_delay": 3,
                "max_retries": 3
            }
        }

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并配置，保留默认值
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                        elif isinstance(value, dict):
                            for sub_key, sub_value in value.items():
                                if sub_key not in config[key]:
                                    config[key][sub_key] = sub_value
                    return config
            except Exception as e:
                logger.warning(f"配置文件加载失败: {e}，使用默认配置")
        else:
            # 创建默认配置文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            logger.info(f"创建默认配置文件: {self.config_file}")

        return default_config

    def _setup_session(self) -> requests.Session:
        """设置网络会话"""
        session = requests.Session()
        session.verify = False
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "X-Requested-With": "XMLHttpRequest",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        })
        return session

    def _setup_driver(self):
        """设置Chrome浏览器驱动"""
        if self.driver:
            return

        try:
            options = Options()

            settings = self.config["settings"]
            if settings.get("headless", True):
                options.add_argument("--headless")

            # 基本设置
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-web-security")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument(
                "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
            )

            # 排除自动化标识
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)

            # 初始化驱动
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
            except Exception:
                # 使用系统chromedriver
                self.driver = webdriver.Chrome(options=options)

            self.driver.set_window_size(1920, 1080)
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            logger.info("Chrome浏览器驱动初始化成功")

        except Exception as e:
            logger.error(f"浏览器驱动初始化失败: {e}")
            raise RuntimeError(f"无法初始化Chrome浏览器驱动: {e}")

    def get_article_list(self, account_name: str, begin: int = 0, count: int = 10) -> Optional[Dict]:
        """获取公众号文章列表"""
        fakeid = self.config["accounts"].get(account_name, {}).get("fakeid")
        auth = self.config["auth"]

        if not fakeid:
            logger.error(f"未找到账号 {account_name} 的fakeid")
            return None

        url = "https://mp.weixin.qq.com/cgi-bin/appmsgpublish"
        params = {
            "sub": "list",
            "search_field": "null",
            "begin": str(begin),
            "count": str(count),
            "query": "",
            "fakeid": fakeid,
            "type": "101_1",
            "free_publish_type": "1",
            "sub_action": "list_ex",
            "token": auth["token"],
            "lang": "zh_CN",
            "f": "json",
            "ajax": "1",
        }

        headers = {
            "Referer": f"https://mp.weixin.qq.com/cgi-bin/appmsgtemplate?action=edit&lang=zh_CN&token={auth['token']}",
            "Cookie": auth["cookie"],
        }

        try:
            response = self.session.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()

            response_text = response.text
            # 处理转义字符
            response_text = response_text.replace("\\\\", "")
            response_text = response_text.replace('\\"', '"')
            response_text = response_text.replace('"{', "{")
            response_text = response_text.replace('}"', "}")

            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                return {"raw_response": response_text}

        except Exception as e:
            logger.error(f"获取文章列表失败: {e}")
            return None

    def extract_articles_from_data(self, data: Dict) -> List[Dict]:
        """从API数据中提取文章信息"""
        articles = []

        if not data or "publish_page" not in data:
            return articles

        publish_list = data.get("publish_page", {}).get("publish_list", [])

        for publish in publish_list:
            if ("publish_info" in publish and
                "appmsg_info" in publish["publish_info"] and
                len(publish["publish_info"]["appmsg_info"]) > 0):

                appmsgex_info = publish["publish_info"]["appmsgex"][0]

                article = {
                    "title": appmsgex_info.get("title", ""),
                    "id": appmsgex_info.get("appmsgid", -1),
                    "link": appmsgex_info.get("link", ""),
                    "update_time": datetime.fromtimestamp(
                        appmsgex_info.get("update_time", 0)
                    ).strftime("%Y-%m-%d %H:%M:%S"),
                    "author": appmsgex_info.get("author_name", ""),
                    "digest": appmsgex_info.get("digest", ""),
                    "cover_url": appmsgex_info.get("cover_url", ""),
                }
                articles.append(article)

        return articles

    def crawl_article_content(self, url: str) -> Optional[Dict]:
        """爬取文章内容"""
        if not self.driver:
            self._setup_driver()

        try:
            logger.info(f"爬取文章: {url}")

            self.driver.get(url)
            wait = WebDriverWait(self.driver, self.config["settings"]["wait_time"])

            # 等待文章标题加载
            wait.until(EC.presence_of_element_located((By.ID, "activity-name")))

            # 滚动页面
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            while True:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            # 提取内容
            article_data = {}

            # 标题
            try:
                title = self.driver.find_element(By.ID, "activity-name").text.strip()
                article_data["title"] = title
            except:
                article_data["title"] = "未知标题"

            # 作者
            try:
                author = self.driver.find_element(By.ID, "js_name").text.strip()
                article_data["author"] = author
            except:
                article_data["author"] = "未知作者"

            # 发布时间
            try:
                publish_time = self.driver.find_element(By.ID, "publish_time").text.strip()
                article_data["publish_time"] = publish_time
            except:
                article_data["publish_time"] = "未知时间"

            # 正文内容
            try:
                content_element = self.driver.find_element(By.ID, "js_content")
                content_html = content_element.get_attribute("innerHTML")

                # 使用BeautifulSoup提取纯文本
                soup = BeautifulSoup(content_html, "html.parser")
                for script in soup(["script", "style"]):
                    script.decompose()
                content_text = soup.get_text(separator="\n", strip=True)

                article_data["content_html"] = content_html
                article_data["content_text"] = content_text
            except:
                article_data["content_html"] = ""
                article_data["content_text"] = ""

            article_data["url"] = self.driver.current_url
            article_data["crawl_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            logger.info(f"成功爬取文章: {article_data['title']}")
            return article_data

        except Exception as e:
            logger.error(f"爬取文章内容失败: {e}")
            return None

    def save_data(self, data: Any, account_name: str, file_path: str) -> bool:
        """保存数据到文件"""
        try:
            base_dir = Path(self.config["settings"]["base_dir"]) / account_name
            base_dir.mkdir(parents=True, exist_ok=True)

            full_path = base_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, "w", encoding="utf-8") as f:
                if isinstance(data, (dict, list)):
                    json.dump(data, f, ensure_ascii=False, indent=2)
                else:
                    f.write(str(data))

            logger.debug(f"数据保存成功: {full_path}")
            return True
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
            return False

    def get_all_articles(self, account_name: str) -> List[Dict]:
        """获取公众号所有文章链接"""
        logger.info(f"获取公众号 {account_name} 的所有文章链接")

        all_articles = []
        begin = 0
        count = 10
        request_count = 0

        while True:
            logger.info(f"获取第 {request_count + 1} 页数据 (begin={begin})")

            data = self.get_article_list(account_name, begin, count)
            if not data:
                logger.error("获取文章列表失败，停止获取")
                break

            # 保存原始数据
            self.save_data(data, account_name, f"json_origin/{begin}.json")

            # 提取文章信息
            articles = self.extract_articles_from_data(data)
            if not articles:
                logger.info("没有更多文章，获取完成")
                break

            all_articles.extend(articles)
            logger.info(f"本页获取到 {len(articles)} 篇文章")
            begin += count
            request_count += 1

            # 请求延时
            time.sleep(self.config["settings"]["request_delay"])

        # 保存完整文章列表
        self.save_data(all_articles, account_name, "all_articles.json")

        logger.info(f"总共获取到 {len(all_articles)} 篇文章链接")
        return all_articles

    def crawl_all_content(self, account_name: str, limit: Optional[int] = None) -> List[Dict]:
        """爬取公众号所有文章内容"""
        # 获取文章链接
        articles = self.get_all_articles(account_name)

        if limit:
            articles = articles[:limit]

        logger.info(f"开始爬取 {len(articles)} 篇文章的内容")
        results = []

        for i, article in enumerate(articles, 1):
            logger.info(f"爬取第 {i}/{len(articles)} 篇: {article['title']}")

            content_data = self.crawl_article_content(article['link'])

            result = {
                "article_info": article,
                "crawl_success": content_data is not None,
                "content_data": content_data
            }

            if content_data:
                # 保存文章内容
                article_id = str(article['id'])
                self.save_data(content_data, account_name, f"article_content/{article_id}/meta_info.json")
                self.save_data(
                    f"标题: {content_data.get('title', '')}\n"
                    f"作者: {content_data.get('author', '')}\n"
                    f"发布时间: {content_data.get('publish_time', '')}\n"
                    f"抓取时间: {content_data.get('crawl_time', '')}\n"
                    f"链接: {content_data.get('url', '')}\n\n"
                    f"{'='*80}\n\n"
                    f"{content_data.get('content_text', '')}",
                    account_name,
                    f"article_content/{article_id}/content.txt"
                )

            results.append(result)

            # 添加延时
            if i < len(articles):
                time.sleep(self.config["settings"]["request_delay"])

        success_count = sum(1 for r in results if r["crawl_success"])
        logger.info(f"内容爬取完成: {success_count}/{len(articles)} 篇成功")

        return results

    def is_article_crawled(self, account_name: str, article_id: str) -> bool:
        """检查文章是否已经被爬取"""
        try:
            article_dir = Path(self.config["settings"]["base_dir"]) / account_name / "article_content" / article_id
            meta_file = article_dir / "meta_info.json"
            content_file = article_dir / "content.txt"

            return meta_file.exists() and content_file.exists()
        except Exception:
            return False

    def get_uncrawled_articles(self, account_name: str) -> List[Dict]:
        """获取未爬取的文章列表"""
        # 获取所有文章
        all_articles = self.get_all_articles(account_name)

        # 过滤出未爬取的文章
        uncrawled = []
        for article in all_articles:
            if not self.is_article_crawled(account_name, str(article['id'])):
                uncrawled.append(article)

        logger.info(f"公众号 '{account_name}' 总共 {len(all_articles)} 篇文章，未爬取 {len(uncrawled)} 篇")
        return uncrawled

    def incremental_crawl(self, account_name: str, limit: Optional[int] = None) -> List[Dict]:
        """增量爬取：只爬取未获取的文章内容"""
        # 获取未爬取的文章
        uncrawled_articles = self.get_uncrawled_articles(account_name)

        if limit:
            uncrawled_articles = uncrawled_articles[:limit]

        if not uncrawled_articles:
            logger.info(f"公众号 '{account_name}' 所有文章都已爬取完成")
            return []

        logger.info(f"开始增量爬取 {len(uncrawled_articles)} 篇未爬取的文章")
        results = []

        for i, article in enumerate(uncrawled_articles, 1):
            logger.info(f"爬取第 {i}/{len(uncrawled_articles)} 篇: {article['title']}")

            content_data = self.crawl_article_content(article['link'])

            result = {
                "article_info": article,
                "crawl_success": content_data is not None,
                "content_data": content_data
            }

            if content_data:
                # 保存文章内容
                article_id = str(article['id'])
                self.save_data(content_data, account_name, f"article_content/{article_id}/meta_info.json")
                self.save_data(
                    f"标题: {content_data.get('title', '')}\n"
                    f"作者: {content_data.get('author', '')}\n"
                    f"发布时间: {content_data.get('publish_time', '')}\n"
                    f"抓取时间: {content_data.get('crawl_time', '')}\n"
                    f"链接: {content_data.get('url', '')}\n\n"
                    f"{'='*80}\n\n"
                    f"{content_data.get('content_text', '')}",
                    account_name,
                    f"article_content/{article_id}/content.txt"
                )

            results.append(result)

            # 添加延时
            if i < len(uncrawled_articles):
                time.sleep(self.config["settings"]["request_delay"])

        success_count = sum(1 for r in results if r["crawl_success"])
        logger.info(f"增量爬取完成: {success_count}/{len(uncrawled_articles)} 篇成功")

        return results

    def get_accounts_list(self) -> List[str]:
        """获取所有配置的公众号列表"""
        return list(self.config["accounts"].keys())

    def close(self):
        """关闭爬虫，清理资源"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("浏览器已关闭")
            except:
                pass

        if self.session:
            try:
                self.session.close()
                logger.info("网络会话已关闭")
            except:
                pass

    def __del__(self):
        """析构函数"""
        self.close()


if __name__ == "__main__":
    # 简单测试
    crawler = WeChatCrawler()

    try:
        print("配置的公众号:")
        for account in crawler.get_accounts_list():
            print(f"- {account}")

        print("\n使用 run_wechat_crawler.py 来进行爬取操作")

    finally:
        crawler.close()