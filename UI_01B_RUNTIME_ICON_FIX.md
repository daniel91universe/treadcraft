# TreadCraft — UI-01B Runtime Icon Fix

Data 11 novembre 2026. Esperimento locale su branch
`codex/ui-01b-runtime-icons`, base `7cd2dfc`.
Il progetto Wi-Fi resta in attesa.

## Diagnosi prima della modifica

Misure native su Windows 10, Python 3.12.10 e Tk 8.6.15, senza modificare
impostazioni Windows o DPI awareness. Sono stati interrogati
`GetWindowDpiAwarenessContext`, `GetAwarenessFromDpiAwarenessContext`,
`GetDpiForWindow`, `GetScaleFactorForMonitor`, `WM_GETICON`,
`GetClassLongPtrW` e `GetIconInfo`. I bitmap temporanei restituiti da
`GetIconInfo` sono stati liberati.

| Misura | Python originale | Portable pubblico v0.4.0 |
| --- | --- | --- |
| Awareness della finestra | 0, DPI-unaware | 0, DPI-unaware |
| DPI restituito dalla finestra | 96 | 96 |
| Scala del monitor | 150% | 150% |
| WM_GETICON, ICON_SMALL | 0 | 0 |
| WM_GETICON, ICON_BIG | 0 | 0 |
| Icona piccola di classe | 16×16 | 16×16 |
| Icona grande di classe | 32×32 | 32×32 |

HICON osservati nella misura Python originale, piccoli/grandi di classe,
rispettivamente `1378615` e `65733987`. Nel portable pubblico erano
`7342613` e `51317511`. Sono handle validi solo per quelle esecuzioni.

La chiamata a `iconbitmap(default=...)` riesce. In questa esecuzione le
icone sono di classe e non risultano HICON specifici di finestra. Il
conflitto ipotizzato nell'audit UI-01A non è stato quindi dimostrato in
questa configurazione. È invece verificato il disallineamento fra scala
del monitor e dimensioni delle icone di classe.

La condizione precedente basata su `winfo_fpixels("1i") <= 97` attiva il
ritocco da 16 px anche qui, perché Tk vede circa 95,95 DPI sebbene il
monitor sia al 150%. Il solo DPI virtualizzato non descrive dunque la
dimensione fisica richiesta per l'icona.

Le metriche Windows interrogate a 144 DPI richiedono 24×24 per l'icona
piccola e 48×48 per quella grande. Questo misura le metriche disponibili,
non traccia ogni richiesta di Explorer o del compositor.

## Correzione

- `app.py` elimina il precedente ritocco con `SetClassLongPtrW` e applica
  la stessa gestione alla root e all'anteprima QZ.
- `windows_icons.py` assegna ICON_SMALL e ICON_BIG al wrapper nativo
  tramite WM_SETICON, caricando dall'ICO principale alle dimensioni delle
  metriche Windows.
- Per una finestra DPI-unaware, GetDpiForWindow restituisce 96. In questo
  caso viene letta la scala del monitor per calcolare le metriche delle
  sole icone. Non viene chiamata alcuna API che modifichi la DPI awareness.
- Gli eventi Map e Configure ricontrollano wrapper e dimensioni. Se sono
  invariati non vengono caricati nuovi handle.
- Ogni finestra possiede i propri HICON. Al cambio dimensioni o alla
  distruzione vengono liberati solo gli handle creati dal componente.
  Quando opportuno vengono ripristinati gli handle precedenti, mai
  distrutti dal componente. Se un caricamento parziale fallisce vengono
  mantenute le icone correnti.

Nessun asset Brand v1.0 o parametro di layout è stato modificato.

## Diagnosi dopo la modifica

| Misura | Python UI-01B | Portable UI-01B |
| --- | --- | --- |
| WM_GETICON, ICON_SMALL | 24×24, HICON 723263 | 24×24, HICON 198947 |
| WM_GETICON, ICON_BIG | 48×48, HICON 96799267 | 48×48, HICON 13568101 |
| Icone di classe | 16×16 e 32×32 | 16×16 e 32×32 |
| Awareness e impostazioni DPI | Invariate | Awareness 0, finestra 96 DPI |

Le misure sono state eseguite sul monitor al 150%. Sono stati caricati e
misurati anche HICON da 16, 20, 24, 28, 32, 40, 48 e 56 px tramite
LoadImageW. Questo verifica le dimensioni prodotte dal caricamento, ma non
costituisce una prova visiva su Windows configurato a tutte quelle scale.

## Test e portable sperimentale

- Suite completa superata: **100 test**, inclusi cinque nuovi test su
  dimensioni, sostituzione e rilascio degli handle, fallimento parziale,
  annullamento dei callback e separazione degli eventi delle finestre.
- Dopo il riscaldamento, 50 aperture e chiusure di finestre secondarie:
  risorse GDI 56 → 56, USER 90 → 89. Nessun incremento osservato.
  Una seconda prova di 50 cicli ha confermato GDI 56 → 56 e USER 90 → 90.
- Build onedir locale con Python 3.12.10 x64, PyInstaller 6.22.3 e
  websockets 15.0.1. Anche la copia sorgente della build supera 100 test.
- Avvio del portable sperimentale e misure native riusciti.
- Le sei immagini ICO incorporate nell'EXE e tutti gli asset Brand
  coincidono con quelli della v0.4.0. Il logo dell'eseguibile conserva
  quindi le stesse risorse grafiche.

Il pacchetto `TreadCraft-UI-01B-Windows-x64.zip` contiene la base
`7cd2dfc` con le modifiche locali ad app.py e il nuovo modulo.
Non corrisponde a un nuovo commit o a una release.

SHA-256:

```text
eedf8ed116aac96be0c4c32d4a8c72a97bef5b9f50e96d670ca4a558f82fb487
```

## Limiti e problemi residui

La cattura della finestra del portable ha restituito
`window capture timed out: timed out waiting on channel`, anche dopo il
recupero della finestra e un secondo tentativo. Non è stato possibile
certificare visivamente titolo, taskbar e Alt+Tab.

L'utente ha provato UI-01B sul PC al 175% e sul tablet senza Python,
confermando icone più nitide nella barra del titolo, nella taskbar e in
Alt+Tab. Ha poi precisato che l'icona ancora sfocata appartiene al messaggio
**Workout Loaded**. L'icona della finestra di selezione del file è nitida.

Un controllo aggiuntivo sul normale flusso di apertura dell'anteprima QZ,
nell'ambiente disponibile al 150%, conferma che i due HICON della finestra
corrispondono a quelli assegnati dal gestore UI-01B. Questo controllo non
dimostra la qualità visiva al 175% e non copre il dialogo nativo di salvataggio.

Le icone caricate
alle dimensioni intermedie possono ancora essere ricampionate da Windows,
perché l'ICO originale non contiene tutti i frame intermedi. Il marchio
conserva inoltre molti dettagli alle dimensioni più piccole.

La DPI virtualization complessiva del processo resta attiva. La correzione
è limitata alle icone e non può garantire di eliminare ogni ricampionamento
applicato dalla shell o dal compositor. La scelta della taskbar può anche
dipendere da collegamenti fissati e cache, che non sono stati modificati.

Il cambio reale fra monitor e il confronto visivo a 100%, 125% e 150%
restano da provare. La scala del tablet non è stata comunicata.

## Prova manuale sul PC e sul tablet

1. Estrarre lo ZIP UI-01B in una cartella distinta dalla v0.4.0. Aprire
   TreadCraft.exe mantenendo la cartella _internal accanto all'eseguibile.
2. Confrontare con la v0.4.0 barra del titolo, taskbar e Alt+Tab.
   Controllare anche l'icona dell'EXE in Esplora file.
3. Aprire il 3×3000 m e l'anteprima Export to QZ XML. Controllare l'icona
   della finestra secondaria e ripetere apertura e chiusura.
4. Ridurre a icona e ripristinare l'app, quindi chiuderla e riaprirla.
5. Sul PC verificare prima il 175% abituale. Confrontare anche 100%, 125%
   e 150% se disponibili, riaprendo l'app dopo il cambio. Se sono presenti
   più monitor, provare il passaggio tra monitor.
6. Ripetere sul tablet senza Python usando lo stesso ZIP. Per la versione
   Python del PC usare il consueto avvio locale con la dipendenza WebSocket.

Non cancellare la cache delle icone durante il primo confronto. Annotare
se si usa un collegamento fissato o l'avvio diretto.

Stato prima della conferma visiva r2: modifiche e ZIP solo locali, in attesa della verifica
visiva dell'utente. Nessun commit, PR, merge o release.

## Ritocco r2 — messaggio Workout Loaded

Il messaggio di conferma usa il dialogo nativo di Tk. Il sorgente ufficiale
Tk 8.6.15 mostra che TkWinDialog preleva le icone dalla cache interna
tramite TkWinGetIcon e le assegna al MessageBox. Le icone runtime impostate
sul wrapper della root non aggiornano questa cache.

Riferimento al sorgente:
[tkWinDialog.c](https://github.com/tcltk/tk/blob/core-8-6-15/win/tkWinDialog.c).

La misura nativa ha confermato che, prima del ritocco, il messaggio usa
HICON differenti da quelli della root. La correzione applica al messaggio
Workout Loaded i due HICON runtime della root, alla sua attivazione,
tramite un hook CBT limitato al thread corrente e alla durata del dialogo.
Sono filtrati il proprietario e la classe nativa #32770. L'hook viene
rimosso in finally. Gli HICON sono presi in prestito dalla root e non
vengono duplicati o distrutti dal messaggio.

Una prova separata ha misurato i due HICON del dialogo corretti e identici
a quelli della root, verificando anche la restituzione dalla chiamata al
messaggio e la chiusura. I primi tentativi di chiusura automatica del
dialogo si sono bloccati; la prova conclusiva da processo separato,
usando WM_CLOSE, è riuscita. La successiva conferma visiva dell'utente è
registrata sotto.

Il ritocco è limitato a Workout Loaded. Gli altri messaggi nativi non sono
stati estesi automaticamente. Nessun asset è stato modificato.

La suite completa ora supera **101 test**, compreso il nuovo test sul
riutilizzo degli HICON e sulla conservazione del risultato del messaggio.
Il pacchetto per la nuova prova è
`TreadCraft-UI-01B-r2-Windows-x64.zip`.

La build r2 ha superato gli stessi 101 test. SHA-256 dello ZIP:

```text
22776ee34eecb7ac89e718d2045d865c27be562f2f5ef398b348db11212ab2a1
```

Per provarlo sul PC al 175% e sul tablet senza Python, estrarre r2 in una
nuova cartella e usare Open Workout per aprire il 3×3000 m. Controllare
l'icona del messaggio Workout Loaded e chiuderlo con OK. Confermare che il
caricamento dell'allenamento e le icone principali restino corretti.

## Esito della prova visiva r2

L'11 novembre 2026 l'utente ha confermato l'esito positivo della prova di
`TreadCraft-UI-01B-r2-Windows-x64.zip` sul **PC Windows al 175%** e sul
**tablet Windows senza Python**: anche l'icona del messaggio
**Workout Loaded è nitida**.

Questa conferma completa la verifica visiva del ritocco r2. Restano
documentati gli esiti positivi della precedente prova su barra del titolo,
taskbar e Alt+Tab. La suite e la build r2 avevano superato **101 test**;
non sono stati rieseguiti per questo aggiornamento del solo report.

Le prove alle altre scale e il cambio fra monitor rimangono fuori da
questa conferma. Il ritocco agli altri messaggi nativi non è stato esteso.

Stato attuale: esito visivo r2 positivo, modifiche e pacchetti solo locali.
Nessun commit o PR creato.
