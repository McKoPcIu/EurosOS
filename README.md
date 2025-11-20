# Euros OS Home Assistant Integration

Integracja **Euros OS** umożliwia monitorowanie i kontrolowanie systemów grzewczych EurosEnergy oraz E-On poprzez **MQTT** w Home Assistant.  
Dzięki tej integracji możesz wyświetlać temperatury, stany pracy, tryby urządzenia oraz zużycie energii w czasie rzeczywistym, a także aktualizować wybrane wartości urządzenia wraz z zmianą trybu pracy.

---

## Funkcje

- Pobieranie danych z urządzeń EurosEnergy oraz E-On przez MQTT.
- Obsługa wielu sensorów:
  - Temperatury i stany urządzenia
  - Tryb pracy (AUTO, ECO, TIME, AWAY, OFF)
  - Aktulane oraz całkowite zużycie energii elektrycznej, które można zaimplementować do zakładki "Energia"
- Łatwa konfiguracja w Home Assistant przy użyciu **Config Flow** – wystarczy podać adres IP urządzenia oraz klucz produktu.

---

## Wymagania

- Home Assistant ≥ 2023.3
- Urządzenie EurosEnergy lub E-On z działającym brokerem MQTT

---

## Instalacja

### 1. Ręczna

1. Skopiuj katalog `custom_components/euros_os` do katalogu konfiguracji Home Assistant `/config`, aby powstała ścieżka `/config/custom_components/euros_os/__init__.py`.
2. Uruchom ponownie Home Assistant.
3. W panelu `Konfiguracja → Urządzenia i usługi → Dodaj integrację` wyszukaj **Euros OS**.
4. Podaj:
   - Klucz urządzenia (Device Key)
   - Adres IP pompy ciepła w Twojej lokalnej sieci.
5. Integracja automatycznie pobierze odpowiednie dane.

### 2. Dzięki HACS

1. **Dodaj repozytorium do HACS**  
   HACS → Integracje → + Dodaj repozytorium  
   - URL: `https://github.com/McKoPcIu/EurosOS`  
   - Typ: Integracja → Dodaj  

2. **Zainstaluj integrację**  
   HACS → Integracje → Euros OS → Zainstaluj  

3. **Restart Home Assistant**  
   Ustawienia → System → Uruchom ponownie  

4. **Dodaj integrację w HA**  
   Konfiguracja → Urządzenia i usługi → Dodaj integrację → Euros OS  
   Wprowadź:  
   - Klucz urządzenia (Device Key)  
   - Adres IP pompy ciepła  

**Gotowe** – sensory i liczby pojawią się automatycznie w HA

---

### 3. ⚠️ Modyfikacja plików pompy
Aby umożliwić połączenie z Home Assistant przez MQTT, wymagana jest edycja pliku na karcie SD pompy, plik `/etc/iptables/rules.v4` i dodać linię:

```
-A INPUT -i eth0 -p tcp --dport 8883 -j ACCEPT
```

Więcej informacji na temat konfiguracji znajdziesz w [MQTT_SETUP.md](MQTT_SETUP.md).

---

## Konfiguracja

Po dodaniu integracji w Home Assistant:

- Każdy sensor zostanie utworzony automatycznie.
- Sensory będą odświeżane na bieżąco przy otrzymaniu danych MQTT.
- Jeśli dane nie nadejdą przez określony czas (domyślnie 60 sekund), encja przechodzi w stan `unavailable`.

Przykładowe encje:

| Sensor | Opis |
|--------|------|
| `Temperatura CO` | Aktualna temperatura w obiegu CO |
| `Temperatura CWU` | Aktualna temperatura w obiegu CWU |
| `Tryb pracy` | AUTO / ECO / TIME / AWAY / OFF |
| `Energia całkowita` | Zużycie energii w kWh |

---

## Wsparcie

- Grupa E-On na FB: [Pompy Ciepła E.ON Air Euros Atmo DIY](https://www.facebook.com/groups/1068907574414311?locale=pl_PL)
- Repozytorium GitHub: [Repozytorium](https://github.com/McKoPcIu/Euros_OS)
- Błędy i sugestie można zgłaszać bezpośrednio w GitHub.

---

## Licencja

MIT License © 2025 Patryk "KoPcIu" Kopeć
