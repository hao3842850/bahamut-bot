import requests, re, json, os

LINE_CHANNEL_TOKEN = os.environ.get("LINE_CHANNEL_TOKEN", "")
LINE_TO = os.environ.get("LINE_TO", "")

HEADERS = {"User-Agent": "Mozilla/5.0"}
SEEN_FILE = "seen_ids.json"

KOREAN_PATTERN = re.compile(r"韓版\s*\d{1,2}/\d{1,2}\s*NEW!?")
# 台版：【xx/xx 活動總覽】 和 【xx/xx 更新與活動總覽】 都抓
TW_PATTERN = re.compile(r"【\s*\d{1,2}/\d{1,2}\s*(更新與)?活動總覽】")

def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f, ensure_ascii=False)

def push_line(text):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_TOKEN}", "Content-Type": "application/json"}
    body = {"to": LINE_TO, "messages": [{"type": "text", "text": text}]}
    r = requests.post(url, headers=headers, json=body, timeout=10)
    print("LINE 推播:", r.status_code, r.text[:200])
    return r.status_code == 200

def check_bahamut(seen):
    print("=== 檢查 巴哈韓版 ===")
    url = "https://forum.gamer.com.tw/B.php?page=1&bsn=25908"
    r = requests.get(url, headers=HEADERS, timeout=15)
    items = re.findall(r'C\.php\?bsn=25908&snA=(\d+)[^>]*>([^<]+)</a>', r.text)
    print(f"巴哈抓到 {len(items)} 篇")
    count = 0
    for snA, title in items:
        title = title.strip()
        key = f"bahamut-{snA}"
        if key in seen:
            continue
        seen.add(key)
        if KOREAN_PATTERN.search(title):
            link = f"https://forum.gamer.com.tw/C.php?bsn=25908&snA={snA}"
            push_line(f"韓版 NEW!\n{title}\n{link}")
            count += 1
    print(f"巴哈推播 {count} 篇")
    return count

def check_taiwan_official(seen):
    print("=== 檢查 台版官網 (用真瀏覽器) ===")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("沒有 playwright，跳過台版")
        return 0
    all_text = ""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36")
        try:
            page.goto("https://lineagem.beanfun.com/News", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)
            all_text = page.content()
            print(f"瀏覽器抓到長度 {len(all_text)}")
            # 也試著抓內文
            body_text = page.inner_text("body")
            all_text += "\n" + body_text
            print(f"內文長度 {len(body_text)}，前 1000 字: {body_text[:1000].replace(chr(10),' | ')}")
        except Exception as e:
            print(f"瀏覽器抓取失敗: {e}")
        finally:
            browser.close()
    # 從渲染後的內容找
    titles = re.findall(r"【\s*\d{1,2}/\d{1,2}\s*(?:更新與)?活動總覽】", all_text)
    print(f"台版找到 {len(titles)} 個活動總覽: {titles}")
    # 也找 bid
    items = re.findall(r'News\?bid=(\d+)[^>]*>([^<]+)</a>', all_text)
    print(f"台版 bid 抓到 {len(items)} 篇")
    count = 0
    # 用 bid 優先
    for bid, title in items:
        title = title.strip()
        if TW_PATTERN.search(title):
            key = f"tw-{bid}"
            if key in seen:
                continue
            seen.add(key)
            link = f"https://lineagem.beanfun.com/News?bid={bid}"
            push_line(f"台版官網\n{title}\n{link}")
            count += 1
            print("台版推播:", title)
        else:
            key = f"tw-{bid}"
            if key not in seen:
                seen.add(key)
    # 如果 bid 沒抓到，用標題當備用
    if not items:
        for title in set(titles):
            title = title.strip()
            key = f"tw-{title}"
            if key in seen:
                continue
            seen.add(key)
            push_line(f"台版官網\n{title}\nhttps://lineagem.beanfun.com/News")
            count += 1
            print("台版備用推播:", title)
    print(f"台版推播 {count} 篇")
    return count

def main():
    if not LINE_CHANNEL_TOKEN or not LINE_TO:
        print("錯誤：沒有設定 Secrets")
        return
    seen = load_seen()
    total = 0
    total += check_bahamut(seen)
    total += check_taiwan_official(seen)
    save_seen(seen)
    print(f"全部完成，總推播 {total} 篇")

if __name__ == "__main__":
    main()