#!/usr/bin/env pybricks-micropython

"""
Exemplo de Programa "Puppy" (cachorrinho) para LEGO® MINDSTORMS® EV3
---------------------------------------------------------------------

Este programa requer o LEGO® EV3 MicroPython v2.0.
Download: https://education.lego.com/en-us/support/mindstorms-ev3/python-for-ev3

As instruções de montagem podem ser encontradas em:
https://education.lego.com/en-us/support/mindstorms-ev3/building-instructions#building-core

Cores do "osso" (Sensor de Cor, Port.S4) e o que cada uma faz
-----------------------------------------------------------------------------
Aproximando o osso (ou qualquer objeto colorido) do Sensor de Cor, o
cachorrinho reage de forma diferente para cada cor, segundo update_feed_count():

none (nenhuma cor detectada): não alimenta o cachorrinho; nada acontece.
black (preto/ausência de comida): NÃO conta como alimentação — ela fica de
  pé, late e mostra a língua de fora (stand_up + NEUTRAL_EYES + DOG_BARK_1).
red (vermelho): ação de comer — abaixa a cabeça, mastiga e levanta de novo (eat()).
green (verde): pedindo comida — senta e faz carinha triste (HURT_EYES + sit_down).
blue (azul): feliz, língua de fora (ofegando) e latindo, brincalhona (NEUTRAL_EYES + DOG_BARK_2).
yellow (amarelo): faz xixi em vez de comer — levanta a perna esquerda, balança
  e toca o som de xixi (executa go_to_bathroom).
white (branco) / brown (marrom): reação padrão de comer e sentar (SQUINTY_EYES + som de mastigar + sit_down).

Observação: exceto o preto (que não conta como alimentação), toda cor válida
incrementa feed_count. Só conta uma nova reação quando a cor muda em relação
à última leitura (self.prev_color), então é preciso afastar o osso e
aproximar de novo (ou trocar de cor) para repetir a reação.

Sensor de toque (Port.S1)
-----------------------------------------------------------------------------
Sempre que o sensor de toque é pressionado (carinho/pet), a cachorrinha
sempre balança a cabeça bem rápido (shake_head, 750 graus/s — 5x mais rápido
que um movimento normal de cabeça). Além disso, o número de carinhos
recebidos desde o último reset() dispara reações especiais:

1º carinho: senta, dorme e ronca (vai para o comportamento go_to_sleep).
2º carinho: senta e late apaixonada (HEART_EYES + DOG_BARK_1).
3º carinho: rosna e fica brava (vai para o comportamento act_angry).

A partir do 4º carinho, volta à reação padrão (SQUINTY_EYES + som de fungada).

Inatividade
-----------------------------------------------------------------------------
Se ficar 15 segundos sem nenhuma interação (nem carinho, nem comida), o
cachorrinho senta e vai dormir (ver monitor_counts).

Música de abertura
-----------------------------------------------------------------------------
Ao iniciar o programa (run()), o cachorrinho toca uma pequena melodia
(play_startup_song) a 200 BPM, antes de começar a se movimentar. As notas
ficam definidas em STARTUP_SONG. A mesma melodia também toca ao final do
comportamento de fazer xixi (go_to_bathroom).

Fazer xixi (go_to_bathroom)
-----------------------------------------------------------------------------
Ao entrar nesse comportamento, o cachorrinho levanta todas as pernas e fica
de pé (stand_up), depois levanta e balança a perna ESQUERDA 3 vezes (postura
de "fazer xixi", com o som de buzina), e por fim toca a música de abertura
antes de voltar a ficar parado (idle).

LED do EV3 (humor do cachorrinho)
-----------------------------------------------------------------------------
Sempre que o comportamento muda, o LED do bloco EV3 é atualizado para
espelhar o humor atual (ver update_light). Como o LED só tem 4 estados
possíveis (apagado, vermelho, verde e laranja):

apagado: dormindo (go_to_sleep).
vermelho: com raiva (act_angry) — alerta.
laranja: precisando de atenção — fome, banheiro, ou acordando
  (act_hungry, go_to_bathroom, wake_up).
verde: tudo bem — parado, brincalhão ou feliz (idle, act_playful, act_happy).
"""

import urandom

from pybricks.hubs import EV3Brick
from pybricks.ev3devices import Motor, ColorSensor, TouchSensor
from pybricks.parameters import Port, Button, Color, Direction, Stop
from pybricks.media.ev3dev import Image, ImageFile, SoundFile
from pybricks.tools import wait, StopWatch


class Puppy:
    # Estas constantes são usadas para posicionar as pernas.
    HALF_UP_ANGLE = (
        25  # Ângulo de "meio levantado" (posição intermediária ao levantar/sentar)
    )
    STAND_UP_ANGLE = 65  # Ângulo em que o cachorrinho fica de pé
    STRETCH_ANGLE = (
        125  # Ângulo em que as pernas ficam esticadas para trás (alongamento)
    )

    # Estas constantes são para posicionar a cabeça.
    HEAD_UP_ANGLE = 0  # Posição da cabeça levantada (posição inicial/zero)
    HEAD_DOWN_ANGLE = -40  # Posição da cabeça abaixada (usada ao dormir)

    # Estas constantes são para os "olhos" (imagens exibidas na tela do EV3).
    NEUTRAL_EYES = Image(ImageFile.NEUTRAL)  # Olhos neutros/normais
    TIRED_EYES = Image(ImageFile.TIRED_MIDDLE)  # Olhos cansados (olhando para o meio)
    TIRED_LEFT_EYES = Image(
        ImageFile.TIRED_LEFT
    )  # Olhos cansados olhando para a esquerda
    TIRED_RIGHT_EYES = Image(
        ImageFile.TIRED_RIGHT
    )  # Olhos cansados olhando para a direita
    SLEEPING_EYES = Image(ImageFile.SLEEPING)  # Olhos fechados (dormindo)
    HURT_EYES = Image(
        ImageFile.HURT
    )  # Olhos de "machucado"/triste (usado quando está com fome)
    ANGRY_EYES = Image(ImageFile.ANGRY)  # Olhos de raiva
    HEART_EYES = Image(ImageFile.LOVE)  # Olhos de coração (feliz/apaixonado)
    SQUINTY_EYES = Image(
        ImageFile.TEAR
    )  # a lágrima é apagada depois (ver draw_box no final do arquivo)

    # Melodia tocada ao iniciar o programa (ver play_startup_song).
    # Formato pybricks: "<NOTA><OITAVA>/<DURAÇÃO>" ("#" = sustenido,
    # "." = nota pontuada, ou seja, 1.5x a duração).
    STARTUP_SONG = [
        # Compasso 1: e6 d6 f#5 g#5
        "E6/4",
        "D6/4",
        "F#5/4",
        "G#5/4",
        # Compasso 2: c#6 b5 d5 e5
        "C#6/4",
        "B5/4",
        "D5/4",
        "E5/4",
        # Compasso 3: b5 a5 c#5 e5
        "B5/4",
        "A5/4",
        "C#5/4",
        "E5/4",
        # Compasso 4: a5 (mínima pontuada)
        "A5/2.",
    ]

    def __init__(self):
        # Inicializa o bloco (hub) do EV3.
        self.ev3 = EV3Brick()

        # Inicializa os motores conectados às pernas traseiras.
        self.left_leg_motor = Motor(Port.D, Direction.COUNTERCLOCKWISE)
        self.right_leg_motor = Motor(Port.A, Direction.COUNTERCLOCKWISE)

        # Inicializa o motor conectado à cabeça.
        # A engrenagem sem-fim (worm gear) move 1 dente por rotação. Ela se conecta
        # a uma engrenagem de 24 dentes. Essa engrenagem de 24 dentes é ligada, por
        # um eixo, a engrenagens paralelas de 12 dentes. As engrenagens de 12 dentes
        # se conectam a engrenagens de 36 dentes.
        self.head_motor = Motor(
            Port.C, Direction.COUNTERCLOCKWISE, gears=[[1, 24], [12, 36]]
        )
        # Define a posição atual da cabeça como o ângulo 15° já na inicialização.
        self.head_motor.reset_angle(15)

        # Inicializa o Sensor de Cor. É usado para detectar as cores ao
        # "alimentar" o cachorrinho.
        self.color_sensor = ColorSensor(Port.S4)

        # Inicializa o sensor de toque. É usado para detectar quando alguém
        # faz carinho no cachorrinho (pet).
        self.touch_sensor = TouchSensor(Port.S1)

        # Cronômetros usados para controlar o tempo desde a última carícia,
        # desde a última alimentação e desde a última mudança de contagem.
        self.pet_count_timer = StopWatch()
        self.feed_count_timer = StopWatch()
        self.count_changed_timer = StopWatch()

        # Estes atributos são inicializados depois, no método reset().
        self.pet_target = None  # Quantidade de carícias necessária para ficar feliz
        self.feed_target = (
            None  # Quantidade de alimentações necessária para ficar feliz
        )
        self.pet_count = None  # Contador atual de carícias recebidas
        self.feed_count = None  # Contador atual de alimentações recebidas

        # Estes atributos são usados pelas properties (behavior/eyes).
        self._behavior = None
        self._behavior_changed = None
        self._eyes = None
        self._eyes_changed = None

        # Estes atributos são usados na atualização dos olhos (piscar aleatório).
        self.eyes_timer_1 = StopWatch()
        self.eyes_timer_1_end = 0
        self.eyes_timer_2 = StopWatch()
        self.eyes_timer_2_end = 0
        self.eyes_closed = False

        # Estes atributos são usados pelo comportamento "brincalhão" (act_playful).
        self.playful_timer = StopWatch()
        self.playful_bark_interval = None  # Intervalo aleatório entre latidos

        # Estes atributos são usados nos métodos de atualização (update_*),
        # para detectar mudanças de estado (borda de subida).
        self.prev_petted = None
        self.prev_color = None

    def adjust_head(self):
        """Usa os botões para cima e para baixo do bloco EV3 para ajustar a
        cabeça do cachorrinho para cima ou para baixo (calibração manual
        antes de iniciar o programa).

        Ao entrar aqui, a cabeça já sobe sozinha até o ponto mais alto
        possível (até travar mecanicamente), para que a calibração comece
        sempre do topo — bastando usar o botão para baixo, se necessário,
        para ajustar fino.
        """
        self.ev3.screen.load_image(ImageFile.EV3_ICON)
        self.ev3.light.on(Color.ORANGE)

        # Levanta a cabeça o mais alto possível (até travar no limite
        # mecânico), com torque limitado para não forçar as engrenagens.
        self.head_motor.run_until_stalled(30, then=Stop.HOLD, duty_limit=30)

        while True:
            buttons = self.ev3.buttons.pressed()
            if Button.CENTER in buttons:
                # Botão central confirma o ajuste e encerra o laço.
                break
            elif Button.UP in buttons:
                self.head_motor.run(20)
            elif Button.DOWN in buttons:
                self.head_motor.run(-20)
            else:
                self.head_motor.stop()
            wait(100)

        self.head_motor.stop()
        # Define a posição atual da cabeça como o novo "ângulo zero".
        self.head_motor.reset_angle(0)
        self.ev3.light.on(Color.GREEN)

    def move_head(self, target):
        """Move a cabeça até o ângulo alvo (target).

        Argumentos:
            target (int):
                O ângulo alvo em graus. 0 é a posição inicial, valores
                negativos ficam abaixo desse ponto e valores positivos
                ficam acima desse ponto.
        """
        self.head_motor.run_target(20, target)

    def shake_head(self):
        """Balança a cabeça do cachorrinho bem rápido (usada quando o
        sensor de toque é pressionado, ou seja, quando ela recebe carinho).
        Velocidade 5x maior que um movimento normal de cabeça (750 graus/s
        em vez de 150 graus/s)."""
        self.head_motor.run_target(750, self.HEAD_UP_ANGLE + 15)
        self.head_motor.run_target(750, self.HEAD_DOWN_ANGLE + 15)
        self.head_motor.run_target(750, self.HEAD_UP_ANGLE)

    def play_startup_song(self):
        """Toca a música de abertura (STARTUP_SONG) a 400 BPM."""
        self.ev3.speaker.play_notes(self.STARTUP_SONG, tempo=400)

    def eat(self):
        """Faz a ação de comer: abaixa a cabeça até a tigela, mastiga e
        levanta a cabeça de novo (usada quando a cor lida é vermelha)."""
        self.move_head(self.HEAD_DOWN_ANGLE)
        self.eyes = self.SQUINTY_EYES
        self.ev3.speaker.play_file(SoundFile.CRUNCHING)
        wait(500)
        self.move_head(self.HEAD_UP_ANGLE)

    def reset(self):
        # Deve ser chamado quando o cachorrinho estiver sentado.
        self.left_leg_motor.reset_angle(0)
        self.right_leg_motor.reset_angle(0)
        # Escolhe um número aleatório de vezes que o cachorrinho precisa ser acariciado.
        self.pet_target = urandom.randint(3, 6)
        # Escolhe um número aleatório de vezes que o cachorrinho precisa ser alimentado.
        self.feed_target = urandom.randint(2, 4)
        # A contagem de carícias e a de alimentação começam em 1.
        self.pet_count, self.feed_count = 1, 1
        # Reinicia os cronômetros.
        self.pet_count_timer.reset()
        self.feed_count_timer.reset()
        self.count_changed_timer.reset()
        # Define o comportamento inicial como "idle" (parado/à espera).
        self.behavior = self.idle

    # Os próximos 8 métodos definem os 8 comportamentos do cachorrinho.

    def idle(self):
        """O cachorrinho está parado, esperando que alguém faça carinho
        nele ou o alimente."""
        if self.did_behavior_change:
            print("idle")
            self.stand_up()
        self.update_eyes()
        self.update_behavior()
        self.update_pet_count()
        self.update_feed_count()

    def go_to_sleep(self):
        """Faz o cachorrinho dormir."""
        if self.did_behavior_change:
            print("go_to_sleep")
            self.eyes = self.TIRED_EYES
            self.sit_down()
            self.move_head(self.HEAD_DOWN_ANGLE)
            self.eyes = self.SLEEPING_EYES
            self.ev3.speaker.play_file(SoundFile.SNORING)
        # Para acordar, é preciso tocar no sensor de toque E pressionar o
        # botão central ao mesmo tempo.
        if self.touch_sensor.pressed() and Button.CENTER in self.ev3.buttons.pressed():
            self.count_changed_timer.reset()
            self.behavior = self.wake_up

    def wake_up(self):
        """Faz o cachorrinho acordar."""
        if self.did_behavior_change:
            print("wake_up")
        self.eyes = self.TIRED_EYES
        self.ev3.speaker.play_file(SoundFile.DOG_WHINE)
        self.move_head(self.HEAD_UP_ANGLE)
        self.sit_down()
        self.stretch()
        wait(1000)
        self.stand_up()
        self.behavior = self.idle

    def act_playful(self):
        """Faz o cachorrinho agir de forma brincalhona (quando está sem
        carícias, mas já foi alimentado)."""
        if self.did_behavior_change:
            print("act_playful")
            self.eyes = self.NEUTRAL_EYES
            self.stand_up()
            self.playful_bark_interval = 0

        if self.update_pet_count():
            # Se o cachorrinho foi acariciado, paramos de ser brincalhões.
            self.behavior = self.idle

        # Late em intervalos aleatórios enquanto estiver brincalhão.
        if self.playful_timer.time() > self.playful_bark_interval:
            self.ev3.speaker.play_file(SoundFile.DOG_BARK_2)
            self.playful_timer.reset()
            self.playful_bark_interval = urandom.randint(4, 8) * 1000

    def act_angry(self):
        """Faz o cachorrinho agir com raiva (quando recebeu carícia demais
        e comida de menos)."""
        if self.did_behavior_change:
            print("act_angry")
        self.eyes = self.ANGRY_EYES
        self.ev3.speaker.play_file(SoundFile.DOG_GROWL)
        self.stand_up()
        wait(1500)
        self.ev3.speaker.play_file(SoundFile.DOG_BARK_1)
        # Penaliza a contagem de carícias por ter ficado com raiva.
        self.pet_count -= 1
        print("pet_count:", self.pet_count, "pet_target:", self.pet_target)
        self.behavior = self.idle

    def act_hungry(self):
        """Faz o cachorrinho agir com fome (quando a contagem de
        alimentação chegou a zero)."""
        if self.did_behavior_change:
            print("act_hungry")
            self.eyes = self.HURT_EYES
            self.sit_down()
            self.ev3.speaker.play_file(SoundFile.DOG_WHINE)

        if self.update_feed_count():
            # Se recebemos comida, não estamos mais com fome.
            self.behavior = self.idle

        if self.update_pet_count():
            # Se recebemos carícia em vez de comida, ficamos com raiva.
            self.behavior = self.act_angry

    def go_to_bathroom(self):
        """Faz o cachorrinho "ir ao banheiro" (quando recebeu comida
        demais e carícia de menos, ou ao ser alimentado com a cor amarela)."""
        if self.did_behavior_change:
            print("go_to_bathroom")
        self.eyes = self.SQUINTY_EYES
        # Levanta todas as pernas e fica de pé antes de fazer xixi.
        self.stand_up()
        wait(100)
        # Levanta a perna esquerda (postura de "fazer xixi").
        self.left_leg_motor.run_target(100, self.STRETCH_ANGLE)
        wait(800)
        self.ev3.speaker.play_file(SoundFile.HORN_1)
        wait(1000)
        # Balança a perna esquerda 3 vezes.
        for _ in range(3):
            self.left_leg_motor.run_angle(100, 20)
            self.left_leg_motor.run_angle(100, -20)
        self.left_leg_motor.run_target(100, self.STAND_UP_ANGLE)
        # Toca a música de abertura também ao terminar de fazer xixi.
        self.play_startup_song()
        # Zera a contagem de alimentação, já que "gastou" a comida.
        self.feed_count = 1
        self.behavior = self.idle

    def act_happy(self):
        """Faz o cachorrinho agir feliz (quando atingiu exatamente as
        metas de carícia e alimentação)."""
        if self.did_behavior_change:
            print("act_happy")
        self.eyes = self.HEART_EYES
        # self.move_head(self.?)
        self.sit_down()
        # Late e pula 3 vezes para comemorar.
        for _ in range(3):
            self.ev3.speaker.play_file(SoundFile.DOG_BARK_1)
            self.hop()
        wait(500)
        # Faz a dancinha (pernas esquerda/direita alternadas).
        self.dance()
        self.sit_down()
        # Reinicia o ciclo com novas metas aleatórias de carícia/alimentação.
        self.reset()

    def sit_down(self):
        """Faz o cachorrinho sentar."""
        self.left_leg_motor.run(-50)
        self.right_leg_motor.run(-50)
        wait(1000)
        self.left_leg_motor.stop()
        self.right_leg_motor.stop()
        wait(100)

    # Os próximos 4 métodos definem ações usadas para compor os
    # comportamentos acima.

    def stand_up(self):
        """Faz o cachorrinho ficar de pé."""
        # Primeiro sobe até a posição intermediária (meio levantado)...
        self.left_leg_motor.run_target(100, self.HALF_UP_ANGLE, wait=False)
        self.right_leg_motor.run_target(100, self.HALF_UP_ANGLE)
        while not self.left_leg_motor.control.done():
            wait(100)

        # ...depois sobe até a posição final, de pé.
        self.left_leg_motor.run_target(50, self.STAND_UP_ANGLE, wait=False)
        self.right_leg_motor.run_target(50, self.STAND_UP_ANGLE)
        while not self.left_leg_motor.control.done():
            wait(100)

        wait(500)

    def stretch(self):
        """Faz o cachorrinho esticar as pernas para trás (alongamento)."""
        self.stand_up()

        # Estica as pernas para trás.
        self.left_leg_motor.run_target(100, self.STRETCH_ANGLE, wait=False)
        self.right_leg_motor.run_target(100, self.STRETCH_ANGLE)
        while not self.left_leg_motor.control.done():
            wait(100)

        self.ev3.speaker.play_file(SoundFile.DOG_WHINE)

        # Volta para a posição de pé.
        self.left_leg_motor.run_target(100, self.STAND_UP_ANGLE, wait=False)
        self.right_leg_motor.run_target(100, self.STAND_UP_ANGLE)
        while not self.left_leg_motor.control.done():
            wait(100)

    def hop(self):
        """Faz o cachorrinho pular (usado na comemoração de act_happy)."""
        self.left_leg_motor.run(500)
        self.right_leg_motor.run(500)
        wait(275)
        self.left_leg_motor.hold()
        self.right_leg_motor.hold()
        wait(275)
        self.left_leg_motor.run(-50)
        self.right_leg_motor.run(-50)
        wait(275)
        self.left_leg_motor.stop()
        self.right_leg_motor.stop()

    def dance(self):
        """Faz a "dancinha": balança as pernas esquerda e direita de forma
        alternada (usada na comemoração de act_happy)."""
        for _ in range(4):
            self.left_leg_motor.run_target(300, self.HALF_UP_ANGLE, wait=False)
            self.right_leg_motor.run_target(300, self.STAND_UP_ANGLE, wait=False)
            wait(200)
            self.left_leg_motor.run_target(300, self.STAND_UP_ANGLE, wait=False)
            self.right_leg_motor.run_target(300, self.HALF_UP_ANGLE, wait=False)
            wait(200)
        self.left_leg_motor.run_target(300, self.STAND_UP_ANGLE, wait=False)
        self.right_leg_motor.run_target(300, self.STAND_UP_ANGLE)

    @property
    def behavior(self):
        """Obtém e define o comportamento atual (guarda uma referência ao
        método de comportamento, por exemplo self.idle, self.act_happy etc.)."""
        return self._behavior

    @behavior.setter
    def behavior(self, value):
        # Só marca como "alterado" se o comportamento realmente mudou,
        # evitando reiniciar a lógica de did_behavior_change sem necessidade.
        if self._behavior != value:
            self._behavior = value
            self._behavior_changed = True
            self.update_light()

    @property
    def did_behavior_change(self):
        """bool: Verifica se o comportamento mudou desde a última vez que
        essa property foi lida (funciona como uma flag de "consumo único",
        útil para executar código apenas uma vez ao entrar em um comportamento).
        """
        if self._behavior_changed:
            self._behavior_changed = False
            return True
        return False

    def update_light(self):
        """Faz o LED do EV3 espelhar o humor atual do cachorrinho. O LED do
        bloco EV3 só tem 4 estados possíveis (apagado, vermelho, verde e
        laranja), então o mapeamento é:

        - Dormindo (go_to_sleep): luz apagada.
        - Com raiva (act_angry): luz vermelha (alerta).
        - Precisando de atenção — fome, banheiro, ou acordando
          (act_hungry, go_to_bathroom, wake_up): luz laranja.
        - Qualquer outro estado (idle, act_playful, act_happy): tudo bem,
          luz verde.
        """
        if self.behavior == self.go_to_sleep:
            self.ev3.light.off()
        elif self.behavior == self.act_angry:
            self.ev3.light.on(Color.RED)
        elif self.behavior in (self.act_hungry, self.go_to_bathroom, self.wake_up):
            self.ev3.light.on(Color.ORANGE)
        else:
            self.ev3.light.on(Color.GREEN)

    def update_behavior(self):
        """Atualiza a property :prop:`behavior` (comportamento) com base no
        estado atual das contagens de carícia e alimentação.
        """
        if self.pet_count == self.pet_target and self.feed_count == self.feed_target:
            # Se temos exatamente a quantidade certa de carícias e comida, fica feliz.
            self.behavior = self.act_happy
        elif self.pet_count > self.pet_target and self.feed_count < self.feed_target:
            # Se temos carícia demais e comida de menos, fica com raiva.
            self.behavior = self.act_angry
        elif self.pet_count < self.pet_target and self.feed_count > self.feed_target:
            # Se temos carícia de menos e comida demais, vai ao banheiro.
            self.behavior = self.go_to_bathroom
        elif self.pet_count == 0 and self.feed_count > 0:
            # Se não recebeu nenhuma carícia mas já foi alimentado, fica brincalhão.
            self.behavior = self.act_playful
        elif self.feed_count == 0:
            # Se não recebeu nenhuma comida, fica com fome.
            self.behavior = self.act_hungry

    @property
    def eyes(self):
        """Obtém e define a imagem dos olhos exibida na tela."""
        return self._eyes

    @eyes.setter
    def eyes(self, value):
        # Só redesenha a tela se a imagem realmente mudou, evitando
        # recarregar a mesma imagem repetidamente.
        if value != self._eyes:
            self._eyes = value
            self.ev3.screen.load_image(value)

    def update_eyes(self):
        """Anima os olhos ao longo do tempo (piscadas aleatórias), dando a
        impressão de que o cachorrinho está vivo mesmo quando parado."""
        # Timer 1: alterna entre "olhos fechados" (piscada rápida) e o
        # estado anterior, em intervalos aleatórios.
        if self.eyes_timer_1.time() > self.eyes_timer_1_end:
            self.eyes_timer_1.reset()
            if self.eyes == self.SLEEPING_EYES:
                self.eyes_timer_1_end = urandom.randint(1, 5) * 1000
                self.eyes = self.TIRED_RIGHT_EYES
            else:
                self.eyes_timer_1_end = 250
                self.eyes = self.SLEEPING_EYES

        # Timer 2: alterna entre olhar para a esquerda e para a direita,
        # em intervalos aleatórios (só quando não está com os olhos fechados).
        if self.eyes_timer_2.time() > self.eyes_timer_2_end:
            self.eyes_timer_2.reset()
            if self.eyes != self.SLEEPING_EYES:
                self.eyes_timer_2_end = urandom.randint(1, 10) * 1000
                if self.eyes != self.TIRED_LEFT_EYES:
                    self.eyes = self.TIRED_LEFT_EYES
                else:
                    self.eyes = self.TIRED_RIGHT_EYES

    def update_pet_count(self):
        """Atualiza o atributo :attr:`pet_count` caso o cachorrinho esteja
        sendo acariciado no momento (sensor de toque pressionado).

        Retorna:
            bool:
                ``True`` se o cachorrinho foi acariciado desde a última vez
                que este método foi chamado, ``False`` caso contrário.
        """
        changed = False

        petted = self.touch_sensor.pressed()
        # Só conta quando o sensor passa de "solto" para "pressionado"
        # (evita contar várias vezes enquanto o botão continua pressionado).
        if petted and petted != self.prev_petted:
            self.pet_count += 1
            print("pet_count:", self.pet_count, "pet_target:", self.pet_target)
            self.count_changed_timer.reset()
            # Ao ser tocada (carinho), a cachorrinha sempre balança a cabeça.
            self.shake_head()

            # self.pet_count começa em 1 (definido em reset()), então o
            # número de carinhos recebidos desde então é pet_count - 1.
            touches = self.pet_count - 1
            if touches == 1:
                # 1º carinho: senta, dorme e ronca.
                self.behavior = self.go_to_sleep
            elif touches == 2:
                # 2º carinho: senta e late apaixonada.
                self.sit_down()
                self.eyes = self.HEART_EYES
                self.ev3.speaker.play_file(SoundFile.DOG_BARK_1)
            elif touches == 3:
                # 3º carinho: rosna e fica brava.
                self.behavior = self.act_angry
            elif not self.behavior == self.act_hungry:
                self.eyes = self.SQUINTY_EYES
                self.ev3.speaker.play_file(SoundFile.DOG_SNIFF)
            changed = True

        self.prev_petted = petted
        return changed

    def update_feed_count(self):
        """Atualiza o atributo :attr:`feed_count` caso o cachorrinho esteja
        sendo alimentado no momento (sensor de cor detecta uma cor).

        Retorna:
            bool:
                ``True`` se o cachorrinho foi alimentado desde a última vez
                que este método foi chamado, ``False`` caso contrário.
        """
        color = self.color_sensor.color()
        changed = False

        # Nenhuma cor detectada, ou a mesma cor de antes: não faz nada
        # (evita repetir a mesma reação continuamente).
        if color is None or color == self.prev_color:
            return changed

        self.prev_color = color
        self.count_changed_timer.reset()

        if color == Color.BLACK:
            # Preto (ausência de comida): fica de pé, late e mostra a
            # língua de fora — mas não conta como alimentação.
            self.stand_up()
            self.eyes = self.NEUTRAL_EYES
            self.ev3.speaker.play_file(SoundFile.DOG_BARK_1)
        else:
            self.feed_count += 1
            print("feed_count:", self.feed_count, "feed_target:", self.feed_target)
            changed = True
            if color == Color.RED:
                # Vermelho: ação de comer.
                self.eat()
            elif color == Color.GREEN:
                # Verde: pedindo comida — senta e faz carinha triste.
                self.eyes = self.HURT_EYES
                self.sit_down()
            elif color == Color.BLUE:
                # Azul: feliz, língua de fora (ofegando) e latindo (brincalhão).
                self.eyes = self.NEUTRAL_EYES
                self.ev3.speaker.play_file(SoundFile.DOG_BARK_2)
            elif color == Color.YELLOW:
                # Amarelo: em vez de comer, faz xixi (levanta a perna
                # esquerda, balança e toca o som de xixi).
                self.go_to_bathroom()
            else:
                # Qualquer outra cor (branco, marrom, etc.): reação padrão
                # de comer e sentar.
                self.eyes = self.SQUINTY_EYES
                self.ev3.speaker.play_file(SoundFile.CRUNCHING)
                self.sit_down()

        return changed

    def monitor_counts(self):
        """Monitora as contagens de carícia e alimentação, diminuindo-as
        aos poucos com o passar do tempo (o cachorrinho "esquece" carinho
        e comida antigos se nada de novo acontecer)."""
        if self.pet_count_timer.time() > 15000:
            self.pet_count_timer.reset()
            self.pet_count = max(0, self.pet_count - 1)
            print("pet_count:", self.pet_count, "pet_target:", self.pet_target)
        if self.feed_count_timer.time() > 15000:
            self.feed_count_timer.reset()
            self.feed_count = max(0, self.feed_count - 1)
            print("feed_count:", self.feed_count, "feed_target:", self.feed_target)
        if self.count_changed_timer.time() > 15000:
            # Se nada aconteceu por 15 segundos, senta e vai dormir.
            self.count_changed_timer.reset()
            self.behavior = self.go_to_sleep

    def run(self):
        """Este é o laço principal (loop) do programa."""
        self.play_startup_song()
        self.sit_down()
        self.adjust_head()
        # Ao inicializar, mantém a cabeça no ângulo -1.
        self.move_head(-1)
        self.eyes = self.SLEEPING_EYES
        self.reset()
        while True:
            self.monitor_counts()
            # Executa o método de comportamento atualmente ativo
            # (self.behavior aponta para idle, act_happy, act_angry etc.).
            self.behavior()
            wait(100)


# Isto cobre a lágrima (tear) para criar uma nova imagem de "olhos apertados"
# (SQUINTY_EYES), desenhando um retângulo branco por cima dela.
Puppy.SQUINTY_EYES.draw_box(120, 60, 140, 85, fill=True, color=Color.WHITE)


if __name__ == "__main__":
    puppy = Puppy()
    puppy.run()
