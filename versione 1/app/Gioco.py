import machine
from machine import SPI, SoftSPI, Pin
import time
import ili9341
import math
import random
import network
import espnow

# =============================================================================
# 1. CONFIGURAZIONE WIRELESS MULTIPLAYER (ESP-NOW)
# =============================================================================
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

e = espnow.ESPNow()
e.active(True)

BROADCAST_MAC = b'\xff\xff\xff\xff\xff\xff'
e.add_peer(BROADCAST_MAC)

# CONFIGURAZIONE IDENTITÀ DELLA SCHEDA:
# Sulla prima scheda lascia: ID_GIOCATORE = 1
# Sulla seconda scheda cambia in: ID_GIOCATORE = 2
ID_GIOCATORE = 1 

p2_x, p2_y, p2_a = 2.5, 2.5, 0.0
p2_connesso = False
ultimo_pacchetto_p2 = time.ticks_ms()

# =============================================================================
# 2. CONFIGURAZIONE HARDWARE (Display ILI9341 e Touch SPI)
# =============================================================================
TFT_MISO, TFT_MOSI, TFT_CLK = 12, 13, 14
TFT_CS, TFT_DC, TFT_RST, TFT_BCKL = 15, 2, 4, 21

backlight = Pin(TFT_BCKL, Pin.OUT, value=1)

spi = SPI(1, baudrate=40000000, sck=Pin(TFT_CLK), mosi=Pin(TFT_MOSI), miso=Pin(TFT_MISO))
display = ili9341.Display(spi, dc=Pin(TFT_DC), cs=Pin(TFT_CS), rst=Pin(TFT_RST), width=320, height=240, rotation=90)

TP_CLK, TP_MISO, TP_MOSI, TP_CS = 25, 39, 32, Pin(33, Pin.OUT, value=1)
spi_touch = SoftSPI(baudrate=1000000, sck=Pin(TP_CLK), mosi=Pin(TP_MOSI), miso=Pin(TP_MISO))

# =============================================================================
# 3. CONFIGURAZIONE LABIRINTO (Griglia di Gioco)
# =============================================================================
MAP_SIZE = 16
RIGA_00 = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
RIGA_01 = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1]
RIGA_02 = [1, 0, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1]
RIGA_03 = [1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1]
RIGA_04 = [1, 0, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1]
RIGA_05 = [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1]
RIGA_06 = [1, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1]
RIGA_07 = [1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1]
RIGA_08 = [1, 1, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1]
RIGA_09 = [1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1]
RIGA_10 = [1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1]
RIGA_11 = [1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1]
RIGA_12 = [1, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1]
RIGA_13 = [1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1]
RIGA_14 = [1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1]
RIGA_15 = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]

WORLD_MAP = [
    RIGA_00, RIGA_01, RIGA_02, RIGA_03,
    RIGA_04, RIGA_05, RIGA_06, RIGA_07,
    RIGA_08, RIGA_09, RIGA_10, RIGA_11,
    RIGA_12, RIGA_13, RIGA_14, RIGA_15
]

VIEW_W = 320
VIEW_H = 180
RES_STEP = 4  

# Palette Atmosfera Backrooms
SOFFITTO    = 0x4228  
TERRENO     = 0x4228  
MURO        = 0xDE68  
MURO_OMBRA  = 0x6B22  
NERO        = 0x0000
ROSSO_SANGUE= 0x9000
VERDE_BAT   = 0x07E0
BIANCO      = 0xFFFF
COL_MINIMAP_MURO  = 0x8404  
COL_MINIMAP_VUOTO = 0x18C3  
COL_MINIMAP_MOSTRO= 0xF800  
CELESTE_ONDA      = 0x07FF  
COL_MINIMAP_P2    = 0x001F  # Blu per il secondo giocatore sulla mappa

# STATO GIOCATORE
if ID_GIOCATORE == 1:
    px, py = 1.5, 1.5
else:
    px, py = 4.5, 1.5
    
pa = 0.0          
FOV = math.pi / 2.2
torcia_livello = 100.0

# CONTATORE FPS
ultimo_calcolo_fps = time.ticks_ms()
conteggio_frame = 0
fps_correnti = 0

# STATO MOSTRO
mx, my = 14.5, 14.5  
game_over = False

# STATO MODALITÀ SPECIALI
mappa_schermo_intero = False
mostro_cliccato_mappa = False
god_mode = False  

# =============================================================================
# 4. PRECOMPILAZIONE LOOKUP TABLES (LUT)
# =============================================================================
RAY_ANGLES = []
COS_ANGLES = []
for i in range(0, VIEW_W, RES_STEP):
    angolo_relativo = (- FOV / 2) + (i / VIEW_W) * FOV
    RAY_ANGLES.append(angolo_relativo)
    COS_ANGLES.append(math.cos(angolo_relativo))

# =============================================================================
# 5. FUNZIONI DI TRASMISSIONE E RICEZIONE WIRELESS (ESP-NOW)
# =============================================================================
def invia_posizione_wireless():
    """Invia le proprie coordinate convertite in stringa compressa"""
    msg = f"{ID_GIOCATORE},{px:.2f},{py:.2f},{pa:.2f}"
    try:
        e.send(BROADCAST_MAC, msg)
    except:
        pass

def controlla_ricezione_wireless():
    """Analizza il buffer asincrono radio per catturare i movimenti del P2"""
    global p2_x, p2_y, p2_a, p2_connesso, ultimo_pacchetto_p2
    
    mac, msg = e.recv(0) 
    if msg:
        try:
            dati = msg.decode().split(',')
            id_mittente = int(dati[0]) # Estrae l'ID stringa e lo converte in int
            
            if id_mittente != ID_GIOCATORE:
                p2_x = float(dati[1]) # Coordinata X
                p2_y = float(dati[2]) # Coordinata Y
                p2_a = float(dati[3]) # Angolo visivo

        except:
            pass
            
    if p2_connesso and time.ticks_diff(time.ticks_ms(), ultimo_pacchetto_p2) > 2000:
        p2_connesso = False

# =============================================================================
# 6. GESTIONE INPUT TOUCH E POSIZIONAMENTO
# =============================================================================
def leggi_touch():
    TP_CS.value(0)
    spi_touch.write(b'\x90')
    rx = spi_touch.read(2)
    spi_touch.write(b'\xD0')
    ry = spi_touch.read(2)
    TP_CS.value(1)
    gx = int.from_bytes(rx, 'big') >> 4
    gy = int.from_bytes(ry, 'big') >> 4
    if gx != 2047 and gx > 100 and gy > 100:
        tx = int((1812 - gx) * 320 / 1682)
        ty = int((1823 - gy) * 240 / 1658)
        return max(0, min(tx, 320)), max(0, min(ty, 240))
    return None

def posiziona_mostro_casuale():
    global mx, my
    tentativi = 0
    while tentativi < 50:
        rx = random.randint(1, MAP_SIZE - 2) + 0.5
        ry = random.randint(1, MAP_SIZE - 2) + 0.5
        if WORLD_MAP[int(ry)][int(rx)] == 0:
            dist_sicurezza = math.sqrt((rx - px)**2 + (ry - py)**2)
            if dist_sicurezza > 4.0:
                mx, my = rx, ry
                return
        tentativi += 1
    mx, my = 14.5, 14.5

posiziona_mostro_casuale()

# =============================================================================
# 7. GESTIONE BATTERIE (Respawn)
# =============================================================================
batterie = []
batterie_da_rigenerare = []

def genera_singola_batteria():
    tentativi = 0
    while tentativi < 30:
        bx = random.randint(1, MAP_SIZE - 2) + 0.5
        by = random.randint(1, MAP_SIZE - 2) + 0.5
        if WORLD_MAP[int(by)][int(bx)] == 0 and (abs(bx - px) > 2 or abs(by - py) > 2):
            if (bx, by) not in batterie:
                batterie.append((bx, by))
                return True
        tentativi += 1
    return False

def inizializza_batterie():
    global batterie, batterie_da_rigenerare
    batterie = []
    batterie_da_rigenerare = []
    for _ in range(3):
        genera_singola_batteria()

def controlla_raccolta_batterie():
    global torcia_livello, batterie, batterie_da_rigenerare
    if god_mode: return  
    tempo_attuale = time.ticks_ms()
    for b in batterie[:]:
        # --- FIX: Usiamo b[0] per la coordinata X e b[1] per la coordinata Y della tupla ---
        dist = math.sqrt((b[0] - px)**2 + (b[1] - py)**2)
        # ----------------------------------------------------------------------------------
        if dist < 0.5:
            torcia_livello = min(100.0, torcia_livello + 40.0)
            batterie.remove(b)
            batterie_da_rigenerare.append(time.ticks_add(tempo_attuale, 15000))
            display.fill_rectangle(0, 0, 320, 240, VERDE_BAT)
            time.sleep_ms(40)
            disegna_controlli_joystick()


def aggiorna_rigenerazione_batterie():
    global batterie_da_rigenerare
    tempo_attuale = time.ticks_ms()
    for tempo_respawn in batterie_da_rigenerare[:]:
        if time.ticks_diff(tempo_respawn, tempo_attuale) <= 0:
            if genera_singola_batteria():
                batterie_da_rigenerare.remove(tempo_respawn)

inizializza_batterie()

# =============================================================================
# 8. INTERFACCIA GRAFICA (GUI) E STRUMENTI DI DISEGNO
# =============================================================================
def disegna_controlli_joystick():
    display.fill_rectangle(0, VIEW_H, 320, 2, ROSSO_SANGUE if not god_mode else CELESTE_ONDA)
    display.fill_rectangle(0, VIEW_H + 2, 320, 58, NERO)
    display.fill_rectangle(10, 188, 65, 45, 0x2104)
    display.draw_text8x8(24, 206, "<-", BIANCO)
    display.fill_rectangle(85, 188, 65, 45, 0x1A03)
    display.draw_text8x8(105, 206, "/\\", BIANCO)
    display.fill_rectangle(160, 188, 65, 45, 0x2104)
    display.draw_text8x8(182, 206, "->", BIANCO)
    display.fill_rectangle(245, 188, 65, 45, 0x3000)
    display.draw_text8x8(268, 206, "\\/", BIANCO)

def disegna_interfaccia_torcia():
    display.draw_text8x8(8, 8, "TORCIA:", BIANCO)
    display.fill_rectangle(65, 8, 52, 9, BIANCO)
    display.fill_rectangle(66, 9, 50, 7, NERO)
    lunghezza = int(torcia_livello / 2)
    if lunghezza > 0:
        colore_barra = CELESTE_ONDA if god_mode else (VERDE_BAT if torcia_livello > 25 else ROSSO_SANGUE)
        display.fill_rectangle(66, 9, lunghezza, 7, colore_barra)
    if god_mode:
        display.draw_text8x8(124, 8, "GOD ACTIVE", CELESTE_ONDA)

def renderizza_mappa_schermo_intero():
    display.fill_rectangle(0, 0, 320, 240, NERO)
    ox, oy = 64, 24
    dim = 12
    for y_idx in range(MAP_SIZE):
        for x_idx in range(MAP_SIZE):
            col = COL_MINIMAP_MURO if WORLD_MAP[y_idx][x_idx] == 1 else COL_MINIMAP_VUOTO
            display.fill_rectangle(ox + (x_idx * dim), oy + (y_idx * dim), dim, dim, col)
    for b in batterie:
        # Usa b[0] per la coordinata X e b[1] per la coordinata Y
        display.fill_rectangle(ox + int(b[0] * dim) + 4, oy + int(b[1] * dim) + 4, 4, 4, VERDE_BAT)

    display.fill_rectangle(ox + int(mx * dim) + 3, oy + int(my * dim) + 3, 6, 6, COL_MINIMAP_MOSTRO)
    if p2_connesso:
        display.fill_rectangle(ox + int(p2_x * dim) + 3, oy + int(p2_y * dim) + 3, 6, 6, COL_MINIMAP_P2)
    display.fill_rectangle(ox + int(px * dim) + 3, oy + int(py * dim) + 3, 6, 6, BIANCO)
    display.fill_rectangle(8, 205, 48, 28, 0x2104)
    display.draw_text8x8(16, 215, "X", BIANCO)
    if mostro_cliccato_mappa:
        col_tasto = CELESTE_ONDA if god_mode else ROSSO_SANGUE
        text_tasto = "GOD: ON" if god_mode else "GOD MODE"
        display.fill_rectangle(210, 205, 102, 28, col_tasto)
        display.draw_text8x8(220, 215, text_tasto, BIANCO)

# =============================================================================
# 9. LOGICA DELLE ABILITÀ E NEMICI
# =============================================================================
def spara_onda_energetica():
    for _ in range(3):
        display.fill_rectangle(0, 0, 320, 180, BIANCO)
        time.sleep_ms(30)
        display.fill_rectangle(0, 0, 320, 180, CELESTE_ONDA)
        time.sleep_ms(30)
    posiziona_mostro_casuale()
    render_prospettiva_3d()

def muovi_mostro():
    global mx, my
    if random.randint(1, 3) != 1: return
    start_x, start_y = int(mx), int(my)
    target_x, target_y = int(px), int(py)
    if start_x == target_x and start_y == target_y:
        mx += 0.3 if px > mx else -0.3 if px < mx else 0
        my += 0.3 if py > my else -0.3 if py < my else 0
        return
    queue = [(start_x, start_y, [])]
    visitati = {(start_x, start_y)}
    percorso_trovato = None
    direzioni = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    while queue:
        cx, cy, path = queue.pop(0)
        if cx == target_x and cy == target_y:
            percorso_trovato = path
            break
        for dx, dy in direzioni:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < MAP_SIZE and 0 <= ny < MAP_SIZE:
                # Controlla che la riga e la colonna esistano e siano valide
                if WORLD_MAP[ny][nx] == 0 and (nx, ny) not in visitati:
                    visitati.add((nx, ny))
                    queue.append((nx, ny, path + [(nx, ny)]))
                    
    # --- FIX SICUREZZA PACCHETTO COORD ---
    if percorso_trovato and len(percorso_trovato) > 0:
        try:
            # Estraiamo il primo passo in modo esplicito per evitare l'errore di unpack
            passo = percorso_trovato[0]
            prossimo_passo_x = passo[0]
            prossimo_passo_y = passo[1]
            
            target_dec_x = prossimo_passo_x + 0.2
            target_dec_y = prossimo_passo_y + 0.2
            mx += 0.02 if target_dec_x > mx else -0.02 if target_dec_x < mx else 0
            my += 0.02 if target_dec_y > my else -0.02 if target_dec_y < my else 0
        except (TypeError, IndexError):
            # Se il percorso è corrotto, il mostro si muove in linea d'aria senza mandare in crash il gioco
            mx += 0.02 if px > mx else -0.02 if px < mx else 0
            my += 0.02 if py > my else -0.02 if py < my else 0
    else:
        mx += 0.02 if px > mx else -0.02 if px < mx else 0
        my += 0.02 if py > my else -0.02 if py < my else 0


def esegui_jumpscare():
    global game_over
    game_over = True
    for dimensione in range(20, 90, 15):
        sfondo = 0x2000 if random.randint(0, 1) == 0 else NERO
        display.fill_rectangle(0, 0, 320, 240, sfondo)
        vibra_x = random.randint(-8, 8)
        vibra_y = random.randint(-8, 8)
        cx = 160 + vibra_x
        cy = 100 + vibra_y
        display.fill_rectangle(cx - dimensione, cy - int(dimensione * 1.3), dimensione * 2, int(dimensione * 1.5), BIANCO)
        for _ in range(4):
            tx = random.randint(0, 320)
            ty = random.randint(0, 240)
            display.fill_rectangle(tx, ty, random.randint(10, 80), random.randint(2, 6), NERO)
        time.sleep_ms(40)
    display.fill_rectangle(0, 0, 320, 240, NERO)
    for y in range(0, 240, random.randint(4, 12)):
        display.fill_rectangle(0, y, 320, random.randint(1, 3), ROSSO_SANGUE)
    time.sleep_ms(300)
    display.fill_rectangle(40, 90, 240, 50, NERO)
    display.draw_text8x8(112, 100, "SEI MORTO.", ROSSO_SANGUE)
    display.draw_text8x8(80, 125, "LUI TI HA CONSUMATO.", 0x7BCE)
    display.draw_text8x8(64, 190, "[ TOCCA PER RICOMINCIARE ]", BIANCO)

def render_prospettiva_3d():
    sfondo_cielo = SOFFITTO if torcia_livello > 0 else NERO
    sfondo_terra = TERRENO if torcia_livello > 0 else NERO
    display.fill_rectangle(0, 0, VIEW_W, VIEW_H // 2, sfondo_cielo)
    display.fill_rectangle(0, VIEW_H // 2, VIEW_W, VIEW_H // 2, sfondo_terra)
    dist_mostro_giocatore = math.sqrt((mx - px)**2 + (my - py)**2)
    dist_p2_giocatore = math.sqrt((p2_x - px)**2 + (p2_y - py)**2) if p2_connesso else 999.0
    if dist_mostro_giocatore < 0.6 and not god_mode:
        esegui_jumpscare()
        return
    monster_dir = math.atan2(mx - px, my - py)
    while monster_dir - pa > math.pi: monster_dir -= 2 * math.pi
    while monster_dir - pa < -math.pi: monster_dir += 2 * math.pi
    p2_dir = math.atan2(p2_x - px, p2_y - py) if p2_connesso else 0.0
    while p2_dir - pa > math.pi: p2_dir -= 2 * math.pi
    while p2_dir - pa < -math.pi: p2_dir += 2 * math.pi
    colonna_centrale = VIEW_W // 2
    idx_raggio = 0
    for i in range(0, VIEW_W, RES_STEP):
        angolo_relativo = RAY_ANGLES[idx_raggio]
        ray_angle = pa + angolo_relativo
        distance_to_wall = 0.0
        hit_wall = False
        shaded = False
        hit_battery = False
        dist_bat = 11.0
        eye_x = math.sin(ray_angle)
        eye_y = math.cos(ray_angle)
                # --- BLOCCO CORRETTO PER IL CONTROLLO DELLE BATTERIE (TUPLA) ---
        while not hit_wall and distance_to_wall < 10.5:
            distance_to_wall += 0.15
            test_x = int(px + eye_x * distance_to_wall)
            test_y = int(py + eye_y * distance_to_wall)
            if test_x < 0 or test_x >= MAP_SIZE or test_y < 0 or test_y >= MAP_SIZE:
                hit_wall = True
                distance_to_wall = 10.5
            else:
                for b in batterie:
                    # CORREZIONE: b[0] per la coordinata X, b[1] per la coordinata Y
                    if int(b[0]) == test_x and int(b[1]) == test_y and not hit_battery:
                        hit_battery = True
                        dist_bat = distance_to_wall
                if WORLD_MAP[test_y][test_x] == 1:
                    hit_wall = True
                    boundary_x = (px + eye_x * distance_to_wall) - test_x
                    if boundary_x < 0.06 or boundary_x > 0.94: shaded = True

        dist_corretta = distance_to_wall * COS_ANGLES[idx_raggio]
        if dist_corretta < 0.1: dist_corretta = 0.1
        wall_height = int(VIEW_H / dist_corretta)
        if wall_height > VIEW_H: wall_height = VIEW_H
        y_start = (VIEW_H // 2) - (wall_height // 2)
        if torcia_livello <= 0 or distance_to_wall > 8.0: colore_blocco = NERO
        elif distance_to_wall > 5.5: colore_blocco = MURO_OMBRA
        else: colore_blocco = MURO_OMBRA if shaded else MURO
        display.fill_rectangle(i, y_start, RES_STEP, wall_height, colore_blocco)
        if hit_battery and dist_bat < distance_to_wall and dist_bat < 6.0 and torcia_livello > 0:
            b_height = int(VIEW_H / (dist_bat * COS_ANGLES[idx_raggio]))
            if b_height > VIEW_H: b_height = VIEW_H
            bat_h = max(4, b_height // 4)
            bat_y_start = (VIEW_H // 2) + (b_height // 2) - bat_h
            display.fill_rectangle(i, bat_y_start, RES_STEP, bat_h, VERDE_BAT)
        if p2_connesso and dist_p2_giocatore < distance_to_wall and dist_p2_giocatore < 8.0 and torcia_livello > 0:
            angolo_p2 = ray_angle - p2_dir
            while angolo_p2 > math.pi: angolo_p2 -= 2 * math.pi
            while angolo_p2 < -math.pi: angolo_p2 += 2 * math.pi
            p2_dist_corr = dist_p2_giocatore * COS_ANGLES[idx_raggio]
            if p2_dist_corr < 0.1: p2_dist_corr = 0.1
            p2_height = int(VIEW_H / p2_dist_corr)
            if p2_height > VIEW_H: p2_height = VIEW_H
            p2_y_start = (VIEW_H // 2) - (p2_height // 2)
            mezzo_p2_w = (math.atan2(0.15, dist_p2_giocatore))
            if abs(angolo_p2) < mezzo_p2_w:
                display.fill_rectangle(i, p2_y_start, RES_STEP, p2_height, COL_MINIMAP_P2)
                display.fill_rectangle(i, p2_y_start, RES_STEP, p2_height // 4, BIANCO)
        if dist_mostro_giocatore < distance_to_wall and dist_mostro_giocatore < 8.0 and torcia_livello > 0:
            angolo_mostro = ray_angle - monster_dir
            while angolo_mostro > math.pi: angolo_mostro -= 2 * math.pi
            while angolo_mostro < -math.pi: angolo_mostro += 2 * math.pi
            m_dist_corr = dist_mostro_giocatore * COS_ANGLES[idx_raggio]
            if m_dist_corr < 0.1: m_dist_corr = 0.1
            m_height = int(VIEW_H / m_dist_corr)
            if m_height > VIEW_H: m_height = VIEW_H
            m_y_start = (VIEW_H // 2) - (m_height // 2)
            mezzo_mostro_w = (math.atan2(0.18, dist_mostro_giocatore)) 
            if abs(angolo_mostro) < mezzo_mostro_w:
                testa_h = max(2, m_height // 6)
                busto_h = m_height // 2
                centro_mostro = abs(angolo_mostro) < (mezzo_mostro_w * 0.4)
                estremita_braccia = abs(angolo_mostro) > (mezzo_mostro_w * 0.7)
                glitch_testa = BIANCO if random.randint(1, 10) > 2 else NERO
                if centro_mostro:
                    display.fill_rectangle(i, m_y_start, RES_STEP, testa_h, glitch_testa)
                    display.fill_rectangle(i, m_y_start + testa_h, RES_STEP, max(1, testa_h // 3), ROSSO_SANGUE)
                    display.fill_rectangle(i, m_y_start + testa_h + 1, RES_STEP, busto_h, NERO)
                    display.fill_rectangle(i, m_y_start + testa_h + busto_h, RES_STEP, m_height - testa_h - busto_h, NERO)
                elif not estremita_braccia: display.fill_rectangle(i, m_y_start + testa_h, RES_STEP, busto_h, NERO)
                else: display.fill_rectangle(i, m_y_start + int(testa_h * 1.5), RES_STEP, int(busto_h * 1.2), NERO)
            if i == colonna_centrale and dist_mostro_giocatore < 3.2 and abs(angolo_mostro) < 0.1 and not god_mode:
                if random.randint(1, 4) == 1:
                    esegui_jumpscare()
                    return
        idx_raggio += 1
    if torcia_livello > 0:
        offset_x, offset_y = 248, 8
        dim_blocco = 4
        for my_idx in range(MAP_SIZE):
            for mx_idx in range(MAP_SIZE):
                col_mappa = COL_MINIMAP_MURO if WORLD_MAP[my_idx][mx_idx] == 1 else COL_MINIMAP_VUOTO
                display.fill_rectangle(offset_x + (mx_idx * dim_blocco), offset_y + (my_idx * dim_blocco), dim_blocco, dim_blocco, col_mappa)
        # --- BLOCCO MINIMAPPA CORRETTO ---
        for b in batterie: 
            # CORREZIONE: usiamo b[0] per la X e b[1] per la Y della tupla
            display.fill_rectangle(offset_x + int(b[0] * dim_blocco), offset_y + int(b[1] * dim_blocco), 2, 2, VERDE_BAT)

        if god_mode or dist_mostro_giocatore < 10.0: display.fill_rectangle(offset_x + int(mx * dim_blocco), offset_y + int(my * dim_blocco), 3, 3, COL_MINIMAP_MOSTRO)
        if p2_connesso: display.fill_rectangle(offset_x + int(p2_x * dim_blocco), offset_y + int(p2_y * dim_blocco), 3, 3, COL_MINIMAP_P2)
        display.fill_rectangle(offset_x + int(px * dim_blocco), offset_y + int(py * dim_blocco), 3, 3, BIANCO)
    display.fill_rectangle(150 , 119 - 30 , 20 , 2 , BIANCO)
    display.fill_rectangle(159 , 110 - 30 , 2 , 20 , BIANCO)
    display.fill_rectangle(8, 20, 56, 8, NERO)
    display.draw_text8x8(8, 20, "FPS: " + str(fps_correnti), VERDE_BAT if fps_correnti > 20 else ROSSO_SANGUE)
    disegna_interfaccia_torcia()

# =============================================================================
# 10. AVVIO OPERATIVO E LOOP DI RENDERING INTERATTIVO MULTIPLAYER
# =============================================================================
disegna_controlli_joystick()
render_prospettiva_3d()

ultimo_tocco = 0
ultimo_scarico_torcia = time.ticks_ms()
ultimo_invio_radio = time.ticks_ms()

while True:
    # Gestione continua e asincrona dei pacchetti radio in ingresso
    controlla_ricezione_wireless()
    
    # Trasmette la propria posizione via radio a 20Hz (ogni 50 millisecondi)
    if time.ticks_diff(time.ticks_ms(), ultimo_invio_radio) > 50:
        invia_posizione_wireless()
        ultimo_invio_radio = time.ticks_ms()
        
    tocco = leggi_touch()
    aggiorna_grafica = False
    tempo_attuale = time.ticks_ms()
    
    # -------------------------------------------------------------------------
    # CASO A: GESTIONE MODALITÀ MAPPA A SCHERMO INTERO
    # -------------------------------------------------------------------------
    if mappa_schermo_intero:
        if tocco is not None:
            tx, ty = tocco
            if time.ticks_diff(tempo_attuale, ultimo_tocco) > 250:
                if 64 <= tx <= 256 and 24 <= ty <= 216 and god_mode:
                    click_grid_x = int((tx - 64) / 12)
                    click_grid_y = int((ty - 24) / 12)
                    if 0 <= click_grid_x < MAP_SIZE and 0 <= click_grid_y < MAP_SIZE:
                        if WORLD_MAP[click_grid_y][click_grid_x] == 0:
                            px, py = click_grid_x + 0.5, click_grid_y + 0.5
                            renderizza_mappa_schermo_intero()
                            ultimo_tocco = tempo_attuale
                            continue

                if 8 <= tx <= 56 and 205 <= ty <= 233:
                    mappa_schermo_intero = False
                    mostro_cliccato_mappa = False
                    display.fill_rectangle(0, 0, 320, 240, NERO)
                    disegna_controlli_joystick()
                    render_prospettiva_3d()
                    ultimo_tocco = tempo_attuale
                    continue
                    
                mostro_screen_x = 64 + int(mx * 12) + 3
                mostro_screen_y = 24 + int(my * 12) + 3
                if (mostro_screen_x - 12 <= tx <= mostro_screen_x + 18) and \
                   (mostro_screen_y - 12 <= ty <= mostro_screen_y + 18):
                    mostro_cliccato_mappa = True
                    renderizza_mappa_schermo_intero()
                    ultimo_tocco = tempo_attuale
                    continue
                
                if mostro_cliccato_mappa and 210 <= tx <= 312 and 205 <= ty <= 233:
                    god_mode = not god_mode
                    if god_mode:
                        torcia_livello = 100.0 
                    renderizza_mappa_schermo_intero()
                    ultimo_tocco = tempo_attuale
                    continue
        time.sleep_ms(20)
        continue

    # -------------------------------------------------------------------------
    # CASO B: GAME OVER / RESPAWN
    # -------------------------------------------------------------------------
    if game_over:
        if tocco is not None:
            if ID_GIOCATORE == 1:
                px, py = 1.5, 1.5
            else:
                px, py = 4.5, 1.5
            pa = 0.0
            torcia_livello = 100.0
            game_over = False
            god_mode = False
            mappa_schermo_intero = False
            mostro_cliccato_mappa = False
            posiziona_mostro_casuale()
            inizializza_batterie() 
            disegna_controlli_joystick()
            render_prospettiva_3d()
            time.sleep_ms(300)
        continue

    # -------------------------------------------------------------------------
    # AGGIORNAMENTO ENERGIA TORCIA 
    # -------------------------------------------------------------------------
    if time.ticks_diff(tempo_attuale, ultimo_scarico_torcia) > 100:
        if god_mode:
            torcia_livello = 100.0  
        elif torcia_livello > 0:
            torcia_livello -= 0.05
            if int(torcia_livello * 10) % 50 == 0:
                disegna_interfaccia_torcia()
            if torcia_livello <= 0:
                torcia_livello = 0
                disegna_interfaccia_torcia()
        ultimo_scarico_torcia = tempo_attuale

    muovi_mostro()
    controlla_raccolta_batterie()        
    aggiorna_rigenerazione_batterie()    
    
    # -------------------------------------------------------------------------
    # STRUTTURA TOUCH PRINCIPALE
    # -------------------------------------------------------------------------
    if tocco is not None:
        tx, ty = tocco
        
        if tx >= 240 and ty <= 80:
            if time.ticks_diff(tempo_attuale, ultimo_tocco) > 300:
                mappa_schermo_intero = True
                renderizza_mappa_schermo_intero()
                ultimo_tocco = tempo_attuale
                continue

        if ty >= 180:
            if time.ticks_diff(tempo_attuale, ultimo_tocco) > 80: 
                vecchia_px, vecchia_py = px, py
                if 10 <= tx <= 75:
                    pa -= 0.25
                    aggiorna_grafica = True
                elif 85 <= tx <= 150:
                    px += math.sin(pa) * 0.4
                    py += math.cos(pa) * 0.4
                    aggiorna_grafica = True
                elif 160 <= tx <= 225:
                    pa += 0.25
                    aggiorna_grafica = True
                elif 245 <= tx <= 310:
                    px -= math.sin(pa) * 0.4
                    py -= math.cos(pa) * 0.4
                    aggiorna_grafica = True
                
                if aggiorna_grafica and WORLD_MAP[int(py)][int(px)] == 1:
                    px, py = vecchia_px, vecchia_py
                ultimo_tocco = tempo_attuale
                
        elif ty < 180 and god_mode:
            if time.ticks_diff(tempo_attuale, ultimo_tocco) > 400:
                spara_onda_energetica()
                ultimo_tocco = tempo_attuale

    # Forza il refresh dello schermo se ti muovi o se l'altro giocatore si sposta
    if aggiorna_grafica or p2_connesso:
        render_prospettiva_3d()
        conteggio_frame += 1

    tempo_attuale_fps = time.ticks_ms()
    if time.ticks_diff(tempo_attuale_fps, ultimo_calcolo_fps) >= 1000:
        fps_correnti = conteggio_frame
        conteggio_frame = 0
        ultimo_calcolo_fps = tempo_attuale_fps
        if not mappa_schermo_intero and not game_over:
            display.fill_rectangle(8, 20, 56, 8, NERO)
            display.draw_text8x8(8, 20, "FPS: " + str(fps_correnti), VERDE_BAT if fps_correnti > 20 else ROSSO_SANGUE)
        
    time.sleep_ms(10)
