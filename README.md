# Ileri_Python_Proje
TF-IDF algoritması ile oyun tavsiye sistemi

---

### 1. **Projenin Genel Amacı**
- Kullanıcıların oynadığı oyunlara veya belirttiği oyun isimlerine göre benzer oyunları öneren bir sistem geliştirilmiştir.
- Öneriler, oyunların açıklamaları, türleri, etiketleri ve ekran görüntüleri gibi metin tabanlı veriler üzerinden **TF-IDF (Term Frequency-Inverse Document Frequency)** algoritması ile hesaplanan benzerliklere dayanmaktadır.
- Kullanıcı geri bildirimleri (beğenme veya beğenmeme) de öneri sistemine dahil edilerek daha kişiselleştirilmiş sonuçlar sunulmaktadır.

---

### 2. **Kullanılan Teknolojiler ve Kütüphaneler**
- **Python**: Projenin temel programlama dili.
- **Tkinter**: Kullanıcı arayüzü (GUI) oluşturmak için kullanılmıştır.
- **Pandas**: Veri işleme ve CSV dosyalarını okumak için kullanılmıştır.
- **Requests**: Steam API ve diğer web isteklerini gerçekleştirmek için kullanılmıştır.
- **BeautifulSoup**: HTML temizleme ve web scraping işlemleri için kullanılmıştır.
- **Scikit-learn**: TF-IDF vektörleştirme ve benzerlik hesaplamaları için kullanılmıştır.
- **Threading ve ThreadPoolExecutor**: Çoklu iş parçacığı kullanılarak API isteklerinin ve hesaplamaların daha hızlı yapılması sağlanmıştır.

---

### 3. **Kodun Ana Bölümleri**

#### a. **Cache Yönetimi**
- **`load_cache` ve `save_cache`** fonksiyonları, oyun bilgilerini bir JSON dosyasında önbelleğe alarak API isteklerini azaltır ve performansı artırır.

#### b. **Steam API Entegrasyonu**
- Kullanıcının Steam ID'sine göre son oynadığı oyunlar **Steam API** üzerinden alınır.
- **`son_oynanan_oyuna_oneri`** fonksiyonu, kullanıcının son oynadığı oyunların AppID'lerini döndürür.

#### c. **Oyun Bilgisi Çekme**
- **`bilgi_cek`** fonksiyonu, bir oyunun açıklama metnini Steam mağazasından alır ve HTML etiketlerinden temizler.
- Bu bilgiler, oyunlar arasındaki benzerlikleri hesaplamak için kullanılır.

#### d. **TF-IDF ile Benzerlik Hesaplama**
- **`onerilen_oyun_mantigi`** fonksiyonu, kullanıcının belirttiği oyun ismine göre diğer oyunlarla olan benzerlikleri hesaplar.
- **TF-IDF algoritması**, oyunların açıklama metinlerini vektörleştirir ve **cosine similarity** ile benzerlik skorları hesaplanır.

#### e. **Kullanıcı Geri Bildirimi**
- Kullanıcılar, önerilen oyunları "Beğendim" veya "Beğenmedim" olarak işaretleyebilir.
- Bu geri bildirimler, bir CSV dosyasında saklanır ve öneri skorlarına etki eder.

#### f. **Fiyat-Performans Önerisi**
- **`onerilen_fiyat_performans_mantigi`** fonksiyonu, oyunların fiyat bilgilerini **SteamDB** üzerinden çekerek fiyat-performans analizi yapar.
- Kullanıcıya en iyi fiyat-performans oranına sahip oyun önerilir.

#### g. **Kullanıcı Arayüzü (GUI)**
- **Tkinter** kullanılarak bir grafiksel arayüz oluşturulmuştur.
- Kullanıcı, oyun ismini veya Steam ID'sini girerek öneri alabilir.
- Öneriler, arayüzde listelenir ve kullanıcı geri bildirimleri alınabilir.

---

### 4. **Projenin İşleyişi**
1. **Oyun İsmi ile Öneri**:
   - Kullanıcı, bir oyun ismi girer.
   - Sistem, girilen oyun ismine benzer oyunları TF-IDF algoritması ile analiz ederek önerir.

2. **Steam ID ile Öneri**:
   - Kullanıcı, Steam ID'sini girer.
   - Sistem, kullanıcının son oynadığı oyunları bulur ve bu oyunlara benzer oyunları önerir.

3. **Geri Bildirim**:
   - Kullanıcı, önerilen oyunları beğenip beğenmediğini işaretleyebilir.
   - Bu geri bildirimler, öneri algoritmasının sonuçlarını etkiler.

4. **Fiyat-Performans Önerisi**:
   - Sistem, önerilen oyunlar arasından en iyi fiyat-performans oranına sahip oyunu belirler ve kullanıcıya sunar.

---

### 5. **Sonuç**
Bu proje, kullanıcıların oyun tercihlerini analiz ederek onlara en uygun oyunları önermeyi hedefleyen bir sistemdir. Kullanıcı geri bildirimleri ve fiyat-performans analizi gibi özelliklerle öneri sistemi daha da geliştirilmiştir. Bu sayede, kullanıcılar hem ilgi alanlarına uygun hem de bütçelerine uygun oyunlar bulabilirler.


Bu projede, TF-IDF algoritması kullanılarak bir oyun öneri sistemi geliştirilmiştir. Projenin amacı, kullanıcının oynadığı oyunlara veya belirttiği oyun isimlerine göre benzer oyunlar önererek kullanıcı deneyimini geliştirmektir. Aşağıda, kodun genel işleyişi ve önemli bölümleri detaylı bir şekilde açıklanmıştır:

1. Projenin Genel Amacı
Kullanıcıların oynadığı oyunlara veya belirttiği oyun isimlerine göre benzer oyunları öneren bir sistem geliştirilmiştir.
Öneriler, oyunların açıklamaları, türleri, etiketleri ve ekran görüntüleri gibi metin tabanlı veriler üzerinden TF-IDF (Term Frequency-Inverse Document Frequency) algoritması ile hesaplanan benzerliklere dayanmaktadır.
Kullanıcı geri bildirimleri (beğenme veya beğenmeme) de öneri sistemine dahil edilerek daha kişiselleştirilmiş sonuçlar sunulmaktadır.
2. Kullanılan Teknolojiler ve Kütüphaneler
Python: Projenin temel programlama dili.
Tkinter: Kullanıcı arayüzü (GUI) oluşturmak için kullanılmıştır.
Pandas: Veri işleme ve CSV dosyalarını okumak için kullanılmıştır.
Requests: Steam API ve diğer web isteklerini gerçekleştirmek için kullanılmıştır.
BeautifulSoup: HTML temizleme ve web scraping işlemleri için kullanılmıştır.
Scikit-learn: TF-IDF vektörleştirme ve benzerlik hesaplamaları için kullanılmıştır.
Threading ve ThreadPoolExecutor: Çoklu iş parçacığı kullanılarak API isteklerinin ve hesaplamaların daha hızlı yapılması sağlanmıştır.
3. Kodun Ana Bölümleri
a. Cache Yönetimi
load_cache ve save_cache fonksiyonları, oyun bilgilerini bir JSON dosyasında önbelleğe alarak API isteklerini azaltır ve performansı artırır.
b. Steam API Entegrasyonu
Kullanıcının Steam ID'sine göre son oynadığı oyunlar Steam API üzerinden alınır.
son_oynanan_oyuna_oneri fonksiyonu, kullanıcının son oynadığı oyunların AppID'lerini döndürür.
c. Oyun Bilgisi Çekme
bilgi_cek fonksiyonu, bir oyunun açıklama metnini Steam mağazasından alır ve HTML etiketlerinden temizler.
Bu bilgiler, oyunlar arasındaki benzerlikleri hesaplamak için kullanılır.
d. TF-IDF ile Benzerlik Hesaplama
onerilen_oyun_mantigi fonksiyonu, kullanıcının belirttiği oyun ismine göre diğer oyunlarla olan benzerlikleri hesaplar.
TF-IDF algoritması, oyunların açıklama metinlerini vektörleştirir ve cosine similarity ile benzerlik skorları hesaplanır.
e. Kullanıcı Geri Bildirimi
Kullanıcılar, önerilen oyunları "Beğendim" veya "Beğenmedim" olarak işaretleyebilir.
Bu geri bildirimler, bir CSV dosyasında saklanır ve öneri skorlarına etki eder.
f. Fiyat-Performans Önerisi
onerilen_fiyat_performans_mantigi fonksiyonu, oyunların fiyat bilgilerini SteamDB üzerinden çekerek fiyat-performans analizi yapar.
Kullanıcıya en iyi fiyat-performans oranına sahip oyun önerilir.
g. Kullanıcı Arayüzü (GUI)
Tkinter kullanılarak bir grafiksel arayüz oluşturulmuştur.
Kullanıcı, oyun ismini veya Steam ID'sini girerek öneri alabilir.
Öneriler, arayüzde listelenir ve kullanıcı geri bildirimleri alınabilir.
4. Projenin İşleyişi
Oyun İsmi ile Öneri:

Kullanıcı, bir oyun ismi girer.
Sistem, girilen oyun ismine benzer oyunları TF-IDF algoritması ile analiz ederek önerir.
Steam ID ile Öneri:

Kullanıcı, Steam ID'sini girer.
Sistem, kullanıcının son oynadığı oyunları bulur ve bu oyunlara benzer oyunları önerir.
Geri Bildirim:

Kullanıcı, önerilen oyunları beğenip beğenmediğini işaretleyebilir.
Bu geri bildirimler, öneri algoritmasının sonuçlarını etkiler.
Fiyat-Performans Önerisi:

Sistem, önerilen oyunlar arasından en iyi fiyat-performans oranına sahip oyunu belirler ve kullanıcıya sunar.
5. Sonuç
Bu proje, kullanıcıların oyun tercihlerini analiz ederek onlara en uygun oyunları önermeyi hedefleyen bir sistemdir. Kullanıcı geri bildirimleri ve fiyat-performans analizi gibi özelliklerle öneri sistemi daha da geliştirilmiştir. Bu sayede, kullanıcılar hem ilgi alanlarına uygun hem de bütçelerine uygun oyunlar bulabilirler.