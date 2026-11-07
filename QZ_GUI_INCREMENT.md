# Incremento 4 · Esportazione QZ dalla GUI

La Fase A ha verificato il commit locale 08bec8db8886fe76833ae4b769c898889ed02f70 contro main sul repository privato. La suite iniziale ha superato 53 test. L'esportatore XML, il profilo Commercial LE e i dati per il riepilogo erano già disponibili.

Il pulsante **Export to QZ XML** genera l'XML con l'esportatore esistente. Mostra gli errori bloccanti prima della scelta del file. L'anteprima distingue il tempo delle righe temporali dalle stime delle righe a distanza e mostra gli avvisi del profilo. Dopo la conferma apre il dialogo per la destinazione.

Il salvataggio accetta percorsi XML e chiede conferma per una destinazione esistente. Scrive e sincronizza un temporaneo nella directory di destinazione. Usa la sostituzione atomica per le sovrascritture confermate e un hard link per pubblicare un file nuovo senza sovrascrivere un file creato nel frattempo. Un file system privo di supporto agli hard link può rifiutare la creazione e la GUI mostra l'errore I/O.

| File | Modifica |
|---|---|
| app.py | Pulsante, callback, anteprima e scrittura sicura |
| test_qz_gui.py | Otto test su callback e scrittura |
| QZ_GUI_INCREMENT.md | Resoconto dell'incremento |

Tutti i 61 test sono passati con Python 3.15 e il comando python -B -m unittest. I mock coprono l'annullamento, il rifiuto della discesa, la conferma di sostituzione e gli errori di accesso. Le prove su file temporanei controllano contenuto XML, integrità del JSON, ripetute a distanza e conflitto con una creazione concorrente. La verifica visiva della GUI Windows e le prove sul tapis restano aperte.

Il branch feature/qz-export-ui parte da 08bec8d. Il commit che contiene questo report raccoglie la modifica proposta per la pull request verso main. Il merge è soggetto ad autorizzazione separata.

Il prossimo passo di verifica è importare dalla GUI un allenamento misto nella build QZ Android effettiva e controllare separatamente anteprima e transizioni sul tapis quando disponibile.

Il commit di implementazione è f573d88. La [pull request #7](https://github.com/daniel91universe/treadcraft/pull/7) è aperta in bozza verso main.
