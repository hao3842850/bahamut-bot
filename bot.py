import requests, re, json, os

LINE_CHANNEL_TOKEN = os.environ.get("LINE_CHANNEL_TOKEN", "")
LINE_TO = os.environ.get("LINE_TO", "")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9",
    "Referer": "https://lineagem.beanfun.com/",
}
SEEN_FILE = "seen_ids.json"

# 韓版維持
KOREAN_PATTERN = re.compile(r"韓版\s*\d{1,2}/\d{1,2}\s*NEW!?")
# 台版：兩種都抓 【xx/xx 活動總覽】 和 【xx/xx 更新與活動總覽】
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
    print("=== 檢查 台版官網 ===")
    # 試多個網址，官網是 JS，試著用不同方式抓
    urls = [
        "https://lineagem.beanfun.com/News",
        "https://lineagem.beanfun.com/News?tab=0",
        "https://lineagem.beanfun.com/Main",
    ]
    all_text = ""
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            print(f"抓 {url} -> {r.status_code}, 長度 {len(r.text)}")
            all_text += r.text + "\n"
        except Exception as e:
            print(f"抓 {url} 失敗: {e}")
    # 1. 先抓 bid + 標題
    items = re.findall(r'News\?bid=(\d+)[^>]*>([^<]+)</a>', all_text)
    print(f"官網 bid 模式抓到 {len(items)} 篇")
    # 2. 直接從全文找活動總覽
    titles = TW_PATTERN.findall(all_text)
    print(f"官網全文模式抓到 {len(titles)} 個活動總覽 pattern")
    # 用 bid 方式
    count = 0
    found_titles = set()
    for bid, title in items:
        title = title.strip()
        if TW_PATTERN.search(title):
            found_titles.add(title)
            key = f"tw-{bid}"
            if key in seen:
                continue
            seen.add(key)
            link = f"https://lineagem.beanfun.com/News?bid={bid}"
            push_line(f"台版官網\n{title}\n{link}")
            count += 1
            print("台版推播:", title)
        else:
            # 還是要記住 bid，避免下次重複檢查
            key = f"tw-{bid}"
            if key not in seen:
                seen.add(key)
    # 如果 bid 抓不到，用全文標題當備用
    if not items:
        raw_titles = re.findall(r"【\s*\d{1,2}/\d{1,2}\s*(?:更新與)?活動總覽】", all_text)
        for title in raw_titles:
            title = title.strip()
            key = f"tw-{title}"
            if key in seen:
                continue
            seen.add(key)
            push_line(f"台版官網\n{title}\nhttps://lineagem.beanfun.com/News")
            count += 1
            print("台版備用推播:", title)
    print(f"台版推播 {count} 篇")
    # Debug: 印出前 500 字看看官網回什麼，方便下次除錯
    print("DEBUG 官網回應開頭:", all_text[:500].replace("\n", " ")[:500])
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
