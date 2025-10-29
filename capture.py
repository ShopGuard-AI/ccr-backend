# capture.py
import threading
import cv2
import time
import sys
import logging
import math # Para backoff exponencial
import os

# Obtém logger específico para este módulo
logger = logging.getLogger(__name__)

# Constantes de Reconexão
MAX_RECONNECT_ATTEMPTS = None # None para infinito, ou um número alto (ex: 1000)
INITIAL_RECONNECT_DELAY = 2   # Delay inicial em segundos (2s)
MAX_RECONNECT_DELAY = 60      # Delay máximo em segundos (1 min)
BACKOFF_FACTOR = 1.5          # Fator exponencial (menor que 2 para crescimento mais suave)

class VideoCapture:
    """
    Classe otimizada para captura de vídeo usando um thread dedicado,
    com lógica de reconexão automática para streams.
    """
    def __init__(self, src=0, width=640, height=480, backend=None):
        self.src = src
        self.width = width
        self.height = height
        self.backend = backend if backend is not None else cv2.CAP_FFMPEG
        self.cap: cv2.VideoCapture = None # Objeto de captura do OpenCV
        self.status = "initializing" # Estados: initializing, connected, reconnecting, failed, stopped
        self.grabbed = False         # Último status de cap.read()
        self.frame = None            # Último frame lido com sucesso
        self.started = False         # Flag para controlar o loop do thread
        self.read_lock = threading.Lock() # Lock para acesso seguro a frame, grabbed, status, cap
        self.reconnect_attempts = 0  # Contador de tentativas de reconexão
        self.thread: threading.Thread = None # O objeto do thread
        self._log_extra = {'source': self.src} # Contexto base para logs
        logger.info("Objeto VideoCapture criado.", extra=self._log_extra)

    def _connect(self) -> bool:
        """
        Tenta (re)estabelecer a conexão com a fonte de vídeo.
        Retorna True se bem-sucedido, False caso contrário.
        Deve ser chamado com o read_lock adquirido se acessando self.cap.
        """
        logger.info("Tentando conectar/reconectar...", extra=self._log_extra)
        # Libera captura antiga se existir
        if self.cap is not None:
            logger.debug("Liberando captura antiga...", extra=self._log_extra)
            try:
                self.cap.release()
            except Exception as e_rel:
                logger.warning(f"Erro não crítico ao liberar captura antiga: {e_rel}", extra=self._log_extra)
            self.cap = None

        # Tenta criar nova captura
        try:
            open_backends = []
            if self.backend is not None:
                open_backends.append(self.backend)
            open_backends.append(None)  # Fallback para backend padrão

            self.cap = None
            for backend_flag in open_backends:
                if backend_flag is None:
                    tmp_cap = cv2.VideoCapture(self.src)
                else:
                    tmp_cap = cv2.VideoCapture(self.src, backend_flag)
                if tmp_cap is not None and tmp_cap.isOpened():
                    self.cap = tmp_cap
                    if backend_flag is not None:
                        logger.info(f"Captura aberta com backend {backend_flag}.", extra=self._log_extra)
                    break
                if tmp_cap:
                    tmp_cap.release()

            if self.cap is None or not self.cap.isOpened():
                logger.error("Falha ao abrir fonte na (re)conexão.", extra=self._log_extra)
                return False

            # Define propriedades (ignora erros se não suportado pela fonte)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            # Tenta definir buffer baixo para menor latência (pode não funcionar em todas as fontes)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # Tenta ler o primeiro frame para validar a conexão
            time.sleep(0.5) # Pequena pausa para buffer inicial
            grabbed, frame = self.cap.read()
            if not grabbed:
                logger.error("Falha ao ler primeiro frame após (re)conexão.", extra=self._log_extra)
                self.cap.release()
                self.cap = None
                return False

            logger.info("Conexão estabelecida com sucesso.", extra=self._log_extra)
            # Atualiza estado inicial seguro (já estamos dentro de um lock ou antes do thread)
            self.grabbed = True
            self.frame = frame
            self.status = "connected"
            self.reconnect_attempts = 0 # Reseta tentativas ao conectar
            return True
        except Exception as e_conn:
             logger.error(f"Exceção durante conexão/leitura inicial: {e_conn}", exc_info=False, extra=self._log_extra)
             if self.cap: self.cap.release(); self.cap=None # Garante liberação
             return False

    def set(self, prop_id, value):
        """Define uma propriedade da captura OpenCV."""
        with self.read_lock:
             if self.cap and self.cap.isOpened():
                 return self.cap.set(prop_id, value)
             else:
                 logger.warning(f"Tentativa de set({prop_id}) em captura não aberta/existente.", extra=self._log_extra)
                 return False

    def get(self, prop_id):
        """Obtém uma propriedade da captura OpenCV."""
        with self.read_lock:
             if self.cap and self.cap.isOpened():
                 return self.cap.get(prop_id)
             else:
                 #logger.warning(f"Tentativa de get({prop_id}) em captura não aberta/existente.", extra=self._log_extra)
                 return None # Retorna None se não conseguir obter

    def start(self):
        """Inicia o thread de captura em background."""
        with self.read_lock: # Protege contra condição de corrida no start
            if self.started:
                logger.warning("Thread de captura já iniciado.", extra=self._log_extra)
                return self
            self.started = True # Define como iniciado ANTES de tentar conectar
            self.status = "initializing" # Define estado inicial

        logger.info("Iniciando thread de captura...", extra=self._log_extra)
        # Tenta a conexão inicial fora do lock principal
        if not self._connect():
             logger.error("Falha na conexão inicial. Thread não iniciado ou falhou imediatamente.", extra=self._log_extra)
             with self.read_lock: self.status = "failed"; self.started = False # Marca como falho e não iniciado
             return self # Retorna self mesmo em falha para permitir checagem de status

        # Se a conexão inicial funcionou, inicia o thread
        thread_name = f"CaptureThread-{os.path.basename(str(self.src))}" # Usa basename para URLs longas
        self.thread = threading.Thread(target=self._update_loop, args=(), name=thread_name, daemon=True)
        self.thread.start()
        logger.info(f"Thread de leitura iniciado ({thread_name}).", extra=self._log_extra)
        return self

    def _update_loop(self):
        """Loop principal do thread: lê frames e tenta reconectar."""
        logger.debug("Loop de atualização iniciado.", extra=self._log_extra)
        while self.started: # Loop controlado pela flag self.started
            grabbed = False; frame = None; capture_error = False
            current_cap_ref = None # Referência local ao objeto cap

            # Pega a referência atual do objeto cap dentro do lock
            with self.read_lock:
                if self.status == "connected" and self.cap and self.cap.isOpened():
                    current_cap_ref = self.cap

            # Tenta ler o frame fora do lock principal para permitir chamadas a read()
            if current_cap_ref:
                try:
                    grabbed, frame = current_cap_ref.read()
                    if not grabbed and self.started: # Verifica 'started' de novo, pode ter sido parado enquanto lia
                        logger.warning("Falha ao ler frame (grabbed=False). Iniciando reconexão...", extra=self._log_extra)
                        capture_error = True
                except cv2.error as e: logger.warning(f"Erro cv2 na leitura: {e}. Tentando reconectar.", extra=self._log_extra); grabbed=False; capture_error=True
                except Exception as e: logger.warning(f"Erro inesperado na leitura: {e}. Tentando reconectar.", exc_info=False, extra=self._log_extra); grabbed=False; capture_error=True
            elif self.status == "connected":
                # Se status é connected mas current_cap_ref é None (raro, mas possível), marca erro
                logger.warning("Status 'connected' mas objeto de captura inválido. Tentando reconectar.", extra=self._log_extra)
                capture_error = True


            # --- Processamento do Resultado da Leitura ---
            if grabbed and frame is not None:
                # Sucesso na leitura
                with self.read_lock:
                    self.grabbed = True
                    self.frame = frame
                    # Se estava reconectando, volta para conectado e reseta tentativas
                    if self.status == "reconnecting":
                        logger.info("Reconexão bem sucedida!", extra=self._log_extra)
                        self.status = "connected"
                        self.reconnect_attempts = 0
                # Pequeno sleep para não consumir 100% CPU se a fonte for rápida
                time.sleep(0.001)
                continue # Volta para o início para ler o próximo frame

            # --- Tratamento de Erro / Reconexão ---
            # Só entra aqui se (grabbed=False ou frame=None ou capture_error=True) E self.started=True
            if self.started and (not grabbed or capture_error):
                with self.read_lock: # Atualiza status para 'reconnecting'
                    if self.status != "failed": # Só tenta se não falhou permanentemente
                        self.status = "reconnecting"
                        self.grabbed = False # Garante que read() retorne False
                    else:
                        self.started = False # Garante parada se já está como failed
                        break # Sai do loop se já falhou

                # Se ainda pode reconectar
                if self.status == "reconnecting":
                    self.reconnect_attempts += 1
                    # Verifica limite de tentativas (se definido)
                    if MAX_RECONNECT_ATTEMPTS is not None and self.reconnect_attempts > MAX_RECONNECT_ATTEMPTS:
                        logger.critical(f"Máximo de {MAX_RECONNECT_ATTEMPTS} tentativas de reconexão atingido. Desistindo.", extra=self._log_extra)
                        self.started = False # Para o loop permanentemente
                        with self.read_lock: self.status = "failed"; self.grabbed = False
                        break # Sai do loop while

                    # Calcula delay com backoff exponencial
                    delay = min(INITIAL_RECONNECT_DELAY * (BACKOFF_FACTOR ** (self.reconnect_attempts - 1)), MAX_RECONNECT_DELAY)
                    logger.warning(f"Tentativa de reconexão {self.reconnect_attempts} em {delay:.1f}s...", extra=self._log_extra)
                    # Espera antes de tentar reconectar, mas checa 'started' periodicamente
                    wait_start = time.time()
                    while time.time() - wait_start < delay:
                        if not self.started: break # Sai do sleep se stop() for chamado
                        time.sleep(0.1)
                    if not self.started: break # Sai do loop principal se stop() foi chamado

                    # Tenta reconectar (fora do lock principal)
                    if not self._connect():
                        logger.warning(f"Tentativa de reconexão {self.reconnect_attempts} falhou.", extra=self._log_extra)
                        # Continua no loop para próxima tentativa após delay
                    # else: # Se _connect() funcionou, o status foi para 'connected'
                          # O próximo ciclo do loop tentará ler o frame
            # Pequeno sleep se ainda rodando mas sem ação (ex: inicializando)
            elif self.started:
                 time.sleep(0.05)

        # --- Fim do Loop While ---
        logger.info("Thread de atualização finalizado.", extra={'source': self.src, 'final_status': self.status})
        # Libera o recurso de captura ao final do thread
        with self.read_lock:
             if self.cap and self.cap.isOpened(): self.cap.release(); logger.info("Recurso liberado no fim do thread.", extra={'source': self.src})
             self.status = "stopped" # Define status final como parado


    def read(self):
        """
        Lê o último frame disponível e o status atual da captura.
        Retorna: (grabbed, frame, status)
        - grabbed (bool): True se um frame válido foi lido na última tentativa BEM SUCEDIDA.
        - frame (np.ndarray | None): A cópia do último frame lido, ou None.
        - status (str): O estado atual ('initializing', 'connected', 'reconnecting', 'failed', 'stopped').
        """
        with self.read_lock:
            # Copia o frame apenas se ele existir
            frame_copy = self.frame.copy() if self.frame is not None else None
            # Grabbed indica se a última leitura foi boa, mas retornamos False se não conectado
            current_grabbed = self.grabbed and self.status == "connected"
            current_status = self.status
        return current_grabbed, frame_copy, current_status

    def stop(self):
        """Sinaliza para o thread parar e espera (com timeout) sua finalização."""
        if not self.started and self.status not in ["initializing", "failed"]:
             # Se nunca iniciou ou já está 'stopped', não faz nada
             # logger.debug("Tentativa de stop() em captura não iniciada/já parada.", extra=self._log_extra)
             return

        logger.info("Solicitando parada do thread de captura...", extra=self._log_extra)
        # Sinaliza para o loop while terminar
        self.started = False
        thread_to_join = self.thread # Pega referência local

        if thread_to_join and thread_to_join.is_alive():
             logger.debug("Aguardando thread finalizar...", extra=self._log_extra)
             # Espera um tempo razoável (maior que o delay de reconexão pode ajudar)
             thread_to_join.join(timeout=(MAX_RECONNECT_DELAY + 5.0))
             if thread_to_join.is_alive():
                  logger.warning("Thread de captura não finalizou após join timeout!", extra=self._log_extra)
        else:
             logger.debug("Thread de captura já finalizado ou não iniciado.", extra=self._log_extra)

        # Liberação do 'cap' agora é feita pelo próprio thread ao terminar seu loop.
        # Apenas garantimos que o status final seja 'stopped' ou 'failed'.
        with self.read_lock:
             if self.status != "failed": # Não sobrescreve 'failed'
                 self.status = "stopped"
        logger.info(f"Processo de parada finalizado. Status final: {self.status}", extra=self._log_extra)

    def __exit__(self, exec_type, exc_value, traceback):
         """Garante que stop() seja chamado ao sair do contexto 'with'."""
         self.stop()
