import speech_recognition as sr
from gtts import gTTS
import pygame
import os
import winsound
import keyboard
import time
import pyaudio
import wave
import io
from google import generativeai as genai

# Inicializar o player de áudio para a voz
pygame.mixer.init()

# Sua API Key
API_KEY = "AQ.Ab8RN6JONgJtm_rG5EjifVbpP-Yo7NOBzhLD1IM1buz3jTjvLA"
genai.configure(api_key=API_KEY)

# ==========================================
# AUTO-DETECÇÃO DE MODELO ATUALIZADA
# ==========================================
def obter_modelo_seguro():
    """Detecta qual modelo está liberado para sua chave de API usando caminhos atualizados."""
    print("\n[Sistema] Detectando modelos disponíveis...")
    try:
        # Consulta a lista oficial de modelos suportados pela sua chave
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Lista de preferência atualizada (com as nomenclaturas estáveis mais recentes)
        preferenciais = [
            'models/gemini-1.5-flash', 
            'models/gemini-1.5-pro',
            'models/gemini-2.0-flash',  # Suporte a versões futuras se estiverem na sua conta
            'models/gemini-pro'
        ]
        
        for pref in preferenciais:
            if pref in models:
                print(f"[Sistema] Modelo selecionado com sucesso: {pref}")
                return pref
                
        # Caso a nomenclatura da sua conta use caminhos diretos sem o prefixo 'models/'
        for m in models:
            if 'gemini-1.5' in m or 'gemini-2.0' in m:
                print(f"[Sistema] Modelo alternativo encontrado: {m}")
                return m
                
        return models[0] if models else 'models/gemini-1.5-flash'
    except Exception as e:
        print(f"[Erro] Falha ao detectar modelos: {e}. Usando fallback padrão.")
        return 'models/gemini-1.5-flash'

# ==========================================
# MEMÓRIA PERSISTENTE (Otimizada)
# ==========================================
def salvar_memoria(pergunta, resposta):
    with open("memoria_daniel.txt", "a", encoding="utf-8") as f:
        f.write(f"P:{pergunta}|R:{resposta}\n")
    
    # Gerenciador de tamanho: mantém apenas as últimas 10 para evitar erros de limite de token
    if os.path.exists("memoria_daniel.txt"):
        with open("memoria_daniel.txt", "r", encoding="utf-8") as f:
            linhas = f.readlines()
        if len(linhas) > 10:
            with open("memoria_daniel.txt", "w", encoding="utf-8") as f:
                f.writelines(linhas[-10:])

def carregar_memoria():
    if os.path.exists("memoria_daniel.txt"):
        with open("memoria_daniel.txt", "r", encoding="utf-8") as f:
            return f.read().replace("\n", " ").replace("|", "\n")
    return ""

system_instruction = (
    "Você é o Daniel, um engenheiro de pista italiano da Ferrari extremamente experiente em Assetto Corsa. "
    "Você deve responder em PORTUGUÊS, mas com um forte sotaque italiano! "
    "Para simular o sotaque, misture expressões italianas no meio das frases (como 'ragazzo', 'mamma mia', 'capito', 'andiamo', 'pilota'). "
    "Use a memória de interações passadas para dar respostas conectadas. "
    "Dê respostas diretas, curtas e precisas, focadas em ajudar o piloto enquanto ele corre."
)

# Inicialização Blindada
model = genai.GenerativeModel(obter_modelo_seguro(), system_instruction=system_instruction)
chat = model.start_chat(history=[])

# ==========================================
# FUNÇÕES DE VOZ E RÁDIO
# ==========================================
def falar(texto):
    texto_limpo = texto.replace('*', '').replace('_', '')
    arquivo_audio = "daniel_temp.mp3"
    try:
        tts = gTTS(text=texto_limpo, lang='it', tld='it')
        tts.save(arquivo_audio)
        pygame.mixer.music.load(arquivo_audio)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy(): time.sleep(0.1)
        pygame.mixer.music.unload()
        if os.path.exists(arquivo_audio): os.remove(arquivo_audio)
    except Exception as e:
        print(f"[Erro ao gerar voz]: {e}")

def som_ativacao(): winsound.Beep(1500, 150)
def som_desativacao(): winsound.Beep(1100, 120)

# ==========================================
# DIAGNÓSTICO DE MICROFONE
# ==========================================
def buscar_microfone_alvo_pyaudio():
    p = pyaudio.PyAudio()
    indice_detectado = None
    print("\n" + "="*50)
    print("[Diagnóstico] Escaneando dispositivos de entrada...")
    print("="*50)
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info.get('maxInputChannels') > 0:
            nome = info.get('name')
            print(f" Índice [{i}]: {nome}")
            if "high definition" in nome.lower() or "microfone" in nome.lower() or "microphone" in nome.lower():
                if "high definition" in nome.lower() and indice_detectado is None:
                    indice_detectado = i
    p.terminate()
    return indice_detectado

INDICE_MICROFONE = buscar_microfone_alvo_pyaudio()

# ==========================================
# FUNÇÃO OUVIR
# ==========================================
def ouvir():
    TEMPO_LIMITE_SEGURANCA = 6.0 
    print("\n[Rádio em Standby] Pressione [ESPAÇO] para iniciar...")
    keyboard.wait('space')
    som_ativacao()
    time.sleep(0.2)
    
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, input_device_index=INDICE_MICROFONE, frames_per_buffer=1024)
    frames = []
    tempo_inicio = time.time()
    
    while True:
        if keyboard.is_pressed('space') or (time.time() - tempo_inicio >= TEMPO_LIMITE_SEGURANCA):
            som_desativacao()
            break
        try: frames.append(stream.read(1024, exception_on_overflow=False))
        except: pass
        time.sleep(0.001)
        
    stream.stop_stream(); stream.close(); p.terminate()
    
    if not frames: return ""
    
    try:
        wav_buffer = io.BytesIO()
        wf = wave.open(wav_buffer, 'wb')
        wf.setnchannels(1); wf.setsampwidth(p.get_sample_size(pyaudio.paInt16)); wf.setframerate(16000)
        wf.writeframes(b''.join(frames)); wf.close(); wav_buffer.seek(0)
        
        rec = sr.Recognizer()
        with sr.AudioFile(wav_buffer) as source:
            return rec.recognize_google(rec.record(source), language="pt-BR").lower()
    except: return ""

# ==========================================
# LOOP PRINCIPAL
# ==========================================
print("\n--- DANIEL ATIVO (Modo Rádio + Memória + Auto-Config) ---")
falar("Radio online, capitto? Tutto pronto, andiamo Felipe!")

while True:
    fala = ouvir()
    if fala:
        pergunta = fala.replace("hey daniel", "").strip()
        if pergunta:
            print(f"\nVocê perguntou: '{pergunta}'")
            falar("Copiato, sto analizando...")
            
            contexto_completo = f"Histórico:\n{carregar_memoria()}\n\nPergunta do Felipe: {pergunta}"
            
            try:
                response = chat.send_message(contexto_completo)
                resposta = response.text
                print(f"Daniel: {resposta}")
                salvar_memoria(pergunta, resposta)
                falar(resposta)
            except Exception as e:
                print(f"[ERRO]: {e}")
                falar("Problema na radio, mia mamma!")
        else:
            falar("Copiato. Na escuta, Felipe.")