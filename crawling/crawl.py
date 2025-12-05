#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号一键增量爬取脚本
运行即可自动爬取所有未获取的文章内容
无需任何参数
"""

import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from wechat_crawler import WeChatCrawler


def main():
    """主函数 - 一键增量爬取"""
    print("🚀 微信公众号一键增量爬取")
    print("=" * 50)

    # 创建爬虫实例
    crawler = None
    try:
        crawler = WeChatCrawler()

        # 获取所有配置的公众号
        accounts = crawler.get_accounts_list()
        print(f"📋 配置的公众号数量: {len(accounts)}")
        print(f"账号: {', '.join(accounts)}")
        print()

        total_success = 0
        total_crawled = 0

        # 对每个公众号进行增量爬取
        for account_name in accounts:
            print(f"📖 处理公众号: {account_name}")
            print("-" * 30)

            try:
                # 执行增量爬取
                results = crawler.incremental_crawl(account_name)
                success_count = sum(1 for r in results if r["crawl_success"])
                total_count = len(results)

                if total_count == 0:
                    print("✅ 所有文章都已爬取完成")
                else:
                    print(f"✅ 本次爬取: {success_count}/{total_count} 篇成功")
                    total_success += success_count
                    total_crawled += total_count

                print()

            except Exception as e:
                print(f"❌ 处理公众号 '{account_name}' 时出错: {e}")
                print()

        # 总结
        print("=" * 50)
        if total_crawled == 0:
            print("🎉 所有公众号的文章都已爬取完成！")
        else:
            print(f"🎉 增量爬取完成！")
            print(f"📊 本次总计爬取: {total_success}/{total_crawled} 篇文章")
            print("📁 数据已保存到: /Users/xiyuanyang/Desktop/Dev/IntelliSearch/articles/")

        return True

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
        return False
    except Exception as e:
        print(f"\n❌ 执行过程中出现错误: {e}")
        return False
    finally:
        if crawler:
            crawler.close()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)