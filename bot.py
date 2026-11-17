import requests, re, json, os

LINE_CHANNEL_TOKEN = os.environ.get("LINE_CHANNEL_TOKEN", "")
LINE_TO = os.environ.get("LINE_TO", "")

HEADERS = {"User-Agent": "Mozilla/5.0"}
SEEN_FILE = "seen_ids.json"

KOREAN_PATTERN = re.compile(r"韓版\s*\d{1,2}/\d{1,2}\s*NEW!?")
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
    print("=== 檢查 台版官網 (用真瀏覽器 + 抓連結) ===")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("沒有 playwright")
        return 0
    links = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36")
        try:
            page.goto("https://lineagem.beanfun.com/News", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)
            # 直接拿所有 <a> 的文字 + 連結，這樣才拿得到正確的文章連結
            links = page.evaluate("""() => {
                return Array.from(document.querySelectorAll('a')).map(a => ({
                    text: (a.innerText || '').trim(),
                    href: a.href
                })).filter(x => x.text.length > 0);
            }""")
            print(f"瀏覽器抓到 {len(links)} 個連結")
            for l in links[:20]:
                print(f"連結: {l['text'][:40]} -> {l['href']}")
        except Exception as e:
            print(f"瀏覽器失敗: {e}")
        finally:
            browser.close()
    count = 0
    for item in links:
        title = item["text"]
        href = item["href"]
        if not TW_PATTERN.search(title):
            continue
        # 用連結當 key，才不會重複推同一個連結
        # href 可能是 https://lineagem.beanfun.com/News?bid=xxxx 或 /News/xxxx
        key = f"tw-{href}"
        # 也兼容舊的 title key
        key2 = f"tw-{title}"
        if key in seen or key2 in seen:
            print(f"已推過，跳過: {title}")
            continue
        seen.add(key)
        seen.add(key2)
        # 如果 href 還是首頁 /News，就不要用首頁，改用 News 列表頁 + 標題提示
        if href.rstrip("/").endswith("/News") or href.rstrip("/").endswith("/News?tab=0"):
            print(f"警告：{title} 的連結還是首頁，改用列表頁")
            link = "https://lineagem.beanfun.com/News"
        else:
            link = href
        push_line(f"台版官網\n{title}\n{link}")
        count += 1
        print("台版推播:", title, "->", link)
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