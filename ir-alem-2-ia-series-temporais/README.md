# Ir Além 2 — IA em séries temporais de saúde (CardioIA)

Comparação entre **regressão logística** (baseline tradicional) e
**neurônio LIF** (Leaky Integrate-and-Fire, neuromórfico) na tarefa de
classificar séries de batimentos cardíacos em **normal** vs
**arrítmico**.

## Arquivos

| Arquivo                              | Função                                      |
|--------------------------------------|---------------------------------------------|
| `cardioia_timeseries.ipynb`          | Notebook executável com toda a comparação   |
| `data_generator.py`                  | Geração sintética do dataset                |
| `models/logistic_classifier.py`      | Baseline (sklearn `LogisticRegression`)     |
| `models/lif_neuromorphic.py`         | Modelo LIF + classificador por firing rate  |
| `requirements.txt`                   | Dependências                                |
| `RELATORIO.md`                       | Relatório comparativo (≥ 2 páginas)         |

## Como rodar

```bash
cd ir-alem-2-ia-series-temporais
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
jupyter notebook cardioia_timeseries.ipynb
```

Ou em uma única linha (script):

```bash
python -c "
from data_generator import make_dataset, hand_crafted_features
from models.logistic_classifier import build_pipeline
from models.lif_neuromorphic import LIFClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

X, y = make_dataset(400)
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
lr  = build_pipeline().fit(hand_crafted_features(Xtr), ytr)
lif = LIFClassifier().fit(Xtr, ytr)
print('LogReg:'); print(classification_report(yte, lr.predict(hand_crafted_features(Xte))))
print('LIF:   '); print(classification_report(yte, lif.predict(Xte)))
"
```

## Vídeo (entregar manualmente)

Postar no YouTube como **não listado** e atualizar este link:

> `https://youtu.be/<seu-id>`

Roteiro sugerido (máx. 4 min):

1. Contextualizar o projeto CardioIA (30 s).
2. Mostrar geração dos sinais sintéticos no notebook (45 s).
3. Rodar regressão logística e comentar métricas (45 s).
4. Rodar LIF e comentar firing rate / threshold (60 s).
5. Comparar tabelas / discutir trade-offs (30 s).
6. Encerramento (30 s).
