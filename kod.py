import tkinter as tk
from tkinter import messagebox, ttk
import pandas as pd
import requests
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import Counter
import json
import os
from bs4 import BeautifulSoup  # HTML temizleme için eklendi

# --- Ayarlar ---
API_KEY = '2883D4425F5039AD3C9A9439629C3412'
INPUT_CSV = 'games.csv'
CHUNK_SIZE = 10000
CACHE_FILE = 'game_cache.json'
FEEDBACK_FILE = 'feedback.csv'
current_user= None
IGNORE = set([
    'the','and','or','of','a','an','with','for','on','at','in','to','by',
    'this','that','from','your','you','are','as','has','be','will','not',
    'it','can','is','was','have','more','all','new','but','now','they',
    'game','games','store','steam','https','img','com','jpg','png',
    'singleplayer','multiplayer'
])

# --- Cache Fonksiyonları ---
def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump({}, f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=4)

# --- Yardımcı Fonksiyonlar ---
def son_oynanan_oyuna_oneri(steam_id, cache):
    url = f"https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v1/?key={API_KEY}&steamid={steam_id}"
    try:
        r = requests.get(url, timeout=5)
        print(f"API Yanıtı Durum Kodu: {r.status_code}")  # Yanıt kodu
        print(f"API Yanıtı: {r.json()}")  # API yanıtını tam olarak yazdıralım
        if r.status_code != 200:
            return []

        data = r.json()
        if data.get("response") and "games" in data["response"]:
            games = data["response"]["games"]
            app_ids = [game["appid"] for game in games]
            return app_ids
        else:
            print("Son oynanan oyunlar bulunamadı.")
            return []
    except Exception as e:
        print(f"API hatası: {e}")
        return []


def oyun_ismini_al(appid):
    try:
        df = pd.read_csv(
            INPUT_CSV, usecols=['AppID','Name'], dtype={'AppID': str}, encoding='ISO-8859-1'
        )
        match = df[df['AppID']==str(appid)]
        if not match.empty:
            return match.iloc[0]['Name']
    except:
        pass
    return None

def clean_html(raw_html):
    return BeautifulSoup(raw_html, "html.parser").get_text()

def bilgi_cek(app_id, cache):
    if str(app_id) in cache:
        return cache[str(app_id)]
    url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&key={API_KEY}"
    try:
        r = requests.get(url, timeout=5)
        data = r.json().get(str(app_id), {}).get('data', {})
        about = data.get('about_the_game','')
        clean_about = clean_html(about)
        if clean_about:
            cache[str(app_id)] = clean_about
            save_cache(cache)
        return clean_about
    except:
        return ''

def anahtar_kelime_cikti(text, exclude_name='', top_n=5):
    words = re.findall(r"\b\w+\b", text.lower())
    name_words = set(re.findall(r"\b[a-zA-Z]+\b", exclude_name.lower()))
    filtered = [w for w in words if w.isalpha() and w not in IGNORE and len(w)>2 and w not in name_words]
    counts = Counter(filtered)
    return [w for w,_ in counts.most_common(top_n)]

# --- Feedback Fonksiyonları ---
def write_feedback(user_id, app_id, liked):
    feedback_data = []
    if os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            header = lines[0].strip()
            for line in lines[1:]:
                uid, aid, lkd = line.strip().split(',')
                feedback_data.append((uid, aid, lkd))

    updated = False
    for i, (uid, aid, lkd) in enumerate(feedback_data):
        if uid == str(user_id) and aid == str(app_id):
            feedback_data[i] = (uid, aid, str(liked))
            updated = True
            break

    if not updated:
        feedback_data.append((str(user_id), str(app_id), str(liked)))

    with open(FEEDBACK_FILE, 'w', encoding='utf-8') as f:
        f.write('user_id,app_id,liked\n')
        for uid, aid, lkd in feedback_data:
            f.write(f"{uid},{aid},{lkd}\n")

def load_user_feedback(user_id):
    liked_ids, disliked_ids = set(), set()
    if os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, 'r', encoding='utf-8') as f:
            next(f)
            for line in f:
                uid, aid, lkd = line.strip().split(',')
                if uid == str(user_id):
                    if lkd.lower() == 'true':
                        liked_ids.add(aid)
                    else:
                        disliked_ids.add(aid)
    return liked_ids, disliked_ids

# --- Öneri Mantığı ---
#--- SteamDB'den Fiyat Çekme Fonksiyonu ---

def oyun_fiyatlarını_alma_steamDB(app_id):
    url = f"https://steamdb.info/app/{app_id}/"
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Türkiye fiyatını almak için ilgili HTML elemanını bulmak için yazdık burayı
        price_div = soup.find('div', class_='game-price')
        if price_div:
            price_span = price_div.find('span', class_='price')
            if price_span:
                price = price_span.text.strip()
                return price
    except Exception as e:
        print(f"Fiyat çekme hatası: {e}")
    return None


# --- Fiyat Performans Önerisi Fonksiyonu ---
def onerilen_fiyat_performans_mantigi(games):
    # Kullanıcıya oyunlar listesi üzerinden fiyat-performans önerisi yapacağız
    best_game = None
    best_value = float('-inf')  # En yüksek değerli oyunu bulmak için başlatıyoruz
    for game in games:
        app_id, name, score = game  # Önerilen oyun bilgileri
        price = oyun_fiyatlarını_alma_steamDB(app_id)

        if price:
            # Burada, fiyat-performans hesaplaması yapılabilir. Örneğin:
            # Skor / Fiyat = Değer oranı
            try:
                # Fiyatı "₺" işareti ile aldıysak, fiyatı sayıya çevirelim
                price_value = float(price.replace('₺', '').replace(',', '.').strip())
                value = score / price_value  # Fiyat-performans hesaplama
                if value > best_value:
                    best_value = value
                    best_game = (name, app_id, score, price)
            except ValueError:
                continue
    return best_game
## --- Cache ve API’den açıklama çeken yardımcı ---
cache = load_cache()

def get_about_text(app_id):
    key = str(app_id)
    # 1) Cache’de varsa direkt dön
    if key in cache:
        return cache[key]
    # 2) Yoksa Steam API’den çek, temizle, cache’e kaydet
    url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&key={API_KEY}"
    try:
        r = requests.get(url, timeout=5)
        data = r.json().get(key, {}).get('data', {})
        raw = data.get('about_the_game', '') or ''
        clean = BeautifulSoup(raw, "html.parser").get_text()
        if clean:
            cache[key] = clean
            save_cache(cache)
        return clean
    except Exception:
        return ''
# --- Oyun Öneri Sistemi ---
from concurrent.futures import ThreadPoolExecutor, as_completed

def onerilen_oyun_mantigi(game_name, user_id=None):
    sel = game_name.lower().strip()
    cache = load_cache()

    # --- 1) CSV'yi oku ve temizle ---
    df = pd.read_csv(
        INPUT_CSV,
        usecols=['AppID','Name','Genres','Tags','Screenshots'],
        dtype={'AppID':str}, encoding='ISO-8859-1'
    ).dropna(subset=['Name'])
    df['Name'] = df['Name'].astype(str)
    df['nm']   = df['Name'].str.lower().str.strip()

    sel_rows = df[df['nm'] == sel]
    if sel_rows.empty:
        return []
    sel_row    = sel_rows.iloc[0]
    sel_app_id = sel_row['AppID']
    sel_text   = f"{sel_row['Genres']} {sel_row['Tags']} {sel_row['Screenshots']}"

    # --- 2) TF-IDF ile benzerlik ---
    others     = df[df['AppID'] != sel_app_id]
    all_ids    = others['AppID'].tolist()
    all_names  = others['Name'].tolist()
    all_texts  = (others['Genres'].astype(str) + " " +
                  others['Tags'].astype(str)   + " " +
                  others['Screenshots'].astype(str)).tolist()

    vec        = TfidfVectorizer(stop_words='english')
    tfidf      = vec.fit_transform(all_texts)
    user_vec   = vec.transform([sel_text])
    sims       = cosine_similarity(user_vec, tfidf).flatten()

    ranked = sorted(zip(all_ids, all_names, sims),
                    key=lambda x: x[2], reverse=True)
    candidates = [
        (aid, name, score)
        for aid, name, score in ranked
        if isinstance(name, str) and 'dlc' not in name.lower()
    ][:10]

    # --- 3) Geri bildirimleri al ---
    liked_ids, disliked_ids = load_user_feedback(user_id) if user_id else (set(), set())

    # --- 4) ThreadPool ile about metinlerini çek ---
    abouts = {}
    with ThreadPoolExecutor(max_workers=10) as exe:
        future_to_aid = {exe.submit(get_about_text, aid): aid for aid,, in candidates}
        for fut in as_completed(future_to_aid):
            aid = future_to_aid[fut]
            abouts[aid] = fut.result()

    # --- 5) Seçilen oyun için de ---
    sel_about = get_about_text(sel_app_id)

    # --- 6) ThreadPool ile anahtar kelime çıkarımı ---
    sel_kw = anahtar_kelime_cikti(sel_about, sel_row['Name'])
    kw_map = {}
    with ThreadPoolExecutor(max_workers=20) as exe:
        future_to_pair = {
            exe.submit(anahtar_kelime_cikti, abouts[aid], name): (aid, name)
            for aid, name, _ in candidates
        }
        for fut in as_completed(future_to_pair):
            aid, name = future_to_pair[fut]
            kw_map[aid] = fut.result()

    # --- 7) Sonuçları hesapla ---
    results = []
    for aid, name, sim in candidates:
        kw     = kw_map.get(aid, [])
        ratio  = len(set(sel_kw) & set(kw)) / len(sel_kw) if sel_kw else 0
        boost  = 0.1 if aid in liked_ids else -0.2 if aid in disliked_ids else 0
        score  = 0.7 * sim + 0.3 * ratio + boost
        results.append((name, aid, score))

    # --- 8) Fiyat-performans önerisi (opsiyonel) ---
    best = onerilen_fiyat_performans_mantigi(results)
    if best:
        nm, aid, sc, pr = best
        results.append((f"Fiyat Performans: {nm}", aid, sc))

    # --- 9) Sırala ve dön ---
    results.sort(key=lambda x: x[2], reverse=True)
    return results[:3]


def steam_isimleri_cevir(vanity):
    url = f"https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/?key={API_KEY}&vanityurl={vanity}"
    try:
        r = requests.get(url, timeout=5)
        data = r.json()
        if data.get("response", {}).get("success") == 1:
            return data["response"]["steamid"]
    except Exception as e:
        print(f"Vanity URL çözümleme hatası: {e}")
    return None

# --- GUI ---
root = tk.Tk()
root.title("🎮 Steam Oyun Öneri")
root.geometry("600x550")
frm = ttk.Frame(root, padding=10)
frm.pack(fill='x')

# Kontroller
ttk.Label(frm, text="Oyun İsmi:").grid(row=0, column=0, sticky='w')
entry = ttk.Entry(frm, width=30)
entry.grid(row=0,column=1,padx=5)
btn_manual = ttk.Button(frm, text="Önerileri Göster")
btn_manual.grid(row=0,column=2)

ttk.Label(frm, text="Steam ID:").grid(row=1,column=0,sticky='w', pady=5)
steam_entry = ttk.Entry(frm, width=30)
steam_entry.grid(row=1,column=1,padx=5)
btn_steam = ttk.Button(frm, text="Sonraki Oyununuz Ne?")
btn_steam.grid(row=1,column=2)

results_frame = ttk.Frame(root, padding=10)
results_frame.pack(fill='both', expand=True)
output_text = tk.Text(root, height=10, wrap='word')
output_text.pack(fill='both', expand=True)

def clear_results():
    for w in results_frame.winfo_children(): w.destroy()
    output_text.delete(1.0, tk.END)

def on_feedback(app_id, liked):
    user_id = current_user
    if user_id:
        write_feedback(user_id, app_id, liked)
        messagebox.showinfo('Teşekkürler', f'Geri bildiriminiz kaydedildi: {app_id} -> {liked}')
def onerileri_goster(results):
    clear_results()
    for i, (name, aid, score) in enumerate(results):
        lbl = ttk.Label(results_frame, text=f"{name} — AppID: {aid} | Skor: {score:.4f}")
        lbl.grid(row=i, column=0, sticky='w', pady=5)
        btn_like = ttk.Button(results_frame, text="Beğendim", command=lambda a=aid: on_feedback(a, True))
        btn_like.grid(row=i, column=1, padx=5)
        btn_dislike = ttk.Button(results_frame, text="Beğenmedim", command=lambda a=aid: on_feedback(a, False))
        btn_dislike.grid(row=i, column=2, padx=5)

def Onerileri_goster_basıldıgında_oneri(game_name):
    results = onerilen_oyun_mantigi(game_name, current_user)
    root.after(0, lambda: [output_text.delete(1.0, tk.END), [output_text.insert(tk.END, f"{n} — AppID: {a} | Skor: {s:.4f}\n") for n,a,s in results]])

def Sonraki_Oyun_basildiginda_oneri(steam_id):
    steam_id_input = steam_entry.get().strip()
    if not steam_id_input.isdigit():
        resolved_id = steam_isimleri_cevir(steam_id_input)
        if not resolved_id:
            root.after(0,
                       lambda: messagebox.showwarning('Uyarı', 'Vanity URL çözümlenemedi. Geçerli bir Steam ID girin.'))
            return
        steam_id = resolved_id
    else:
        steam_id = steam_id_input

    global current_user
    current_user = steam_entry.get().strip() or "anonymous"
    if not steam_id.strip():
        root.after(0, lambda: messagebox.showwarning('Uyarı','Lütfen Steam ID girin.'))
        return

    # Cache'i yükle
    cache = load_cache()

    # Steam ID'yi kullanarak son oynanan oyunları al
    app_ids = son_oynanan_oyuna_oneri(steam_id, cache)  # Burada cache parametresini geçiyoruz
    if not app_ids:
        root.after(0, lambda: messagebox.showwarning('Uyarı','Son oynanan oyun bulunamadı veya Steam ID geçersiz.'))
        return

    # Oyunları ve isimlerini al
    for appid in app_ids:
        name = oyun_ismini_al(appid)
        if name:
            results = onerilen_oyun_mantigi(name, current_user)
            root.after(0, lambda r=results: onerileri_goster(r))
            return

    root.after(0, lambda: messagebox.showinfo('Bilgi','Geçerli oyun ismi bulunamadı.'))

btn_manual.config(command=lambda: threading.Thread(target=lambda: [clear_results(), Onerileri_goster_basıldıgında_oneri(entry.get())]).start())
btn_steam.config(command=lambda: threading.Thread(target=lambda: Sonraki_Oyun_basildiginda_oneri(steam_entry.get())).start())

root.mainloop()