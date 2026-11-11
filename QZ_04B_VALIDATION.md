# TreadCraft v0.4.0 · Validazione QZ-04B

L'utente ha verificato la riconnessione dalla versione Python locale di TreadCraft su Windows con QZ Android **2.20.29**, sulla rete Wi-Fi locale senza Internet e senza tapis roulant.

| Prova manuale | Esito |
| --- | --- |
| Riconnessione dopo il riavvio di TreadCraft | L'ultimo indirizzo verificato viene riproposto e la riconnessione riesce. |
| Indirizzo obsoleto | Il tentativo fallisce in modo gestito. L'ultimo indirizzo verificato rimane disponibile e la verifica dell'URL corrente riesce. |
| Annullamento | La verifica viene annullata e l'indirizzo salvato resta invariato. |

## Prova finale su main

L'utente ha ripetuto la prova su Windows dal commit di merge `0116844` (PR #17), con QZ Android **2.20.29**, tramite Wi-Fi locale senza Internet e senza tapis roulant.

- La riconnessione è riuscita dopo il riavvio di TreadCraft.
- L'allenamento **3×3000 m** inviato a QZ contiene **8 righe**. Le righe **2, 4 e 6** conservano ciascuna la distanza di **3 km**.

## Prova del candidato portable v0.4.0 sul tablet

L'11 novembre 2026 l'utente ha confermato l'esito positivo della prova su un tablet Windows senza Python installato, con QZ Android **2.20.29**, tramite Wi-Fi locale senza Internet e senza tapis roulant.

- Candidato Windows x64 onedir dal commit `cd978aa3a3e6752e16724ad17f6d6a13c0a0c5d5`.
- ZIP provato `TreadCraft-v0.4.0-Windows-x64-cd978aa.zip`.
- SHA-256 registrato alla creazione dello ZIP `7dd642467dac7fa0f49bd887890b423f157b0ccc6b45d309235352c23e835da0`.
- Avvio e riconnessione riusciti.
- Invio del **3×3000 m** riuscito, con **8 righe** e **tre ripetute da 3 km** conservate in QZ.

La suite sulla copia del sorgente usata per la build aveva superato **95 test**. La prova sul tablet è stata eseguita dall'utente con il portable.

Le transizioni e il controllo del tapis roulant restano da verificare con l'hardware collegato.
