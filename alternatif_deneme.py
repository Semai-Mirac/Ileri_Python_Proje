import matplotlib
# Add this line to set a headless backend for plotting, which can sometimes help with Tkinter in headless environments
# This line was already present but it's good practice to ensure it's at the top of the plotting imports.
matplotlib.use('Agg')

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
import sys # Import sys to check if in interactive mode

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
        # print(f"API Yanıtı: {r.json()}")  # API yanıtını tam olarak yazdırmayı devre dışı bırakalım, çok detaylı olabilir
        if r.status_code != 200:
            print(f"API isteği başarısız oldu. Durum kodu: {r.status_code}")
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
    except Exception as e:
        print(f"Oyun ismi alma hatası: {e}")
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
    except Exception as e:
        print(f"Bilgi çekme hatası: {e}")
        return ''

def anahtar_kelime_cikti(text, exclude_name='', top_n=5):
    words = re.findall(r"\b\w+\b", text.lower())
    # Exclude single-letter words from name exclusion set
    name_words = set(w for w in re.findall(r"\b[a-zA-Z]+\b", exclude_name.lower()) if len(w) > 1)
    filtered = [w for w in words if w.isalpha() and w not in IGNORE and len(w)>2 and w not in name_words]
    counts = Counter(filtered)
    return [w for w,_ in counts.most_common(top_n)]

# --- Feedback Fonksiyonları ---
def write_feedback(user_id, app_id, liked):
    feedback_data = []
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Check if the file is empty or has no header
                if not lines or lines[0].strip() != 'user_id,app_id,liked':
                    # If not, just start with the header and new data
                    feedback_data = []
                else:
                     # Skip header when reading existing data
                    for line in lines[1:]:
                        try:
                            uid, aid, lkd = line.strip().split(',')
                            feedback_data.append((uid, aid, lkd))
                        except ValueError:
                            # Skip lines with incorrect format
                            continue
        except Exception as e:
            print(f"Feedback dosyası okuma hatası: {e}")
            # If reading fails, start with empty data
            feedback_data = []


    updated = False
    # Use list comprehension for simpler update logic
    new_feedback_data = []
    found = False
    for uid, aid, lkd in feedback_data:
        if uid == str(user_id) and aid == str(app_id):
            new_feedback_data.append((uid, aid, str(liked)))
            found = True
        else:
            new_feedback_data.append((uid, aid, lkd))

    if not found:
        new_feedback_data.append((str(user_id), str(app_id), str(liked)))


    try:
        with open(FEEDBACK_FILE, 'w', encoding='utf-8') as f:
            f.write('user_id,app_id,liked\n')
            for uid, aid, lkd in new_feedback_data:
                f.write(f"{uid},{aid},{lkd}\n")
    except Exception as e:
        print(f"Feedback dosyası yazma hatası: {e}")


def load_user_feedback(user_id):
    liked_ids, disliked_ids = set(), set()
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, 'r', encoding='utf-8') as f:
                # Skip the header line safely
                try:
                    next(f)
                except StopIteration:
                    # File is empty, no feedback to load
                    return liked_ids, disliked_ids

                for line in f:
                    try:
                        uid, aid, lkd = line.strip().split(',')
                        if uid == str(user_id):
                            if lkd.lower() == 'true':
                                liked_ids.add(aid)
                            else:
                                disliked_ids.add(aid)
                    except ValueError:
                        # Skip lines with incorrect format
                        continue
        except Exception as e:
            print(f"Feedback yükleme hatası: {e}")

    return liked_ids, disliked_ids

# --- Öneri Mantığı ---
#--- SteamDB'den Fiyat Çekme Fonksiyonu ---

def oyun_fiyatlarını_alma_steamDB(app_id):
    url = f"https://steamdb.info/app/{app_id}/"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status() # HTTP errors için exception fırlat
        soup = BeautifulSoup(response.text, 'html.parser')
        # Türkiye fiyatını almak için ilgili HTML elemanını bulmak için yazdık burayı
        # SteamDB'nin HTML yapısı zamanla değişebilir, bu selector güncelliğini yitirebilir.
        price_div = soup.find('div', class_='game-price')
        if price_div:
            price_span = price_div.find('span', class_='price')
            if price_span:
                price = price_span.text.strip()
                return price
    except requests.exceptions.RequestException as e:
        print(f"SteamDB'den fiyat çekme hatası (HTTP/Request): {e}")
    except Exception as e:
        print(f"SteamDB'den fiyat çekme hatası (Genel): {e}")
    return None


# --- Fiyat Performans Önerisi Fonksiyonu ---
def onerilen_fiyat_performans_mantigi(games):
    # Kullanıcıya oyunlar listesi üzerinden fiyat-performans önerisi yapacağız
    best_game = None
    best_value = float('-inf')  # En yüksek değerli oyunu bulmak için başlatıyoruz
    # 'games' listesi (name, app_id, score) formatında olmalı
    price_performance_candidates = []
    for name, app_id, score in games: # games formatını (name, app_id, score) olarak varsayalım
         price = oyun_fiyatlarını_alma_steamDB(app_id)
         if price:
             price_performance_candidates.append((name, app_id, score, price))


    for name, app_id, score, price in price_performance_candidates:
        # Burada, fiyat-performans hesaplaması yapılabilir. Örneğin:
        # Skor / Fiyat = Değer oranı
        try:
            # Fiyatı "₺" işareti ile aldıysak, fiyatı sayıya çevirelim
            # Farklı para birimleri veya formatlar olabilir, daha esnek bir yaklaşım gerekebilir.
            price_str = price.replace('₺', '').replace('$', '').replace('€', '').replace(',', '.').strip()
            price_value = float(price_str)
            if price_value <= 0: # Sıfır veya negatif fiyatları atla
                 continue
            value = score / price_value  # Fiyat-performans hesaplama
            if value > best_value:
                best_value = value
                best_game = (name, app_id, score, price)
        except ValueError:
             print(f"Fiyat formatı hatası: {price}")
             continue
        except Exception as e:
             print(f"Fiyat performans hesaplama hatası: {e}")
             continue # Hata durumunda bu oyunu atla

    return best_game
## --- Cache ve API’den açıklama çeken yardımcı ---
# Cache'i burada yüklemek yerine, onerilen_oyun_mantigi içinde yüklemek daha iyi olabilir
# veya global cache değişkenini thread-safe bir şekilde yönetmek gerekir.
# Şimdilik global cache kullanımı devam ediyor, ama thread'ler arası yarış koşullarına dikkat.
cache = load_cache()

def get_about_text(app_id):
    key = str(app_id)
    # 1) Cache’de varsa direkt dön
    # Global cache'e erişim thread-safe olmayabilir. Basit durumlar için sorun olmayabilir.
    if key in cache:
        return cache[key]
    # 2) Yoksa Steam API’den çek, temizle, cache’e kaydet
    url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&key={API_KEY}"
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status() # HTTP hatalarını yakala
        data = r.json().get(key, {}).get('data', {})
        raw = data.get('about_the_game', '') or ''
        clean = BeautifulSoup(raw, "html.parser").get_text()
        if clean:
            # Cache'e kaydederken dikkatli ol, thread'ler arası yazma çakışabilir.
            # Basit file I/O için büyük olasılıkla sorun çıkmaz ama büyük uygulamalarda kilitmekanizması gerekebilir.
            cache[key] = clean
            # save_cache(cache) # save_cache'i her seferinde çağırmak I/O açısından pahalı olabilir.
                                # Belirli aralıklarla veya program kapanırken kaydetmek daha verimli olabilir.
                                # Ancak ThreadPoolExecutor içinde çağırmak özellikle tehlikeli olabilir.
                                # Önerilen: Cache'i RAM'de tut, program sonunda bir kere kaydet veya periyodik kaydet.
                                # Geçici çözüm: Thread içinden save_cache çağırma.
            pass # Save cache logic removed from here for thread safety
        return clean
    except requests.exceptions.RequestException as e:
        print(f"API'den about text çekme hatası (HTTP/Request): {e}")
        return ''
    except Exception as e:
        print(f"API'den about text çekme hatası (Genel): {e}")
        return ''

# --- Oyun Öneri Sistemi ---


def onerilen_oyun_mantigi(game_name, user_id=None):
    sel = game_name.lower().strip()
    # Cache'i fonksiyon içinde yüklemek, global cache kullanırken thread sorunlarını azaltır.
    # Her çağrıda yeniden yüklemek performansı düşürebilir, ancak güvenlik için daha iyidir.
    # Daha iyi bir yaklaşım: cache'i fonksiyon dışında başlat ve thread-safe bir şekilde eriş.
    # Basitlik için, şimdilik fonksiyon içinde yükleyelim.
    current_cache = load_cache()


    # --- 1) CSV'yi oku ve temizle ---
    try:
        df = pd.read_csv(
            INPUT_CSV,
            usecols=['AppID','Name','Genres','Tags','Screenshots'],
            dtype={'AppID':str}, encoding='ISO-8859-1'
        ).dropna(subset=['Name'])
        df['Name'] = df['Name'].astype(str)
        df['nm']   = df['Name'].str.lower().str.strip()
    except FileNotFoundError:
        print(f"Hata: {INPUT_CSV} dosyası bulunamadı.")
        return []
    except Exception as e:
        print(f"CSV okuma veya işleme hatası: {e}")
        return []


    sel_rows = df[df['nm'] == sel]
    if sel_rows.empty:
        print(f"'{game_name}' isminde bir oyun veritabanında bulunamadı.")
        return []
    sel_row    = sel_rows.iloc[0]
    sel_app_id = sel_row['AppID']
    # NaN değerleri boş string ile değiştir
    sel_text   = f"{sel_row['Genres'].astype(str)} {sel_row['Tags'].astype(str)} {sel_row['Screenshots'].astype(str)}"

    # --- 2) TF-IDF ile benzerlik ---
    others     = df[df['AppID'] != sel_app_id]
    all_ids    = others['AppID'].tolist()
    all_names  = others['Name'].tolist()
    # NaN değerleri boş string ile değiştir
    all_texts  = (others['Genres'].astype(str) + " " +
                  others['Tags'].astype(str)   + " " +
                  others['Screenshots'].astype(str)).tolist()

    if not all_texts:
        print("Benzerlik hesaplamak için başka oyun bulunamadı.")
        return []

    try:
        vec        = TfidfVectorizer(stop_words='english')
        tfidf      = vec.fit_transform(all_texts)
        user_vec   = vec.transform([sel_text])
        sims       = cosine_similarity(user_vec, tfidf).flatten()
    except Exception as e:
        print(f"TF-IDF veya Cosine Similarity hatası: {e}")
        return []


    # Zip the results and sort, filter out non-string names and DLCs
    ranked = sorted(zip(all_ids, all_names, sims),
                    key=lambda x: x[2], reverse=True)

    candidates = [
        (aid, name, score)
        for aid, name, score in ranked
        # Ensure name is a string before checking 'dlc'
        if isinstance(name, str) and 'dlc' not in name.lower()
    ][:50] # İlk 50 adayı alalım, fiyat çekmek hepsi için pahalı olabilir.


    if not candidates:
        print("Benzer oyun adayı bulunamadı.")
        return []


    # --- 3) Geri bildirimleri al ---
    liked_ids, disliked_ids = load_user_feedback(user_id) if user_id else (set(), set())

    # --- 4) ThreadPool ile about metinlerini çek ---
    abouts = {}
    # Pass the current_cache to the get_about_text function
    # Note: Modifying the cache object from multiple threads can still be problematic.
    # A Lock or a thread-safe cache implementation would be better for production.
    # For this example, we'll pass the cache and rely on simple dictionary operations.
    # The save_cache call is commented out in get_about_text for safety.
    with ThreadPoolExecutor(max_workers=10) as exe:
        future_to_aid = {exe.submit(get_about_text, aid): aid for aid, name, score in candidates}
        for fut in as_completed(future_to_aid): # CORRECTED: Loop over future_to_aid
            aid = future_to_aid[fut]
            try:
                abouts[aid] = fut.result()
            except Exception as exc:
                print(f'{aid} about text fetching generated an exception: {exc}')
                abouts[aid] = '' # Store empty string on error

    # --- 5) Seçilen oyun için de about metnini çek ---
    sel_about = get_about_text(sel_app_id)


    # --- 6) ThreadPool ile anahtar kelime çıkarımı ---
    sel_kw = anahtar_kelime_cikti(sel_about, sel_row['Name'])
    kw_map = {}
    with ThreadPoolExecutor(max_workers=20) as exe:
        # Prepare futures for keyword extraction
        future_to_pair = {
            exe.submit(anahtar_kelime_cikti, abouts.get(aid, ''), name): (aid, name) # Pass about text from the dict
            for aid, name, _ in candidates
        }
        for fut in as_completed(future_to_pair):
            aid, name = future_to_pair[fut]
            try:
                kw_map[aid] = fut.result()
            except Exception as exc:
                print(f'{name} keyword extraction generated an exception: {exc}')
                kw_map[aid] = [] # Store empty list on error

    # --- 7) Sonuçları hesapla ---
    results = []
    for aid, name, sim in candidates:
        kw     = kw_map.get(aid, [])
        # Ensure sel_kw is not empty to avoid division by zero
        ratio  = len(set(sel_kw) & set(kw)) / len(sel_kw) if sel_kw else 0
        boost  = 0.1 if aid in liked_ids else -0.2 if aid in disliked_ids else 0
        score  = 0.7 * sim + 0.3 * ratio + boost
        results.append((name, aid, score))

    # --- 8) Fiyat-performans önerisi (opsiyonel) ---
    # Pass the results list which contains (name, app_id, score) tuples
    best = onerilen_fiyat_performans_mantigi(results)
    if best:
        nm, aid, sc, pr = best
        # Fiyat-performans sonucunu ayrı bir giriş olarak ekle
        results.append((f"👑Fiyat Performans: {nm} ({pr})", aid, sc)) # Fiyatı da gösterelim

    # --- 9) Sırala ve dön ---
    results.sort(key=lambda x: x[2], reverse=True)

    # After computation, save the updated cache
    # This is done outside the ThreadPoolExecutor to avoid thread conflicts
    # This might still miss updates if the program crashes before saving.
    # A more robust solution involves periodic saving or a dedicated cache manager thread.
    # For now, save the current_cache that was modified (imperfectly) by threads.
    # A better way would be to collect updates from threads and apply them here, or use a thread-safe dict.
    # Assuming simple case where race conditions on dictionary writes are acceptable for this use case.
    save_cache(current_cache)


    return results[:5] # İlk 5 öneriyi dönelim

# Rest of the code remains the same


def steam_isimleri_cevir(vanity):
    url = f"https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/?key={API_KEY}&vanityurl={vanity}"
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status() # HTTP hatalarını yakala
        data = r.json()
        if data.get("response", {}).get("success") == 1:
            return data["response"]["steamid"]
        else:
             # Log the error message from the API if available
             message = data.get("response", {}).get("message", "Unknown error")
             print(f"Vanity URL çözümleme API hatası: {message}")
             return None
    except requests.exceptions.RequestException as e:
        print(f"Vanity URL çözümleme hatası (HTTP/Request): {e}")
    except Exception as e:
        print(f"Vanity URL çözümleme hatası (Genel): {e}")
    return None

# --- GUI ---

# Check if we are in an environment with a display before creating the GUI
# This is a basic check and might not work in all headless scenarios,
# but it prevents the TclError in common cases like running in a script
# without X11 forwarding.
try:
    # Attempt to create a Tkinter root. If it fails, a TclError is raised.
    # This might still fail if DISPLAY is set but X server is not accessible.
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
            if 'root' in globals() and root.winfo_exists(): # Check if root exists before showing messagebox
                 messagebox.showinfo('Teşekkürler', f'Geri bildiriminiz kaydedildi: {app_id} -> {liked}')
            else:
                 print(f'Geri bildirim kaydedildi: {app_id} -> {liked} (GUI kapalı)')

    def onerileri_goster(results):
         if 'root' in globals() and root.winfo_exists(): # Check if root exists before updating GUI
            clear_results()
            for i, (name, aid, score) in enumerate(results):
                lbl = ttk.Label(results_frame, text=f"{name} — AppID: {aid} | Skor: {score:.4f}")
                lbl.grid(row=i, column=0, sticky='w', pady=5)
                btn_like = ttk.Button(results_frame, text="Beğendim", command=lambda a=aid: on_feedback(a, True))
                btn_like.grid(row=i, column=1, padx=5)
                btn_dislike = ttk.Button(results_frame, text="Beğenmedim", command=lambda a=aid: on_feedback(a, False))
                btn_dislike.grid(row=i, column=2, padx=5)
         else:
             print("GUI aktif değil, öneriler konsola yazdırılıyor:")
             for name, aid, score in results:
                 print(f"{name} — AppID: {aid} | Skor: {score:.4f}")


    def Onerileri_goster_basıldıgında_oneri(game_name):
        # Run the recommendation logic
        results = onerilen_oyun_mantigi(game_name, current_user)
        # Update GUI on the main thread using root.after
        if 'root' in globals() and root.winfo_exists():
             root.after(0, lambda: [output_text.delete(1.0, tk.END), [output_text.insert(tk.END, f"{n} — AppID: {a} | Skor: {s:.4f}\n") for n,a,s in results]])
             root.after(0, lambda: onerileri_goster(results)) # Update the buttons frame as well
        else:
             # If GUI is not active, print to console
             print("GUI aktif değil, manuel öneriler konsola yazdırılıyor:")
             for n, a, s in results:
                 print(f"{n} — AppID: {a} | Skor: {s:.4f}")


    def Sonraki_Oyun_basildiginda_oneri(steam_id_input_text):
        # This function runs in a thread, avoid direct GUI manipulation
        if not steam_id_input_text.strip():
            if 'root' in globals() and root.winfo_exists():
                 root.after(0, lambda: messagebox.showwarning('Uyarı','Lütfen Steam ID girin.'))
            else:
                 print('Uyarı: Lütfen Steam ID girin.')
            return

        if not steam_id_input_text.isdigit():
            resolved_id = steam_isimleri_cevir(steam_id_input_text)
            if not resolved_id:
                 if 'root' in globals() and root.winfo_exists():
                    root.after(0,
                               lambda: messagebox.showwarning('Uyarı', 'Vanity URL çözümlenemedi. Geçerli bir Steam ID girin.'))
                 else:
                    print('Uyarı: Vanity URL çözümlenemedi. Geçerli bir Steam ID girin.')
                 return
            steam_id = resolved_id
        else:
            steam_id = steam_id_input_text

        global current_user
        current_user = steam_id_input_text # Use the original input for user ID

        # Cache'i yükle
        # Cache should ideally be thread-safe or passed explicitly
        cache = load_cache()

        # Steam ID'yi kullanarak son oynanan oyunları al
        app_ids = son_oynanan_oyuna_oneri(steam_id, cache)
        if not app_ids:
            if 'root' in globals() and root.winfo_exists():
                root.after(0, lambda: messagebox.showwarning('Uyarı','Son oynanan oyun bulunamadı veya Steam ID geçersiz.'))
            else:
                print('Uyarı: Son oynanan oyun bulunamadı veya Steam ID geçersiz.')
            return

        # Oyunları ve isimlerini al
        found_game = False
        for appid in app_ids:
            name = oyun_ismini_al(appid)
            if name:
                print(f"Son oynanan oyun bulundu: {name} (AppID: {appid}). Öneriler hesaplanıyor...")
                results = onerilen_oyun_mantigi(name, current_user)
                if results:
                    if 'root' in globals() and root.winfo_exists():
                        # Update GUI on the main thread
                        root.after(0, lambda r=results: onerileri_goster(r))
                        root.after(0, lambda r=results: [output_text.delete(1.0, tk.END), [output_text.insert(tk.END, f"{n} — AppID: {a} | Skor: {s:.4f}\n") for n,a,s in r]])
                    else:
                         # If GUI is not active, print to console
                         print("GUI aktif değil, Steam ID önerileri konsola yazdırılıyor:")
                         for n, a, s in results:
                             print(f"{n} — AppID: {a} | Skor: {s:.4f}")
                    found_game = True
                    break # Found a valid game and calculated recommendations, stop looping
                else:
                     print(f"'{name}' için öneri bulunamadı.")


        if not found_game:
             if 'root' in globals() and root.winfo_exists():
                 root.after(0, lambda: messagebox.showinfo('Bilgi','Son oynanan geçerli bir oyun bulunamadı.'))
             else:
                  print('Bilgi: Son oynanan geçerli bir oyun bulunamadı.')


    btn_manual.config(command=lambda: threading.Thread(target=lambda: [clear_results(), Onerileri_goster_basıldıgında_oneri(entry.get())]).start())
    btn_steam.config(command=lambda: threading.Thread(target=lambda: Sonraki_Oyun_basildiginda_oneri(steam_entry.get())).start())

    # Only start the main loop if the root window was successfully created
    root.mainloop()

except tk.TclError as e:
    print(f"Hata: Bir görüntüleme ayarı bulunamadı veya erişilemiyor. Tkinter GUI başlatılamadı.")
    print(f"Detay: {e}")
    print("Program GUI modunda çalıştırılamıyor.")
    # Optionally add a fallback for non-GUI interaction here
    # For example, ask for input via console and print results
    print("\nGUI mevcut değil. Konsol üzerinden bir oyun ismi girerek öneri almayı deneyebilirsiniz.")

    def run_cli_recommendation():
        game_name = input("Lütfen bir oyun ismi girin: ")
        if game_name:
            print(f"'{game_name}' için öneriler hesaplanıyor...")
            # You can optionally ask for