<a href="https://buycoffee.to/kopciu" target="_blank" rel="noopener noreferrer">
  <img src="https://kopciu.info/coffee.png" alt="BuyCoffee.to – Postaw kawę">
</a>

# Euros OS — Home Assistant integration

Integracja **Euros OS** zapewnia lokalny odczyt danych urządzeń EurosEnergy / E-On przez MQTT/TLS oraz wybrane, zabezpieczone funkcje sterowania pompą ciepła.

> **Status: kandydat do jednego PR dla autora, nie oficjalne wydanie.** Numer wersji i minimalna obsługiwana wersja Home Assistant wymagają uzgodnienia z autorem. Na polecenie właściciela projektu nie zmieniamy istniejącego TLS ani wspólnych fabrycznych danych logowania. **Istniejący TLS 1.3 szyfruje przesyłane dane, lecz użycie `ssl._create_unverified_context()` oznacza brak uwierzytelnienia brokera i ryzyko MITM / przechwycenia poświadczeń.** Jest to świadomie zaakceptowane ograniczenie, a NIE naprawiona luka. Nie udostępniaj portu 8883 do Internetu; ogranicz dostęp sieciowy do zaufanych urządzeń. Szczegóły diagnostyki: [TLS](docs/ETAP_9_2_TLS_DIAGNOSTYKA.md).

## Obsługiwane urządzenia i rzeczywisty zakres testów

| Model / typ | Obsługa w kodzie | Potwierdzenie |
| --- | --- | --- |
| **FriskoGEO** / Euros GEO | Odczyty temperatur, stanów pracy, trybów, ograniczone sterowanie, obliczane ΔT | Test na rzeczywistym GEO 06 SH i HA Core 2026.11.1 |
| **FriskoATMO** | Wykrywanie i dotychczasowe encje | Testy automatyczne, bez testu fizycznego w tym projekcie |
| **FriskoALLINONE** | Wykrywanie i dotychczasowe encje | Testy automatyczne, bez testu fizycznego w tym projekcie |
| **METER_1 (EMS – Dom)** | 35 encji: 33 bezpośrednie odczyty + 2 liczniki dzienne, tylko do odczytu | Test na rzeczywistym liczniku |
| **METER_2 / METER_3 / METER_N** | Dynamiczne wykrywanie, gdy urządzenie jest obecne w danych MQTT | Testy symulacyjne; fizyczne dodatkowe liczniki niezweryfikowane |

**Ważne:** `METER_1` mierzy import/eksport energii **całego domu**, a nie wyłącznie pobór mocy pompy ciepła. Nie należy interpretować danych EMS Dom jako licznika samego GEO.

## Funkcje

- Rozpoznawanie skonfigurowanej pompy niezależnie od kolejności rekordów `Devices` i odrzucanie niejednoznacznych pakietów.
- Odczyty GEO: temperatura CO, CWU, dolnego i górnego źródła, różnice temperatur ΔT, stan pracy, wersja sterownika i wybrane nastawy.
- 35 encji EMS Dom, w tym napięcia i prądy fazowe, moc czynną/bierną/pozorną, energię importowaną/eksportowaną i liczniki dzienne; część pól jest oznaczona jako *techniczne* i nie powinna służyć do rozliczeń.
- Obsługa zmiennych `METER_N`, bez tworzenia fikcyjnych liczników.
- Oddzielna kontrola świeżości danych pompy i poszczególnych liczników, reakcja na timeout MQTT, ponowne połączenie oraz sprzątanie klienta MQTT przy wyładowaniu integracji.
- Zachowanie identyfikatorów encji i urządzeń przy aktualizacji jest wymaganiem projektowym; nie należy ich resetować.
- Ograniczenia bezpieczeństwa sterowania GEO. Odczyt trybu **EMS** jest obsługiwany, ale **przełączanie do EMS i niezweryfikowane przejścia z EMS do AUTO są celowo blokowane**; do takich zmian używaj oficjalnej aplikacji Euros Smart.

## Wymagania

- Home Assistant z obsługą integracji niestandardowych oraz lokalny dostęp do brokera MQTT sterownika.
- Certyfikat i połączenie MQTT na porcie **8883**; produkcyjne urządzenia mogą mieć prywatne CA lub certyfikaty z niezgodną nazwą/IP. Aktualna metoda weryfikacji TLS ma otwarte zastrzeżenie bezpieczeństwa.
- Klucz urządzenia oraz adres brokera wymagane przez dotychczasowy Config Flow.
- **Minimalna wersja HA nieustalona dla wydania:** stare deklaracje rozbieżne (`hacs.json`: 2021.12.0; wcześniejszy README: 2023.3). Testy tej gałęzi obejmują HA Core 2026.11.0/2026.11.1 i kilka wersji Pythona; nie dowodzą zgodności ze starymi instalacjami.

## Instalacja i aktualizacja

### Nowa instalacja po opublikowaniu zatwierdzonego wydania

1. Korzystaj z oficjalnego repozytorium autora: https://github.com/McKoPcIu/EurosOS .
2. W HACS / Marketplace zainstaluj **wydaną wersję**, nie gałąź developerską.
3. Uruchom ponownie Home Assistant zgodnie z instrukcją danej wersji.
4. Dodaj integrację Euros OS w **Ustawienia → Urządzenia i usługi**, podając wymagane dane konfiguracyjne.
5. Sprawdź dostępność odczytów i poprawność identyfikacji urządzenia.

### Aktualizacja istniejącej instalacji

**Nie usuwaj istniejącego wpisu integracji ani encji.** Przed aktualizacją wykonaj pełną kopię HA z bazą historii, zapisz kopię katalogu `custom_components/euros_os` i punkt odniesienia rejestru encji. Po aktualizacji porównaj `entity_id`, `unique_id`, powiązania urządzeń oraz statystyki energii. Pełną procedurę, warunki stop i rollback zawiera [instrukcja aktualizacji](docs/RELEASE_UPGRADE_AND_ROLLBACK.md).

### Konfiguracja brokera pompy

Nie zmieniaj samodzielnie konfiguracji systemowej pompy, plików na karcie SD ani reguł firewalla wyłącznie na podstawie ogólnego README. Historyczna [instrukcja MQTT](MQTT_SETUP.md) może dotyczyć konkretnego sterownika i niesie ryzyko utraty komunikacji, naruszenia bezpieczeństwa lub warunków gwarancji. Zweryfikuj sposób konfiguracji z producentem lub autoryzowanym serwisem.

## Testy i ograniczenia

Dotychczasowy raport [ETAP 9.4](docs/ETAP_9_4_TESTY_AUTOMATYCZNE.md): **154/154** testów jednostkowych i symulacyjnych na Pythonie 3.12, 3.13 i 3.14, a także **6** testów z bibliotekami / testową instancją HA Core 2026.11.0, z atrapą MQTT. Wyniki odnoszą się do raportowanego commitu z 12 listopada 2026 r., **nie do nowego wydania ani do każdego późniejszego commitu**. Test rzeczywistego GEO i METER_1 objął 73 zachowane encje, 2 urządzenia i 32 serie statystyczne EMS z zapisami przed i po aktualizacji; nie oznacza to formalnej walidacji wszystkich modeli i scenariuszy.

Zobacz [listę kontrolną przed PR](docs/RELEASE_CANDIDATE_CHECKLIST.md) oraz [CHANGELOG](CHANGELOG.md).

## Wsparcie i autorstwo

- Autor integracji: Patryk „KoPcIu” Kopeć, https://github.com/McKoPcIu/EurosOS
- Dyskusja społeczności: [Pompy Ciepła E.ON Air Euros Atmo DIY](https://www.facebook.com/groups/1068907574414311?locale=pl_PL)
- Zgłoszenia błędów i sugestii: https://github.com/McKoPcIu/EurosOS/issues

Projekt zachowuje dotychczasowe autorstwo i licencję MIT. Zmiany eksperymentalne z forka nie są oficjalnym wydaniem autora.
