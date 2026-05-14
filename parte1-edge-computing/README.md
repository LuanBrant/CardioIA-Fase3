# Parte 1 — Edge Computing (ESP32 + DHT22)

Protótipo de wearable cardiológico que captura sinais vitais, processa
localmente e mantém um buffer offline resiliente que é sincronizado com a
"nuvem" (Serial) quando a conectividade WiFi simulada retorna.

## Arquivos

| Arquivo            | Propósito                                                          |
|--------------------|--------------------------------------------------------------------|
| `sketch.ino`       | Mesma fonte usada pelo Wokwi Web                                   |
| `src/main.cpp`     | Fonte para uso com PlatformIO + extensão Wokwi no VSCode           |
| `diagram.json`     | Circuito Wokwi (ESP32 + DHT22 + 2 botões + 2 LEDs)                 |
| `libraries.txt`    | Dependências para Wokwi Web                                        |
| `platformio.ini`   | Build PlatformIO local                                             |
| `wokwi.toml`       | Apontamento Wokwi → binário PIO                                    |
| `RELATORIO.md`     | Relatório técnico (atende o entregável de 1 página)                |

## Executar no Wokwi Web

1. Acesse <https://wokwi.com/projects/new/esp32>.
2. Em **Code**, cole `sketch.ino`.
3. Em **diagram.json**, cole o conteúdo de `diagram.json`.
4. Em **libraries.txt**, cole o conteúdo de `libraries.txt`.
5. ▶ **Start simulation**.
6. Interaja:
   - Botão **vermelho (PULSO)**: cada toque conta 1 batimento.
   - Botão **azul (WIFI)**: alterna conectividade ON/OFF.
   - LED **verde**: estado da rede.
   - LED **vermelho**: alerta clínico ativo (temperatura/BPM/umidade fora
     da faixa).

## Executar no VSCode + PlatformIO

```bash
pio run                       # compila
# Em seguida abra a paleta -> "Wokwi: Start Simulator"
```

## Limites clínicos usados

- Febre: `T > 38 °C`
- Taquicardia: `BPM > 120`
- Bradicardia: `BPM < 40`
- Sudorese intensa: `UMID > 85 %`

## Link Wokwi

**https://wokwi.com/projects/464008006272352257**
