# Arquivo morto (versões antigas)

Nada aqui é usado. O programa em uso é [`../puppy/mainP.py`](../puppy/mainP.py).

Estes arquivos ficam fora de [`../puppy/`](../puppy/) de propósito: a extensão
EV3 do VS Code envia a pasta do projeto inteira para o brick, e eles não
precisam ir junto.

| Arquivo | O que é |
| --- | --- |
| [`main.py`](main.py) | Versão anterior (743 linhas), com `shake_head` e outro mapeamento de cores — no preto o robô latia |
| [`main2.py`](main2.py) | Versão reduzida (415 linhas), só com a mecânica do osso, sem sensor de toque. **Não roda como está**: a linha 1 tem um cabeçalho de diff (`@ -1,415 +0,0 @@`) colado por engano |
| [`mainP copy.py`](mainP%20copy.py) | Cópia anterior do `mainP.py`. Diferença única: para acordar exigia toque **+** botão CENTRO juntos, em vez de toque **ou** cor |
| [`puppyy-template-main.py`](puppyy-template-main.py) | Esqueleto padrão do template EV3 — só emite um beep. Veio da pasta `puppy/puppy/puppyy/`, já removida |
