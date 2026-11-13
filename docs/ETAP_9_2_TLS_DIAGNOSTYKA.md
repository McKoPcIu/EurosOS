# Euros OS — ETAP 9.2.5: strategia bezpieczeństwa MQTT/TLS

**Stan: 2026-11-12 — diagnoza w toku; problem P1.** Ten dokument służy wyłącznie przygotowaniu bezpiecznej strategii. Nie zmienia działania integracji ani konfiguracji pompy.

## Fakty ustalone na podstawie rzeczywistego odczytu

- Broker MQTT pompy odpowiada na porcie TLS 8883, udostępnia certyfikat X.509.
- Certyfikat ma subject CN `ee-agent`, issuer CN `An MQTT broker`, opis organizacji `OwnTracks.org`. To są napisy w certyfikacie, **nie dowód zaufania do CA**.
- Certyfikat jest ważny czasowo od 2020-05-12 do 2032-05-09.
- Zawiera SAN DNS `ee-agent`, `localhost` i adres IPv4 różny od aktualnego adresu urządzenia. Standardowe porównanie `checkip` z bieżącym IP powinno nie przejść.
- Upstream używa `ssl._create_unverified_context()` zarówno w `coordinator.py`, jak i w `config_flow.py`. Chroni to treść przed biernym podsłuchem, ale nie uwierzytelnia tożsamości serwera i jest ryzykiem MITM.
- `const.py` zawiera odziedziczony model statycznych poświadczeń MQTT. Nie dołączać wartości tych poświadczeń, logów uwierzytelniania ani pełnych MQTT payloadów do zgłoszeń i dokumentacji.
- Nie wiemy, czy firmware używa wspólnego certyfikatu, indywidualnego certyfikatu urządzenia, własnej CA ani czy wspiera wymianę certyfikatu bez ryzyka dla urządzenia.

## Bezpieczne testy read-only — terminal Home Assistant

Zastąpić `<IP_POMPY>` lokalnym adresem IP urządzenia. Polecenia nawiązują jedynie połączenie TLS i nie wykonują MQTT CONNECT, SUBSCRIBE ani PUBLISH.

### A. Zweryfikuj dopasowanie aktualnego IP (nie wymaga zaufanej CA)

```sh
openssl s_client -connect <IP_POMPY>:8883 -showcerts </dev/null 2>/dev/null | openssl x509 -noout -checkip <IP_POMPY> -fingerprint -sha256
```

Możliwy rezultat: `IP <IP_POMPY> does NOT match certificate`. SHA-256 to odcisk **publicznego certyfikatu**, nie klucz prywatny. Zachować go w prywatnej dokumentacji diagnostycznej, jeśli ma służyć jako przyszły punkt odniesienia.

### B. Zweryfikuj łańcuch certyfikatów i zgodność adresu

```sh
openssl s_client -connect <IP_POMPY>:8883 -verify_return_error -verify_ip <IP_POMPY> -brief </dev/null 2>&1
```

Błąd `unable to get local issuer certificate` albo `self-signed certificate in certificate chain` oznacza brak zaufanego łańcucha w lokalnym magazynie. Błąd `IP address mismatch` oznacza niezgodność nazwy/adresu. Ten test może zatrzymać się na *pierwszym* błędzie, dlatego A i B należy analizować osobno.

### C. Liczba certyfikatów wysyłanych przez broker (opcjonalnie)

```sh
openssl s_client -connect <IP_POMPY>:8883 -showcerts </dev/null 2>/dev/null | grep -c -- '-----BEGIN CERTIFICATE-----'
```

`-showcerts` pokazuje certyfikaty przesłane przez serwer; nie jest to dowód poprawności pełnego łańcucha.

## Wyniki wykonanych testów — 12 listopada 2026 r.

Wyniki pochodzą z terminala Home Assistant i zostały odczytane z publicznego certyfikatu serwera. Nie wykonywano żadnej zmiany na pompie ani publikacji MQTT.

1. **Test A — wynik: NEGATYWNY.** `openssl x509 -checkip` zwrócił `IP 192.168.1.17 does NOT match certificate`. Fingerprint SHA-256 został odczytany i przekazany w rozmowie; nie publikujemy tutaj unikatowego odcisku sprzętu użytkownika.
2. **Test B — wynik: NEGATYWNY.** `openssl s_client -verify_return_error -verify_ip` zwrócił `depth=1` i `verify error:num=19:self-signed certificate in certificate chain`, po czym handshake przerwano. To wskazuje na niezaufany certyfikat na poziomie wystawcy w łańcuchu; **nie** dowodzi, że sam certyfikat serwera jest samopodpisany. Ponieważ test zakończył się na błędzie zaufania, nie rozstrzyga niezależnie kolejnego sprawdzenia IP (to wykonał test A).
3. **Test C — wykonany: wynik `2`.** Broker przesłał dokładnie dwa bloki PEM `BEGIN CERTIFICATE`. Typowy układ to certyfikat brokera i certyfikat wystawcy, jednak sama liczba **nie dowodzi**, że drugi certyfikat jest prawidłowym CA ani że należy mu ufać. Niezależne potwierdzenie wystawcy przez producenta nadal nie zostało przeprowadzone.
4. **Wniosek:** standardowa ścieżka z zaufanym CA i dopasowaniem aktualnego IP nie przejdzie w obecnym stanie. Dwa osobne problemy: brak zaufania do lokalnego/root CA oraz niezgodność SAN z aktualnym adresem IP pompy. Nadal nie mamy niezależnie uwierzytelnionej CA ani modelu odnowy certyfikatu.
5. **Decyzja:** nie przełączać działającego Home Assistant na ścisły TLS, nie podmieniać adresu IP, nie wyłączać zabezpieczeń w systemie operacyjnym i nie implementować pinningu na podstawie jednorazowego odczytu z niezaufanego połączenia. Zadanie 9.2.5 pozostaje **P1 / otwarte**.

## Drugi certyfikat — badanie wykonane 2026-11-12

Przeprowadzono odczyt publicznych metadanych drugiego certyfikatu z łańcucha. Wynik:

- Subject: `CN=An MQTT broker, O=OwnTracks.org, OU=generate-CA`.
- Issuer: identyczny jak Subject, zgodny z wcześniej zaobserwowanym błędem OpenSSL dotyczącym samopodpisanego wystawcy.
- `basicConstraints`: **critical, CA:TRUE** — certyfikat przeznaczony do pełnienia funkcji urzędu certyfikacji.
- Ważny od `2020-05-12 17:43:36 GMT` do `2032-05-09 17:43:36 GMT`.

**Interpretacja:** drugi certyfikat to samopodpisany Root CA, lecz nie jest sam przez się *zaufany*. Certyfikat serwera (pierwszy w łańcuchu) jest przez niego deklaratywnie wystawiony. Do potwierdzenia podpisu serwera i poprawności łańcucha można użyć testu z lokalnie podanym CA, ale **nie dowiedzie to autentyczności CA bez niezależnego kanału**.

Nazwy z Subject/Issuer (`An MQTT broker`, `OwnTracks.org`, `generate-CA`) odpowiadają wartościom w publicznym skrypcie OwnTracks `generate-CA.sh`: https://github.com/owntracks/tools/blob/master/TLS/generate-CA.sh . To istotna poszlaka dotycząca metody wygenerowania certyfikatu, **nie dowód, że pompa korzysta z usługi OwnTracks lub że znamy tożsamość operatora CA**.

### Następna decyzja

1. Zwrócić się do dostawcy/producenta sterownika o *niezależnie dostarczony certyfikat publiczny CA albo oficjalny odcisk CA*, informację o udokumentowanym procesie wymiany/odnawiania certyfikatów oraz możliwości weryfikowania nazwy `ee-agent` przy połączeniu do aktualnego IP pompy.
2. Opcjonalnie potwierdzić w samych testach offline, że certyfikat brokera jest podpisany przez pobrany CA i jego SAN zawiera `ee-agent`; taka próba techniczna **nie ustanawia zaufania** i nie nadaje się jako jedyna podstawa wdrożenia.
3. Nie zmieniać teraz `ssl._create_unverified_context()` w produkcyjnym HA: istnieje ryzyko odcięcia komunikacji przy nagłym włączeniu walidacji. Nie zmieniać adresu pompy ani jej certyfikatu.
4. Nie odkładać pozostałych niezależnych prac ETAPU 9 na czas oczekiwania na źródło zaufania. 9.2.5 pozostaje P1 i blokuje końcową bramkę wydania.

## Decyzje projektowe — bez dokonywania zmian w pompie

1. **Preferowane, jeśli wspierane przez producenta:** serwer przedstawia certyfikat ważny dla faktycznej nazwy/IP urządzenia, podpisany przez zaufaną CA (publiczną lub bezpiecznie dostarczoną własną). Wtedy `ssl.create_default_context()`, `CERT_REQUIRED` i sprawdzanie nazwy.
2. **Po udokumentowaniu producenta:** opcjonalna własna CA wskazana przez użytkownika; wymaga osobnego testu dopasowania nazwy/IP. Samo zaufanie CA NIE naprawia niezgodności SAN.
3. **Bez potwierdzonego łańcucha:** pozostać przy dotychczasowej zgodnej z urządzeniem ścieżce tylko jako jawnie rozpoznanym ograniczeniu bezpieczeństwa, bez twierdzenia, że jest bezpieczna przed MITM; dalszy plan z autorem urządzenia/integracji. Nie stosować pozornej poprawy przez `tls_insecure_set(True)`.
4. **Certificate pinning / TOFU:** ewentualny tryb zaawansowany po uzgodnieniu modelu kluczy, niezależnego zaufanego kanału pozyskania fingerprintu, rotacji certyfikatów i możliwości technicznej weryfikacji **przed** wysłaniem danych uwierzytelniających. Nie implementować na ślepo.
5. **Statyczne poświadczenia:** sprawdzić, czy urządzenie rzeczywiście pozwala je zmieniać i jakie są skutki dla istniejących użytkowników. Nie usuwać/nie modyfikować poświadczeń w kodzie bez potwierdzonego mechanizmu konfiguracji.

## Kryteria zamknięcia 9.2.5

- [x] Ustalono, że certyfikat ma SAN niepasujący do bieżącego IP i jest czasowo ważny.
- [x] Potwierdzono w kodzie i dokumentacji Paho, że połączenie nie weryfikuje zaufania.
- [x] Zebrano wynik `checkip` (A) i diagnozę łańcucha (B), oba negatywne.
- [x] Odczytano liczbę certyfikatów przesłanych przez broker (C): **2**.
- [x] Potwierdzono rolę drugiego certyfikatu: samopodpisany Root CA, `CA:TRUE`.
- [ ] Niezależnie potwierdzono tożsamość i autentyczność wystawcy (CA) u producenta lub innym zaufanym kanałem.
- [ ] Udokumentowano ostateczne ograniczenia i wybrany model wdrożenia, kompatybilny z realnym urządzeniem i innymi modelami Euros OS.
- [ ] Zweryfikowano docelową implementację i regresję albo formalnie uznano nierozwiązany problem za **blokadę wydania**.

**Nigdy** nie kopiować prywatnych kluczy, haseł, plików HA `.storage` ani kompletnych danych pompy do publicznego repozytorium.

## Źródła techniczne

- https://docs.openssl.org/master/man1/openssl-x509/
- https://docs.openssl.org/master/man1/openssl-s_client/
- https://docs.python.org/3/library/ssl.html
- https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html
