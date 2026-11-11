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

## Verifica dello ZIP pubblico v0.4.0

L'11 novembre 2026 è stato verificato lo ZIP pubblico `TreadCraft-v0.4.0-Windows-x64-cd978aa.zip`. Il checksum SHA-256 coincide con quello del candidato provato sul tablet e l'eseguibile estratto si avvia su Windows.

La cattura della finestra del portable pubblico è fallita, impedendo la prova dei pulsanti di riconnessione e invio. È stata quindi eseguita una verifica separata con il sorgente esatto del commit di build `cd978aa` e l'esempio **3×3000 m** contenuto nello ZIP pubblico.

- QZ Android **2.20.29** ha risposto al comando di riconoscimento sul nuovo indirizzo locale e ha confermato il salvataggio del programma con **8 righe**.
- Il programma inviato si chiama `3x3000m-public-v0-4-0-verification-15d5dce9bb8649d480caa170dfe0ffd4`.
- L'utente ha verificato in QZ **8 righe** e, nell'XML ricevuto, `distance="3"` alle righe **2, 4 e 6**.

La verifica del trasferimento e dell'integrità del programma ricevuto è positiva. **La prova dei pulsanti del portable pubblico resta incompleta**. La precedente prova positiva del candidato sul tablet rimane documentata separatamente.

Le transizioni e il controllo del tapis roulant restano da verificare con l'hardware collegato.
