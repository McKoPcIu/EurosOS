# Euros OS — lista kontrolna kandydata wydania i jednego końcowego PR

Stan na 2026-11-13. **Decyzja właściciela 13.11.2026: dopuszcza przedstawienie integracji autorowi w jednym PR z jawnym ujawnieniem ograniczeń TLS i poświadczeń.** Nie jest to potwierdzenie bezpieczeństwa połączenia ani upoważnienie do scalenia lub wydania oficjalnej wersji przez autora.

## A. Funkcjonalność i zgodność

- [x] Projekt i automatyczne testy rozpoznawania GEO, ATMO, ALLINONE i METER_N istnieją.
- [x] Test rzeczywistego HA Core 2026.11.1: GEO_1 + METER_1, 2 urządzenia / 73 encje; dostępność i porównanie rejestrów PASS.
- [x] 32 serie EMS mają wpisy w obu okresach względem daty aktualizacji; brak dowodu lukowej kompletności każdej serii.
- [x] Testy sim / HA Core były zielone 12.11.2026: 154/154 na 3 wersjach Python, 6 testów HA Core z atrapą MQTT.
- [ ] Wszystkie testy zielone ponownie na **ostatecznym commicie release**.
- [ ] Kontrola finalnego diff dla ATMO/ALLINONE i niezależnych METER_N.
- [ ] Ewentualne nowe testy produkcyjne tylko za odrębną zgodą operatora.

## B. Bezpieczeństwo — blokady

- [x] **Świadomie pozostawiony obecny TLS — decyzja właściciela 13.11.2026:** NIE zmieniać `ssl._create_unverified_context` w `coordinator.py` i `config_flow.py`. Połączenie jest szyfrowane, ale NIE uwierzytelnia brokera; istnieje ryzyko MITM/ujawnienia wspólnych poświadczeń. Brak niezależnego potwierdzenia CA i zgodności obecnego IP z SAN. Ograniczenie musi być jawnie opisane w README/PR/release notes. **Odstępstwo bezpieczeństwa zaakceptowane przez użytkownika, nie naprawione i nie rekomendowane jako domyślny standard bezpieczeństwa.**
- [x] **Decyzja właściciela projektu (2026-11-13): fabryczne wspólne poświadczenia MQTT pozostają bez zmian** w `const.py`; nie dodawać formularza loginu/hasła ani migracji konfiguracji. Jest to świadomie zaakceptowane ograniczenie istniejącej integracji, NIE gwarancja poufności hasła. W dokumentacji i PR nie powielać jego wartości. Zabezpieczenie sieci i uwierzytelnienie tożsamości serwera TLS pozostają osobnym zagadnieniem; TLS nadal blokuje wydanie.
- [ ] Brak sekretów i identyfikatorów prywatnych w finalnym diff, ZIP i dokumentacji.
- [ ] Uzgodnione zasady blokowania niezweryfikowanych komend GEO; testy bez fizycznego sterowania.

## C. Wydanie, HACS/Marketplace

- [ ] Uzgodniona z autorem docelowa wersja i strategia wobec upstream v0.1.2.
- [ ] Rozstrzygnięta minimalna wersja HA; obecnie `hacs.json: 2021.12.0` vs poprzedni README `>= 2023.3`.
- [x] Mechanizm budowania płaskiego `euros_os.zip` oraz testy pakowania istnieją.
- [ ] Finalny asset `euros_os.zip` z dokładnie przetestowanego commitu; brak danych wrażliwych / plików tymczasowych.
- [ ] Test instalacji/aktualizacji przez HACS/Marketplace w nieprodukcyjnym HA.
- [ ] Weryfikacja mechanizmu rollback i migracji istniejących `unique_id`.

## D. Dokumentacja użytkownika

- [x] README z opisem modelu działania GEO/EMS, ograniczeń i bezpiecznego update.
- [x] CHANGELOG (Unreleased), bez przypisywania nowego numeru release.
- [x] Procedura aktualizacji, kontroli historii i rollback.
- [ ] Weryfikacja językowa PL/EN, tłumaczeń i nazw encji; brak niepotwierdzonych deklaracji.
- [ ] Rozdzielenie krótkich materiałów dla użytkownika od prywatnych logów rozwojowych.
- [ ] Komentarze autora i odpowiednie poprawki w README / release notes.

## E. Jeden PR do autora

- [ ] Porównać z AKTUALNYM upstream main tuż przed finalizacją.
- [ ] Uzgodnić z autorem los otwartego PR #3 (NumberEntity); nie duplikować jego kodu w nakładających się PR.
- [ ] Przygotować **czystą gałąź z aktualnego upstream main**, nie z całej historii gałęzi 9.5; przenieść gotowy kod i testy w logicznych commitach.
- [ ] Powtórzyć pełne CI, statyczny skan sekretów i kontrolę zmian funkcji sterujących.
- [ ] Sporządzić krótkie podsumowanie PR: co zmieniono, jakie modele wspierane, co testowano na sprzęcie, co w symulacjach, znane ograniczenia i rollback.
- [ ] Oddzielna zgoda operatora na otwarcie końcowego PR. Po PR autor decyduje o scaleniu i numerze wydania.

## Następne 3 konkretne zadania

1. Udokumentować i przekazać autorowi świadome pozostawienie nieweryfikowanego TLS oraz fabrycznych poświadczeń; nie przedstawiać jako naprawionego bezpieczeństwa.
2. Uzgodnić bazę upstream, zakres i minimalne wersje; finalnie zamknąć HACS/Marketplace.
3. Przygotować czystą gałąź gotową do review, przetestować i zwrócić autorowi **jeden** finalny PR.

Bez instalacji nowego kodu na HA, restartu, sterowania pompą ani publicznego PR na tym etapie.
