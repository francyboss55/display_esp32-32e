import machine
from machine import SPI, SoftSPI, Pin
import time
import ili9341
import math
import random

# =============================================================================
# 1. CONFIGURAZIONE HARDWARE
# =============================================================================
TFT_MISO, TFT_MOSI, TFT_CLK = 12, 13, 14
TFT_CS, TFT_DC, TFT_RST, TFT_BCKL = 15, 2, 4, 21

backlight = Pin(TFT_BCKL, Pin.OUT, value=1)

spi = SPI(1, baudrate=40000000, sck=Pin(TFT_CLK), mosi=Pin(TFT_MOSI), miso=Pin(TFT_MISO))
display = ili9341.Display(spi, dc=Pin(TFT_DC), cs=Pin(TFT_CS), rst=Pin(TFT_RST), width=320, height=240, rotation=90)

TP_CLK, TP_MISO, TP_MOSI, TP_CS = 25, 39, 32, Pin(33, Pin.OUT, value=1)
spi_touch = SoftSPI(baudrate=1000000, sck=Pin(TP_CLK), mosi=Pin(TP_MOSI), miso=Pin(TP_MISO))

# =============================================================================
# 2. CONFIGURAZIONE BLOCCHI E COLORI RGB565
# =============================================================================
MAP_SIZE = 24
WORLD_MAP = [[0 for _ in range(MAP_SIZE)] for _ in range(MAP_SIZE)]

ARIA    = 0
PIETRA  = 1
ERBA    = 2
LEGNO   = 3
FOGLIE  = 4

CIELO_GIORNO = 0x7EFC  
TERRA_GIORNO = 0x4B00  
NERO         = 0x0000
BIANCO       = 0xFFFF

# Mappatura dei blocchi con colori singoli puri a 16-bit
BLOCCO_COLORI = {
    PIETRA:  {"giorno": 0x7BEF, "notte": 0x3186},
    ERBA:    {"giorno": 0x1F40, "notte": 0x0200},
    LEGNO:   {"giorno": 0x7220, "notte": 0x3100},
    FOGLIE:  {"giorno": 0x05E0, "notte": 0x0200}
}

NOMINI_BLOCCHI = ["ARIA", "PIETRA", "ERBA", "LEGNO", "FOGLIE"]

# =============================================================================
# 3. GENERAZIONE PROCEDURALE
# =============================================================================
def genera_mondo_minecraft():
    for y in range(MAP_SIZE):
        for x in range(MAP_SIZE):
            WORLD_MAP[y][x] = ARIA

    for x in range(MAP_SIZE):
        WORLD_MAP[0][x] = PIETRA
        WORLD_MAP[MAP_SIZE-1][x] = PIETRA
    for y in range(MAP_SIZE):
        WORLD_MAP[y][0] = PIETRA
        WORLD_MAP[y][MAP_SIZE-1] = PIETRA
        
    for y in range(2, MAP_SIZE - 2):
        for x in range(2, MAP_SIZE - 2):
            r = random.random()
            if r < 0.12:
                WORLD_MAP[y][x] = PIETRA if random.random() > 0.4 else ERBA
            elif r < 0.15: 
                WORLD_MAP[y][x] = LEGNO
                if WORLD_MAP[y-1][x] == ARIA: WORLD_MAP[y-1][x] = FOGLIE
                if WORLD_MAP[y+1][x] == ARIA: WORLD_MAP[y+1][x] = FOGLIE
                if WORLD_MAP[y][x-1] == ARIA: WORLD_MAP[y][x-1] = FOGLIE
                if WORLD_MAP[y][x+1] == ARIA: WORLD_MAP[y][x+1] = FOGLIE

genera_mondo_minecraft()

# =============================================================================
# 4. STATO GIOCATORE E PARAMETRI COORIDINATE HOTBAR VISIVA
# =============================================================================
px, py = 3.5, 3.5  
pa = 0.0          
FOV = math.pi / 2.4
VIEW_W, VIEW_H = 320, 150 # Ridotta l'altezza 3D per non sovrapporsi graficamente ai d-pad

blocco_selezionato = PIETRA  

# Nuove coordinate Hotbar nello spazio 3D fluttuante (in basso al centro dello schermo 3D)
HOTBAR_X = 100  
HOTBAR_Y = 120  
SLOT_DIM = 26   

tempo_mondo = 6000 
ultimo_aggiornamento_tempo = time.ticks_ms()

RAY_ANGLES = []
COS_ANGLES = []
for i in range(0, VIEW_W, RES_STEP := 4):
    angolo_relativo = (- FOV / 2) + (i / VIEW_W) * FOV
    RAY_ANGLES.append(angolo_relativo)
    COS_ANGLES.append(math.cos(angolo_relativo))

ultimo_calcolo_fps = time.ticks_ms()
conteggio_frame = 0
fps_correnti = 0

# =============================================================================
# 5. INTERFACCIA INTERATTIVA: HUD DOPPIO D-PAD ED INVENTARIO FLOATING
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

def disegna_hud_joystick():
    display.fill_rectangle(0, VIEW_H, 320, 2, 0x4208)
    display.fill_rectangle(0, VIEW_H + 2, 320, 88, 0x2104) # Ampliata l'altezza HUD a 88 pixel
    
    # D-PAD SINISTRO (Movimento Corpo)
    display.fill_rectangle(10, 185, 30, 22, 0x3186)
    display.draw_text8x8(21, 192, "A", BIANCO) # Cammina a sinistra (Strafe L)
    display.fill_rectangle(45, 160, 30, 22, 0x3186)
    display.draw_text8x8(56, 167, "^", BIANCO) # Avanti
    display.fill_rectangle(80, 185, 30, 22, 0x3186)
    display.draw_text8x8(91, 192, "D", BIANCO) # Cammina a destra (Strafe R)
    display.fill_rectangle(45, 210, 30, 22, 0x3186)
    display.draw_text8x8(56, 217, "v", BIANCO) # Indietro

    # D-PAD DESTRO (Spostamento Visuale)
    display.fill_rectangle(210, 185, 45, 35, 0x528A)
    display.draw_text8x8(228, 198, "<-", BIANCO) # Gira visuale a Sinistra
    display.fill_rectangle(265, 185, 45, 35, 0x528A)
    display.draw_text8x8(283, 198, "->", BIANCO) # Gira visuale a Destra

def disegna_hotbar_floating():
    # Disegna l'hotbar sovrapposta direttamente sopra alla renderizzazione 3D
    for idx in range(4):
        b_id = idx + 1  
        sx = HOTBAR_X + (idx * (SLOT_DIM + 4))
        
        display.fill_rectangle(sx, HOTBAR_Y, SLOT_DIM, SLOT_DIM, NERO)
        col_blocco = BLOCCO_COLORI[b_id]["giorno"]
        display.fill_rectangle(sx + 3, HOTBAR_Y + 3, SLOT_DIM - 6, SLOT_DIM - 6, col_blocco)
        
        if blocco_selezionato == b_id:
            display.draw_rectangle(sx, HOTBAR_Y, SLOT_DIM, SLOT_DIM, BIANCO)
            display.draw_rectangle(sx + 1, HOTBAR_Y + 1, SLOT_DIM - 2, SLOT_DIM - 2, BIANCO)
        else:
            display.draw_rectangle(sx, HOTBAR_Y, SLOT_DIM, SLOT_DIM, 0x5AEB)

# =============================================================================
# 6. ENGINE RAYCASTING CON MINIMAPPA E INTERFACCE INTEGRATE
# =============================================================================
def render_prospettiva_3d():
    if 4000 <= tempo_mondo < 12000:       
        cielo_corr, terra_corr = CIELO_GIORNO, TERRA_GIORNO
        stato_luce = "giorno"
        dist_max_vista = 12.0
    elif 12000 <= tempo_mondo < 14000:     
        cielo_corr, terra_corr = 0x9104, 0x2100  
        stato_luce = "notte"
        dist_max_vista = 9.0
    elif 14000 <= tempo_mondo < 22000:     
        cielo_corr, terra_corr = 0x0008, 0x1082  
        stato_luce = "notte"
        dist_max_vista = 5.5  
    else:                                  
        cielo_corr, terra_corr = 0x4210, 0x2100  
        stato_luce = "giorno"
        dist_max_vista = 9.0

    display.fill_rectangle(0, 0, VIEW_W, VIEW_H // 2, cielo_corr)
    display.fill_rectangle(0, VIEW_H // 2, VIEW_W, VIEW_H // 2, terra_corr)
    
    idx_raggio = 0
    for i in range(0, VIEW_W, 4):
        angolo_relativo = RAY_ANGLES[idx_raggio]
        ray_angle = pa + angolo_relativo
        distance_to_wall = 0.0
        hit_wall = False
        blocco_colpito = ARIA
        
        eye_x = math.sin(ray_angle)
        eye_y = math.cos(ray_angle)
        
        while not hit_wall and distance_to_wall < dist_max_vista:
            distance_to_wall += 0.12
            test_x = int(px + eye_x * distance_to_wall)
            test_y = int(py + eye_y * distance_to_wall)
            
            if test_x < 0 or test_x >= MAP_SIZE or test_y < 0 or test_y >= MAP_SIZE:
                hit_wall = True
                distance_to_wall = dist_max_vista
                blocco_colpito = PIETRA
            else:
                id_cella = WORLD_MAP[test_y][test_x]
                if id_cella != ARIA:
                    hit_wall = True
                    blocco_colpito = id_cella

        dist_corretta = distance_to_wall * COS_ANGLES[idx_raggio]
        if dist_corretta < 0.1: dist_corretta = 0.1
        
        wall_height = int(VIEW_H / dist_corretta)
        if wall_height > VIEW_H: wall_height = VIEW_H
        y_start = (VIEW_H // 2) - (wall_height // 2)
        
        if distance_to_wall >= (dist_max_vista - 0.5):
            colore_colonna = cielo_corr
        else:
            colore_colonna = BLOCCO_COLORI.get(blocco_colpito, {"giorno": 0x7BEF, "notte": 0x2104})[stato_luce]
            
        display.fill_rectangle(i, y_start, 4, wall_height, colore_colonna)
        idx_raggio += 1
        
    # Mirino
    display.fill_rectangle(156, 74, 8, 2, BIANCO)
    display.fill_rectangle(159, 71, 2, 8, BIANCO)
    
    # Rinfresca l'hotbar fluttuante sopra la grafica 3D appena disegnata
    disegna_hotbar_floating()
    
    # MINIMAPPA IN ALTO A DESTRA
    offset_x, offset_y = 264, 4
    dim_blocco = 2
    display.fill_rectangle(offset_x - 2, offset_y - 2, (MAP_SIZE * dim_blocco) + 4, (MAP_SIZE * dim_blocco) + 4, NERO)
    display.draw_rectangle(offset_x - 2, offset_y - 2, (MAP_SIZE * dim_blocco) + 4, (MAP_SIZE * dim_blocco) + 4, BIANCO)
    for my_idx in range(MAP_SIZE):
        for mx_idx in range(MAP_SIZE):
            tipo = WORLD_MAP[my_idx][mx_idx]
            if tipo != ARIA:
                display.fill_rectangle(offset_x + (mx_idx * dim_blocco), offset_y + (my_idx * dim_blocco), dim_blocco, dim_blocco, BLOCCO_COLORI[tipo]["giorno"])
    display.fill_rectangle(offset_x + int(px * dim_blocco), offset_y + int(py * dim_blocco), 2, 2, BIANCO)
    
    # HUD informazioni testuali
    display.fill_rectangle(4, 4, 80, 24, NERO)
    display.draw_text8x8(6, 6, f"FPS: {fps_correnti}", 0x07E0 if fps_correnti > 20 else 0xF800)
    stringa_ora = "NOTTE" if (14000 <= tempo_mondo < 22000) else "GIORNO"
    display.draw_text8x8(6, 16, f"TM:{stringa_ora}", BIANCO)

# =============================================================================
# 7. LOOP DI INTERAZIONE GENERALE
# =============================================================================
disegna_hud_joystick()
render_prospettiva_3d()

ultimo_tocco = 0

while True:
    tempo_attuale = time.ticks_ms()
    
    # Sincronizzazione scorrimento temporale giorno-notte
    if time.ticks_diff(tempo_attuale, ultimo_aggiornamento_tempo) > 200:
        vecchio_periodo = "notte" if (14000 <= tempo_mondo < 22000) else "giorno"
        tempo_mondo = (tempo_mondo + 150) % 24000
        if vecchio_periodo != ("notte" if (14000 <= tempo_mondo < 22000) else "giorno") or (tempo_mondo % 1500 == 0):
            render_prospettiva_3d()
        ultimo_aggiornamento_tempo = tempo_attuale

    tocco = leggi_touch()
    aggiorna_grafica = False
    
    if tocco is not None:
        tx, ty = tocco
        
        # --- GESTIONE HUD IN BASSO (Doppio D-Pad) ---
        if ty >= 150:
            if time.ticks_diff(tempo_attuale, ultimo_tocco) > 80:
                vecchia_px, vecchia_py = px, py
                
                # A) LOGICA D-PAD SINISTRO (Spostamento spaziale del corpo)
                if 10 <= tx <= 40 and 185 <= ty <= 207: # Tasto A (Strafe Sinistra)
                    px += math.sin(pa - math.pi/2) * 0.35
                    py += math.cos(pa - math.pi/2) * 0.35
                    aggiorna_grafica = True
                elif 45 <= tx <= 75 and 160 <= ty <= 182: # Tasto ^ (Avanti)
                    px += math.sin(pa) * 0.35
                    py += math.cos(pa) * 0.35
                    aggiorna_grafica = True
                elif 80 <= tx <= 110 and 185 <= ty <= 207: # Tasto D (Strafe Destra)
                    px += math.sin(pa + math.pi/2) * 0.35
                    py += math.cos(pa + math.pi/2) * 0.35
                    aggiorna_grafica = True
                elif 45 <= tx <= 75 and 210 <= ty <= 232: # Tasto v (Indietro)
                    px -= math.sin(pa) * 0.35
                    py -= math.cos(pa) * 0.35
                    aggiorna_grafica = True
                
                # B) LOGICA D-PAD DESTRO (Rotazione asse della visuale)
                elif 210 <= tx <= 255 and 185 <= ty <= 220: # Ruota a Sinistra
                    pa -= 0.18
                    aggiorna_grafica = True
                elif 265 <= tx <= 310 and 185 <= ty <= 220: # Ruota a Destra
                    pa += 0.18
                    aggiorna_grafica = True
                
                # Controllo collisione con i blocchi solidi
                if aggiorna_grafica and WORLD_MAP[int(py)][int(px)] != ARIA:
                    px, py = vecchia_px, vecchia_py
                    
                ultimo_tocco = tempo_attuale
                
        # --- GESTIONE COSTRUZIONE/SCAVO E FLOATING HOTBAR (Area Superiore 3D) ---
        else:
            if tx > 250 and ty < 60: # Evita tocchi accidentali sopra la minimappa
                continue
                
            # Intercettazione tocco sopra i 4 slot dell'hotbar fluttuante della visuale
            if HOTBAR_X <= tx <= (HOTBAR_X + (4 * (SLOT_DIM + 4))) and HOTBAR_Y <= ty <= (HOTBAR_Y + SLOT_DIM):
                if time.ticks_diff(tempo_attuale, ultimo_tocco) > 150:
                    for idx in range(4):
                        sx = HOTBAR_X + (idx * (SLOT_DIM + 4))
                        if sx <= tx <= (sx + SLOT_DIM):
                            blocco_selezionato = idx + 1
                            disegna_hotbar_floating()
                            break
                    ultimo_tocco = tempo_attuale
                continue

            # Logica di Scavo o Costruzione classica sul mondo 3D
            if time.ticks_diff(tempo_attuale, ultimo_tocco) > 350:
                eye_x = math.sin(pa)
                eye_y = math.cos(pa)
                dist_interazione = 0.0
                colpito = False
                
                azione_scava = (tx < 160)
                bx_colpito, by_colpito = -1, -1
                bx_precedente, by_precedente = -1, -1
                limite_raggio = 4.0 if (4000 <= tempo_mondo < 14000) else 2.5
                
                while dist_interazione < limite_raggio and not colpito:
                    test_x = int(px + eye_x * dist_interazione)
                    test_y = int(py + eye_y * dist_interazione)
                    if 0 <= test_x < MAP_SIZE and 0 <= test_y < MAP_SIZE:
                        if WORLD_MAP[test_y][test_x] != ARIA:
                            bx_colpito, by_colpito = test_x, test_y
                            colpito = True
                        else:
                            bx_precedente, by_precedente = test_x, test_y
                    dist_interazione += 0.15
                
                if azione_scava and colpito:
                    if 0 < bx_colpito < MAP_SIZE-1 and 0 < by_colpito < MAP_SIZE-1:
                        WORLD_MAP[by_colpito][bx_colpito] = ARIA
                        aggiorna_grafica = True
                elif not azione_scava and colpito and bx_precedente != -1:
                    if int(px) != bx_precedente or int(py) != by_precedente:
                        WORLD_MAP[by_precedente][bx_precedente] = blocco_selezionato
                        aggiorna_grafica = True
                        
                ultimo_tocco = tempo_attuale

    if aggiorna_grafica:
        render_prospettiva_3d()
        conteggio_frame += 1

    tempo_attuale_fps = time.ticks_ms()
    if time.ticks_diff(tempo_attuale_fps, ultimo_calcolo_fps) >= 1000:
        fps_correnti = conteggio_frame
        conteggio_frame = 0
        ultimo_calcolo_fps = tempo_attuale_fps
        display.fill_rectangle(4, 4, 80, 24, NERO)
        display.draw_text8x8(6, 6, f"FPS: {fps_correnti}", 0x07E0 if fps_correnti > 20 else 0xF800)
        stringa_ora = "NOTTE" if (14000 <= tempo_mondo < 22000) else "GIORNO"
        display.draw_text8x8(6, 16, f"TM:{stringa_ora}", BIANCO)
        
    time.sleep_ms(10)

