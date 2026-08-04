# =============================================================================
# INTERFACCIA CON LOGHI, SEI PULSANTI INTERATTIVI E TESTO DINAMICO
# =============================================================================
import machine
from machine import SPI, SoftSPI, Pin
import time
import ili9341

# CONFIGURAZIONE HARDWARE (Stessi pin del tuo smartphone)
TFT_MISO, TFT_MOSI, TFT_CLK = 12, 13, 14
TFT_CS, TFT_DC, TFT_RST, TFT_BCKL = 15, 2, 4, 21

backlight = Pin(TFT_BCKL, Pin.OUT, value=1)

spi = SPI(1, baudrate=40000000, sck=Pin(TFT_CLK), mosi=Pin(TFT_MOSI), miso=Pin(TFT_MISO))
display = ili9341.Display(spi, dc=Pin(TFT_DC), cs=Pin(TFT_CS), rst=Pin(TFT_RST), width=240, height=320, rotation=0)

TP_CLK, TP_MISO, TP_MOSI, TP_CS = 25, 39, 32, Pin(33, Pin.OUT, value=1)
spi_touch = SoftSPI(baudrate=1000000, sck=Pin(TP_CLK), mosi=Pin(TP_MOSI), miso=Pin(TP_MISO))

# COLORI
NERO       = 0x0000
BIANCO     = 0xFFFF
VERDE      = 0x2E44
BLU        = 0x03EF
BLU_RL     = 0x001F
ROSSO      = 0xF000
C_GLOW_CIANO  = ili9341.color565(0, 240, 255)

# VARIABILE DI STATO (Memorizza la frase da mostrare)
frase_corrente = "Tocca un pulsante"

def leggi_touch():
    """Legge il touch screen e restituisce X e Y reali"""
    TP_CS.value(0)
    spi_touch.write(b'\x90')
    rx = spi_touch.read(2)
    spi_touch.write(b'\xD0')
    ry = spi_touch.read(2)
    TP_CS.value(1)
    gx = int.from_bytes(rx, 'big') >> 4
    gy = int.from_bytes(ry, 'big') >> 4
    if gx != 2047 and gx > 100 and gy > 100:
        px = 240 - int((1823 - gy) * 240 / 1658)
        py = int((1812 - gx) * 320 / 1682)
        return max(0, min(px, 240)), max(0, min(py, 320))
    return None

def aggiorna_testo_dinamico():
    """Aggiorna solo l'area di testo centrale senza ridisegnare l'intero display"""
    # Sovrascrive la vecchia finestra per cancellare i caratteri precedenti
    display.fill_rectangle(10, 200, 220, 50, C_GLOW_CIANO)
    # Calcola una spaziatura approssimativa per centrare il testo orizzontalmente (8 pixel per carattere)
    lunghezza_testo = len(frase_corrente) * 8
    x_centrata = max(15, 120 - (lunghezza_testo // 2))
    display.draw_text8x8(x_centrata, 221, frase_corrente, ROSSO) # Testo nero su ciano per massima leggibilità

def disegna_tutto():
    """Disegna loghi, sfondo, la griglia di 6 pulsanti e la finestra di testo"""
    PIXEL_SIZE = 4  # Ridotto a 2 per evitare che sbordi dai margini laterali (35 col * 2px = 70px)
    X_CENTRO = 120  # Centro dello schermo (240 // 2)

    # Matrice del Logo M&F (5 righe x 13 colonne)
    LOGO_MF = [
        [BLU_RL, None, None, None, BLU_RL,  None, None, BIANCO, BIANCO, None,  ROSSO, ROSSO, ROSSO],
        [BLU_RL, BLU_RL, None, BLU_RL, BLU_RL,  None, BIANCO, None, None, None,  ROSSO, None, None],
        [BLU_RL, None, BLU_RL, None, BLU_RL,  None, None, BIANCO, BIANCO, None,  ROSSO, ROSSO, None],
        [BLU_RL, None, None, None, BLU_RL,  None, BIANCO, None, BIANCO, None,  ROSSO, None, None],
        [BLU_RL, None, None, None, BLU_RL,  None, None, BIANCO, BIANCO, None,  ROSSO, None, None]
    ]

    # Matrice esatta 5 righe x 35 colonne per la scritta "AMIOISPRO"
    MATRICE_AMIOISPRO = [
        [None,BIANCO,BIANCO,BIANCO,None, BIANCO,None,None,None,BIANCO,None, BIANCO,None, BIANCO,BIANCO,BIANCO,None, BIANCO,None,  BIANCO,BIANCO,BIANCO,None, BIANCO,BIANCO,BIANCO,None, BIANCO,BIANCO,BIANCO,None, BIANCO,BIANCO,BIANCO,None],
        [None,BIANCO,None,BIANCO,None, BIANCO,BIANCO,None,BIANCO,BIANCO,None, BIANCO,None, BIANCO,None,BIANCO,None, BIANCO,None,  BIANCO,None,None,None, BIANCO,None,BIANCO,None, BIANCO,None,BIANCO,None, BIANCO,None,BIANCO,None],
        [None,BIANCO,BIANCO,BIANCO,None, BIANCO,None,BIANCO,None,BIANCO,None, BIANCO,None, BIANCO,None,BIANCO,None, BIANCO,None,  BIANCO,BIANCO,BIANCO,None, BIANCO,BIANCO,BIANCO,None, BIANCO,BIANCO,BIANCO,None, BIANCO,None,BIANCO,None],
        [None,BIANCO,None,BIANCO,None, BIANCO,None,None,None,BIANCO,None, BIANCO,None, BIANCO,None,BIANCO,None, BIANCO,None, None,None,BIANCO,None, BIANCO,None,None,None, BIANCO,BIANCO,None,None, BIANCO,None,BIANCO,None],
        [None,BIANCO,None,BIANCO,None, BIANCO,None,None,None,BIANCO,None, BIANCO,None, BIANCO,BIANCO,BIANCO,None, BIANCO,None, BIANCO,BIANCO,BIANCO,None, BIANCO,None,None,None, BIANCO,None,BIANCO,None, BIANCO,BIANCO,BIANCO,None]
    ]

    # Pulisce lo schermo con lo sfondo BLU
    if hasattr(display, 'clear'): display.clear(BLU)
    else: display.fill_rectangle(0, 0, 240, 320, BLU)

    # 1. DISEGNA LOGO M&F (Y=10)
    y_mf = 10
    x_mf = X_CENTRO - ((13 * PIXEL_SIZE) // 2)
    for r in range(5):
        for c in range(13):
            colore = LOGO_MF[r][c]
            if colore is not None:
                display.fill_rectangle(x_mf + (c * PIXEL_SIZE), y_mf + (r * PIXEL_SIZE), PIXEL_SIZE, PIXEL_SIZE, colore)

    # 2. DISEGNA SCRITTA "AMIOISPRO" CENTRATA (Y=35)
    y_testo = 35
    x_testo_start = X_CENTRO - ((35 * PIXEL_SIZE) // 2)
    for r in range(5):
        for c in range(35):
            colore = MATRICE_AMIOISPRO[r][c]
            if colore is not None:
                display.fill_rectangle(x_testo_start + (c * PIXEL_SIZE), y_testo + (r * PIXEL_SIZE), PIXEL_SIZE, PIXEL_SIZE, colore)

    # 3. DISEGNA I PULSANTI 
    # --- RIGA 1 ---
    display.fill_rectangle(20, 65, 90, 30, ROSSO)
    display.draw_text8x8(25, 76, "---INSERIRE QUI IL NOME DELLA APP---", BIANCO)  
    
    display.fill_rectangle(130, 65, 90, 30, ROSSO)
    display.draw_text8x8(135, 76, "---INSERIRE QUI IL NOME DELLA APP---", BIANCO)
    
    # --- RIGA 2 ---
    display.fill_rectangle(20, 105, 90, 30, ROSSO)
    display.draw_text8x8(25, 116, "---INSERIRE QUI IL NOME DELLA APP---", BIANCO)
    
    display.fill_rectangle(130, 105, 90, 30, ROSSO)
    display.draw_text8x8(135, 116, "---INSERIRE QUI IL NOME DELLA APP---", BIANCO)

    # --- RIGA 3 ---
    display.fill_rectangle(20, 145, 90, 30, ROSSO)
    display.draw_text8x8(25, 156, "---INSERIRE QUI IL NOME DELLA APP---", BIANCO)
    
    display.fill_rectangle(130, 145, 90, 30, ROSSO)
    display.draw_text8x8(135, 156, "---INSERIRE QUI IL NOME DELLA APP---", BIANCO)
    
    # Ridisegna l'area di testo dinamica aggiornata
    aggiorna_testo_dinamico()

# AVVIO PRIMO DISEGNO
disegna_tutto()
ultimo_tocco = 0

# LOOP PRINCIPALE
while True:
    coordinate = leggi_touch()
    if coordinate is not None:
        tempo_attuale = time.ticks_ms()
        if time.ticks_diff(tempo_attuale, ultimo_tocco) > 250:
            x, y = coordinate
            
            if 20 <= x <= 110:
                if 65 <= y <= 95:
                    frase_corrente = "QUI INSERIRE LA FRASE DA VISUALIZZARE QUANDO LA APP VIENE APERTA"
                    aggiorna_testo_dinamico()
                    time.sleep(1.5)
                    import QUI_METTERE_IL_NOME_DEL_FILE_DELLA_APP_SENZA_.py
                
                elif 105 <= y <= 135:
                    frase_corrente = "QUI INSERIRE LA FRASE DA VISUALIZZARE QUANDO LA APP VIENE APERTA"
                    aggiorna_testo_dinamico()
                    time.sleep(1.5)
                    import QUI_METTERE_IL_NOME_DEL_FILE_DELLA_APP_SENZA_.py
                    
                elif 145 <= y <= 175:
                    frase_corrente = "QUI INSERIRE LA FRASE DA VISUALIZZARE QUANDO LA APP VIENE APERTA"
                    aggiorna_testo_dinamico()
                    time.sleep(1.5)
                    import QUI_METTERE_IL_NOME_DEL_FILE_DELLA_APP_SENZA_.py

            elif 130 <= x <= 220:
                if 65 <= y <= 95:
                    frase_corrente = "QUI INSERIRE LA FRASE DA VISUALIZZARE QUANDO LA APP VIENE APERTA"
                    aggiorna_testo_dinamico()
                    time.sleep(1.5)
                    import QUI_METTERE_IL_NOME_DEL_FILE_DELLA_APP_SENZA_.py
                
                elif 105 <= y <= 135:
                    frase_corrente = "QUI INSERIRE LA FRASE DA VISUALIZZARE QUANDO LA APP VIENE APERTA"
                    aggiorna_testo_dinamico()
                    time.sleep(1.5)
                    import QUI_METTERE_IL_NOME_DEL_FILE_DELLA_APP_SENZA_.py
                
                elif 145 <= y <= 175:
                    frase_corrente = "QUI INSERIRE LA FRASE DA VISUALIZZARE QUANDO LA APP VIENE APERTA"
                    aggiorna_testo_dinamico()
                    time.sleep(1.5)
					import QUI_METTERE_IL_NOME_DEL_FILE_DELLA_APP_SENZA_.py
                
            ultimo_tocco = tempo_attuale
            while leggi_touch() is not None:
                time.sleep_ms(10)
                
    time.sleep_ms(10)

