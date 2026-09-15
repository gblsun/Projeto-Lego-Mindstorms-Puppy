#!/usr/bin/env pybricks-micropython

"""
Exemplo de Programa "Puppy" (cachorrinho) para LEGO® MINDSTORMS® EV3
---------------------------------------------------------------------
Versão reduzida: somente funcionalidades do "ossinho"

Este programa requer o LEGO® EV3 MicroPython v2.0.
Download: https://education.lego.com/en-us/support/mindstorms-ev3/python-for-ev3

As instruções de montagem podem ser encontradas em:
https://education.lego.com/en-us/support/mindstorms-ev3/building-instructions#building-core

Esta é uma versão reduzida do Puppy que mantém apenas a mecânica do "osso"
(Sensor de Cor, Port.S4) — a alimentação do cachorrinho. Não há sensor de
toque (carinho) nesta versão: todo o comportamento depende exclusivamente
de quantas vezes o cachorrinho foi alimentado.

Cores do "osso" e o que cada uma faz
-----------------------------------------------------------------------------
Aproximando o osso (ou qualquer objeto colorido) do Sensor de Cor, o
cachorrinho é alimentado, segundo update_feed_count():

none (nenhuma cor detectada): não alimenta o cachorrinho; nada acontece.
black (preto/ausência de comida): NÃO conta como alimentação; nada acontece.
qualquer outra cor válida, diferente da última lida: conta como uma
  alimentação — incrementa feed_count, mostra os "olhos apertados"
  (SQUINTY_EYES) e toca o som de mastigar (CRUNCHING).

Observação: só conta uma nova alimentação quando a cor muda em relação à
última leitura (self.prev_color). É preciso afastar o osso e aproximar de
novo (ou trocar de cor) para repetir a reação.

Meta de alimentação (feed_target)
-----------------------------------------------------------------------------
Ao ser reiniciado (reset()), o cachorrinho sorteia uma meta de alimentação
(feed_target, entre 2 e 4). O comportamento atual é decidido comparando
feed_count com feed_target (ver update_behavior()):

feed_count == feed_target: cachorrinho feliz — comemora (act_happy) e
  reinicia o ciclo com uma nova meta.
feed_count > feed_target: comeu demais — vai ao banheiro (go_to_bathroom) e
  a contagem de alimentação é reiniciada.
feed_count == 0: com fome — fica com fome (act_hungry) até ser alimentado.

Inatividade
-----------------------------------------------------------------------------
A contagem de alimentação diminui aos poucos com o tempo: a cada 15
segundos sem uma nova alimentação, feed_count é reduzida em 1, até no
mínimo 0 (ver monitor_counts). Não há comportamento de dormir nesta
versão — o cachorrinho fica sempre em pé, esperando ser alimentado.
"""

import urandom

from pybricks.hubs import EV3Brick
from pybricks.ev3devices import Motor, ColorSensor
from pybricks.parameters import Port, Button, Color, Direction
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

    # Estas constantes são para os "olhos" (imagens exibidas na tela do EV3).
    TIRED_LEFT_EYES = Image(
        ImageFile.TIRED_LEFT
    )  # Olhos cansados olhando para a esquerda
    TIRED_RIGHT_EYES = Image(
        ImageFile.TIRED_RIGHT
    )  # Olhos cansados olhando para a direita
    SLEEPING_EYES = Image(
        ImageFile.SLEEPING
    )  # Olhos fechados (usado na piscada, em update_eyes)
    HURT_EYES = Image(
        ImageFile.HURT
    )  # Olhos de "machucado"/triste (usado quando está com fome)
    HEART_EYES = Image(ImageFile.LOVE)  # Olhos de coração (feliz)
    SQUINTY_EYES = Image(
        ImageFile.TEAR
    )  # a lágrima é apagada depois (ver draw_box no final do arquivo)

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

        # Inicializa o Sensor de Cor. É usado para detectar as cores do osso
        # ao alimentar o cachorrinho.
        self.color_sensor = ColorSensor(Port.S4)

        # Cronômetro usado para controlar o tempo desde a última alimentação.
        self.feed_count_timer = StopWatch()

        # Estes atributos são inicializados depois, no método reset().
        self.feed_target = (
            None  # Quantidade de alimentações necessária para ficar feliz
        )
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

        # Este atributo é usado em update_feed_count(), para detectar
        # mudanças de estado (borda de subida) na cor lida.
        self.prev_color = None

    def adjust_head(self):
        """Usa os botões para cima e para baixo do bloco EV3 para ajustar a
        cabeça do cachorrinho para cima ou para baixo (calibração manual
        antes de iniciar o programa).
        """
        self.ev3.screen.load_image(ImageFile.EV3_ICON)
        self.ev3.light.on(Color.ORANGE)

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

    def reset(self):
        # Deve ser chamado quando o cachorrinho estiver sentado.
        self.left_leg_motor.reset_angle(0)
        self.right_leg_motor.reset_angle(0)
        # Escolhe um número aleatório de vezes que o cachorrinho precisa ser alimentado.
        self.feed_target = urandom.randint(2, 4)
        # A contagem de alimentação começa em 1.
        self.feed_count = 1
        # Reinicia o cronômetro.
        self.feed_count_timer.reset()
        # Define o comportamento inicial como "idle" (parado/à espera).
        self.behavior = self.idle

    # Os próximos 4 métodos definem os comportamentos do cachorrinho,
    # todos baseados apenas na contagem de alimentação (feed_count).

    def idle(self):
        """O cachorrinho está parado, esperando ser alimentado."""
        if self.did_behavior_change:
            print("idle")
            self.stand_up()
        self.update_eyes()
        self.update_behavior()
        self.update_feed_count()

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

    def go_to_bathroom(self):
        """Faz o cachorrinho "ir ao banheiro" (quando recebeu comida
        demais)."""
        if self.did_behavior_change:
            print("go_to_bathroom")
        self.eyes = self.SQUINTY_EYES
        # Levanta todas as pernas e fica de pé antes de fazer xixi.
        self.stand_up()
        wait(100)
        # Levanta a perna direita (postura de "fazer xixi").
        self.right_leg_motor.run_target(100, self.STRETCH_ANGLE)
        wait(800)
        self.ev3.speaker.play_file(SoundFile.HORN_1)
        wait(1000)
        # Balança a perna direita 3 vezes.
        for _ in range(3):
            self.right_leg_motor.run_angle(100, 20)
            self.right_leg_motor.run_angle(100, -20)
        self.right_leg_motor.run_target(100, self.STAND_UP_ANGLE)
        # Zera a contagem de alimentação, já que "gastou" a comida.
        self.feed_count = 1
        self.behavior = self.idle

    def act_happy(self):
        """Faz o cachorrinho agir feliz (quando atingiu exatamente a meta
        de alimentação)."""
        if self.did_behavior_change:
            print("act_happy")
        self.eyes = self.HEART_EYES
        self.sit_down()
        # Late e pula 3 vezes para comemorar.
        for _ in range(3):
            self.ev3.speaker.play_file(SoundFile.DOG_BARK_1)
            self.hop()
        wait(500)
        self.sit_down()
        # Reinicia o ciclo com uma nova meta aleatória de alimentação.
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

    def update_behavior(self):
        """Atualiza a property :prop:`behavior` (comportamento) com base
        apenas na contagem de alimentação (feed_count).
        """
        if self.feed_count == self.feed_target:
            # Se atingiu exatamente a meta de alimentação, fica feliz.
            self.behavior = self.act_happy
        elif self.feed_count > self.feed_target:
            # Se comeu demais, vai ao banheiro.
            self.behavior = self.go_to_bathroom
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

    def update_feed_count(self):
        """Atualiza o atributo :attr:`feed_count` caso o cachorrinho esteja
        sendo alimentado no momento (sensor de cor detecta uma cor do osso).

        Retorna:
            bool:
                ``True`` se o cachorrinho foi alimentado desde a última vez
                que este método foi chamado, ``False`` caso contrário.
        """
        color = self.color_sensor.color()
        changed = False

        # Nenhuma cor detectada, preto (ausência de comida) ou a mesma cor
        # de antes: não faz nada (evita repetir a mesma reação continuamente).
        if color is None or color == Color.BLACK or color == self.prev_color:
            return changed

        self.prev_color = color
        self.feed_count += 1
        print("feed_count:", self.feed_count, "feed_target:", self.feed_target)
        self.eyes = self.SQUINTY_EYES
        self.ev3.speaker.play_file(SoundFile.CRUNCHING)
        changed = True

        return changed

    def monitor_counts(self):
        """Monitora a contagem de alimentação, diminuindo-a aos poucos com o
        passar do tempo (o cachorrinho "esquece" comida antiga se nada de
        novo acontecer)."""
        if self.feed_count_timer.time() > 15000:
            self.feed_count_timer.reset()
            self.feed_count = max(0, self.feed_count - 1)
            print("feed_count:", self.feed_count, "feed_target:", self.feed_target)

    def run(self):
        """Este é o laço principal (loop) do programa."""
        self.sit_down()
        self.adjust_head()
        self.reset()
        while True:
            self.monitor_counts()
            # Executa o método de comportamento atualmente ativo
            # (self.behavior aponta para idle, act_happy, act_hungry etc.).
            self.behavior()
            wait(100)


# Isto cobre a lágrima (tear) para criar uma nova imagem de "olhos apertados"
# (SQUINTY_EYES), desenhando um retângulo branco por cima dela.
Puppy.SQUINTY_EYES.draw_box(120, 60, 140, 85, fill=True, color=Color.WHITE)


if __name__ == "__main__":
    puppy = Puppy()
    puppy.run()
