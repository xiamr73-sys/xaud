# -*- coding: utf-8 -*-
import asyncio
import os
import ccxt.async_support as ccxt
from dotenv import load_dotenv

async def test_connection():
    # 1. 加载环境变量
    load_dotenv()
    api_key = os.getenv("BINANCE_API_KEY")
    secret = os.getenv("BINANCE_SECRET")

    print(f"[-] 正在检查 API Key 配置...")
    if not api_key:
        print("[!] 错误: 未找到 BINANCE_API_KEY")
        return
    if not secret:
        print("[!] 错误: 未找到 BINANCE_SECRET")
        return

    # 打印 Key 信息（仅用于调试，注意打码）
    print(f"[-] API Key 长度: {len(api_key)}")
    print(f"[-] API Key 前缀: {api_key[:4]}...")
    print(f"[-] API Key 后缀: ...{api_key[-4:]}")
    print(f"[-] Secret 长度: {len(secret)}")

    # 2. 初始化交易所 (Futures Mainnet)
    print("\n[-] [尝试 1] 连接 Binance Futures 主网 (Mainnet)...")
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': secret,
        'timeout': 30000,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future', 
        }
    })

    try:
        # 测试公共端点
        server_time = await exchange.fetch_time()
        print(f"[+] 主网公共端点连接成功! 服务器时间: {server_time}")

        # 测试私有端点 (余额)
        print("[-] 正在测试主网私有端点 (fetch_balance)...")
        balance = await exchange.fetch_balance()
        print("[+] 主网私有端点验证成功! 这是一个主网 Key。")
        await exchange.close()
        return

    except ccxt.AuthenticationError as e:
        print(f"[!] 主网认证失败: {e}")
        print("    -> 正在尝试切换到测试网 (Testnet) 进行验证...")
    except Exception as e:
        print(f"[!] 主网连接发生其他错误: {e}")
    finally:
        await exchange.close()

    # 3. 如果主网失败，尝试测试网 (Testnet) - 手动指定 URL
    print("\n[-] [尝试 2] 连接 Binance Futures 测试网 (Testnet)...")
    exchange_test = ccxt.binance({
        'apiKey': api_key,
        'secret': secret,
        'timeout': 30000,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future', 
        },
        'urls': {
            'api': {
                'fapiPublic': 'https://testnet.binancefuture.com/fapi/v1',
                'fapiPrivate': 'https://testnet.binancefuture.com/fapi/v1',
            },
        }
    })
    
    # 去掉 set_sandbox_mode，防止触发 ccxt 的弃用报错
    # exchange_test.set_sandbox_mode(True) 

    try:
        # 测试公共端点
        print("[-] 正在测试测试网公共端点 (fetch_time)...")
        # 直接调用 raw request 避免 ccxt 内部 URL 构造逻辑的干扰
        # 但为了方便，先试标准方法，如果报错再改
        try:
            server_time = await exchange_test.fetch_time()
            print(f"[+] 测试网公共端点连接成功! 服务器时间: {server_time}")
        except Exception as e:
            print(f"[-] fetch_time 失败 ({e})，尝试继续...")

        # 测试私有端点
        print("[-] 正在测试测试网私有端点 (fetch_balance)...")
        # 注意：Testnet 的 balance 可能为空，但只要不报 AuthenticationError 就算成功
        balance = await exchange_test.fetch_balance()
        print("[+] 测试网私有端点验证成功! \n[***] 这是一个测试网 Key! 请在代码中配置测试网环境。")

    except ccxt.AuthenticationError as e:
        print(f"[!] 测试网认证也失败: {e}")
        print("    -> 结论: 该 Key 在主网和测试网均无效，或者已被删除/禁用。")
    except Exception as e:
        print(f"[!] 测试网连接发生其他错误: {e}")
    finally:
        await exchange_test.close()
        print("\n[-] 所有测试结束。")

if __name__ == "__main__":
    asyncio.run(test_connection())
