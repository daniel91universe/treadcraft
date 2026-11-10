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

Le transizioni e il controllo del tapis roulant restano da verificare con l'hardware collegato.
