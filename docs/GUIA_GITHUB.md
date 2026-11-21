# Guia: o que vai em cada lugar do GitHub e como operar

## 1. Mapa do repositório

| Caminho | O que é | Quem escreve | Pode editar à mão? |
|---|---|---|---|
| `data/lotofacil.csv` | Histórico oficial (1 linha por concurso) | **Você**, só via `src/append_result.py` | Não editar linhas antigas |
| `data/SOURCES.csv` | De onde cada resultado novo foi conferido | `append_result.py` | Não |
| `config/preregistration.json` | Braços primários, controles, critério de decisão | Você, **uma vez** | **Não** depois de começar (mudança = novo arquivo `preregistration_v2.json`, valendo só para concursos futuros) |
| `src/` | Código (`data_io`, `freeze_portfolio`, `score_frozen`, `append_result`, `compare_models`, `randomness_audit`, `hypotheses_test`, `diversified` + versões V6/V7/V7.1/V8) | Você / Claude | Sim, mas toda mudança passa pelos testes |
| `tests/` + `pytest.ini` | 75 testes (dados, vazamento, congelamento, ciclo prospectivo, workflows) | Você / Claude | Sim; nunca apague um teste para "passar" |
| `.github/workflows/` | `tests.yml` (testes), `freeze-portfolio.yml` (congela + pontua), `v6.yml`, `backtest.yml`, `full-backtest.yml`, `stage2.yml` | Você | Sim, com cuidado |
| `results/frozen/` | Portfólios congelados **antes** do sorteio + `MANIFEST.jsonl` | **Só a Action** | **Nunca** |
| `results/prospective/` | `LOG.jsonl` (acertos por concurso) e `SUMMARY.md` | **Só a Action** | **Nunca** |
| `results/compare/`, `results/randomness/`, `results/hypotheses/` | Resultados dos estudos retrospectivos (gerados por scripts) | Você, rodando os scripts | Pode regenerar |
| `docs/` | Documentação: `TESTE.md`, `TEMPORAL_AUDIT.md`, `AUDITORIA_2026-11-19.md`, `AUDITORIA_CICLO2.md`, este guia | Você | Sim |
| `requirements.txt` | `numpy>=2.0`, `pytest`, `PyYAML` | Você | Sim |

## 2. Como colocar estes arquivos no GitHub

**Opção A — pelo navegador (sem instalar nada)**
1. No GitHub, abra o repositório → botão **main** → digite `ciclo-1-2` → *Create branch*.
2. Descompacte `lotofacil_ciclo1_2.zip` no seu computador.
3. Nessa branch: **Add file → Upload files**, arraste o **conteúdo** da pasta descompactada (inclusive `.github`,
   `src`, `tests`, `docs`, `config`, `results`, `pytest.ini`, `requirements.txt`, `.gitignore`; arquivos com o
   mesmo nome serão substituídos). Confirme em *Commit changes*.
   - Se o navegador não enviar a pasta oculta `.github`, crie os arquivos dela com **Add file → Create new file**,
     digitando `.github/workflows/<nome>.yml` e colando o conteúdo.
4. Abra um **Pull request** da branch `ciclo-1-2` para `main`, espere a verificação **tests** ficar verde e faça *Merge*.

**Opção B — terminal (se você usa git)**
```
git checkout -b ciclo-1-2
git apply --check ciclo.patch   # se der erro, o repositório mudou depois do zip: use a Opção A
git apply ciclo.patch
python -m pip install -r requirements.txt
python -m pytest -q -m "not slow"     # deve terminar com todos os testes passando
git add -A && git commit -m "Auditoria ciclos 1 e 2"
git push -u origin ciclo-1-2          # e abra o Pull request
```

## 3. Configurações do repositório (uma vez)

1. **Settings → Actions → General → Workflow permissions → "Read and write permissions"** → Save.
   Sem isso a Action não consegue gravar o registro congelado.
2. **Settings → Branches → Add rule** para `main`: marque *Do not allow force pushes* e *Do not allow deletions*.
   A data do commit é a prova de que o portfólio foi congelado antes do sorteio; reescrever a história a destruiria.
   (Se ativar "Require a pull request", permita que `github-actions[bot]` contorne a regra, ou o commit automático falha.)
3. **Actions**: confirme que `tests`, `freeze-portfolio` e os demais aparecem; rode `tests` manualmente uma vez
   (*Run workflow*).

## 4. Rotina por concurso

**Hoje (única vez):** o CSV está em 3810 e já houve ~24 concursos depois. Para cada concurso que falta, em ordem:
```
python src/append_result.py --csv data/lotofacil.csv --contest 3811 --date 22/10/2026 \
   --numbers 01,02,03,... --source "https://loterias.caixa.gov.br/ (conferido em 20/11/2026)"
```
Use sempre a página oficial da CAIXA. Esses concursos entram como **histórico**; **não** valem como avaliação
prospectiva (não foram congelados antes do sorteio). Só faça o `push` quando o CSV terminar no **último concurso
realizado**.

**Depois, a cada concurso:**
1. *Antes do sorteio (até ~19h):* a Action `freeze-portfolio` já deve ter congelado o próximo concurso
   (aparece um commit "registro prospectivo" e o arquivo `results/frozen/concurso_N_congelado.json`).
   Se não apareceu, veja o erro na aba **Actions** — a causa mais comum é o CSV estar desatualizado (a Action recusa).
2. *Depois do sorteio:* rode `append_result.py` com o resultado oficial, faça commit e push do CSV.
   A Action pontua o registro do concurso e congela o seguinte automaticamente.
3. *Quando quiser:* leia `results/prospective/SUMMARY.md`. Abaixo de 100 concursos o resumo diz **"insuficiente"**:
   não tire conclusão de nenhuma linha da tabela.

**Nunca:** editar `results/frozen/` ou `results/prospective/`; regenerar um registro; trocar o braço "primário"
depois de ver resultados; mudar `config/preregistration.json`.

## 4b. Se algo der errado

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Action recusa: "congelamento recusado … retroativo" | CSV termina há mais de 4 dias | Acrescente os concursos que faltam e faça push |
| `append_result.py`: "lacunas" | Pulou um concurso | Acrescente na ordem, um por vez |
| Action: "Manifesto inválido / conteúdo alterado" | Alguém editou um registro congelado | Restaure o arquivo pelo histórico do git (`git checkout <commit> -- results/frozen`) |
| Action: "histórico … alterado depois do congelamento" | Linha antiga do CSV foi editada | Reverta a edição; se for correção legítima, documente e peça nova auditoria |
| Push da Action rejeitado | Regra de branch bloqueando o bot | Ajuste a regra (seção 3, item 2) |

## 5. O que ainda não foi testado

O passo da Action que faz `git push` do registro e a pontuação automática só podem ser verificados rodando-as no
GitHub. Os scripts que elas chamam têm testes locais; a primeira execução real deve ser acompanhada na aba Actions.
