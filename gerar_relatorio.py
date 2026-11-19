#!/usr/bin/env python3
"""Gera relatorio.html (sem dependencias externas) a partir das rodadas em Média_Tempo.

Uso:  python3 gerar_relatorio.py [pasta_Média_Tempo] [rodada_a_ignorar ...]
Le <rodada>/tempos_brutos.csv de cada subpasta e grava <pasta>/relatorio.html
"""
import csv
import datetime
import html
import os
import re
import statistics
import sys
from collections import defaultdict

PADRAO = "/home/felps/Documentos/Faculdade/6° Período/Sistemas Operacionais/Trabalho/Média_Tempo"
ROTULO_CENARIO = {
    "grande": "Cenário 1: grande (.zip de 1 GB)",
    "pequeno": "Cenário 2: pequeno (.txt de ~1 KB)",
}
ORDEM_CENARIO = ["grande", "pequeno"]

# Pares de comparação cruzada PA vs PB (pasta_pa, pasta_pb, rotulo_pa, rotulo_pb)
PARES = [
    ("fat32_cluster_max", "ntfs_cluster_min", "FAT32 cluster max", "NTFS cluster min"),
    ("fat32_cluster_min", "ext2_cluster_min", "FAT32 cluster min", "ext2 cluster min"),
    ("ext4_cluster_min", "ntfs_cluster_min", "ext4 cluster min", "NTFS cluster min"),
    ("xfs_cluster_min", "ext4_cluster_min", "XFS cluster min", "ext4 cluster min"),
]

# Nomes legíveis para cada rodada
NOMES = {
    "fat32_cluster_max": "FAT32 cluster max",
    "fat32_cluster_min": "FAT32 cluster min",
    "ntfs_cluster_min": "NTFS cluster min",
    "ext2_cluster_min": "ext2 cluster min",
    "ext4_cluster_min": "ext4 cluster min",
    "xfs_cluster_min": "XFS cluster min",
}


def pt(valor, casas=2):
    """Formata número no padrão brasileiro: 1.234,56."""
    s = f"{valor:,.{casas}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def fmt(valor_ms, cenario):
    if cenario == "grande":
        return pt(valor_ms / 1000, 2) + " s"
    return pt(valor_ms, 2) + " ms"


def esc(texto):
    return html.escape(str(texto))


def chave_natural(texto):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", texto)]


def ler_rodada(caminho):
    """dados[cenario][arquivo][repeticao] = tempo em microssegundos."""
    dados = defaultdict(lambda: defaultdict(dict))
    participante = "?"
    with open(caminho, newline="", encoding="utf-8") as fh:
        for linha in csv.DictReader(fh, delimiter=";"):
            participante = linha["participante"]
            dados[linha["cenario"]][linha["arquivo"]][int(linha["repeticao"])] = int(linha["tempo_us"])
    return participante, dados


def media_ms(reps):
    return statistics.mean(reps.values()) / 1000


def media_cenario_ms(dados, cenario):
    """Média geral de um cenário (média das médias por arquivo)."""
    if cenario not in dados:
        return None
    medias = [media_ms(r) for r in dados[cenario].values()]
    return statistics.mean(medias) if medias else None


def estatisticas(medias):
    valores = list(medias.values())
    return {
        "n": len(valores),
        "media": statistics.mean(valores),
        "mediana": statistics.median(valores),
        "minimo": min(valores),
        "maximo": max(valores),
    }


def tabela(cabecalhos, linhas, classes=""):
    cls = f' class="{classes}"' if classes else ""
    cab = "".join(f"<th>{esc(c)}</th>" for c in cabecalhos)
    corpo = ""
    for l in linhas:
        celulas = []
        for c in l:
            if isinstance(c, tuple):
                celulas.append(f'<td class="{c[1]}">{c[0]}</td>')
            else:
                celulas.append(f"<td>{c}</td>")
        corpo += "<tr>" + "".join(celulas) + "</tr>"
    return f'<div class="wrap"><table{cls}><thead><tr>{cab}</tr></thead><tbody>{corpo}</tbody></table></div>'


def barras(itens, cenario, cor=None):
    """itens: lista de (rotulo, valor_ms)."""
    if not itens:
        return ""
    maximo = max(v for _, v in itens) or 1
    partes = []
    for rotulo, valor in itens:
        pct = 100 * valor / maximo
        estilo_cor = f"background:{cor}" if cor else ""
        partes.append(
            f'<div class="barra"><span>{esc(rotulo)}</span>'
            f'<div class="trilha"><div class="preench" style="width:{pct:.1f}%;{estilo_cor}"></div></div>'
            f'<span class="val">{fmt(valor, cenario)}</span></div>'
        )
    return "".join(partes)


def pct_diff(a, b):
    """Retorna (porcentagem, mais_rapido_eh_a). Porcentagem = quanto mais rápido."""
    if a <= 0 or b <= 0:
        return 0, True
    if a <= b:
        return ((b - a) / b) * 100, True
    return ((a - b) / a) * 100, False


def secao_resumo(rodadas):
    linhas, graficos = [], {c: [] for c in ORDEM_CENARIO}
    for nome, part, dados in rodadas:
        for cen in ORDEM_CENARIO:
            if cen not in dados:
                continue
            medias = {a: media_ms(r) for a, r in dados[cen].items()}
            est = estatisticas(medias)
            medicoes = sum(len(r) for r in dados[cen].values())
            linhas.append([
                esc(nome), esc(part), esc(ROTULO_CENARIO[cen].split(":")[0]),
                str(est["n"]), str(medicoes),
                fmt(est["media"], cen), fmt(est["mediana"], cen),
                fmt(est["minimo"], cen), fmt(est["maximo"], cen),
            ])
            graficos[cen].append((NOMES.get(nome, nome), est["media"]))

    out = ["<h2>Resumo comparativo</h2>",
           tabela(["Rodada", "Part.", "Cenário", "Arquivos", "Medições",
                   "Média/arquivo", "Mediana", "Mín.", "Máx."], linhas)]
    for cen in ORDEM_CENARIO:
        if graficos[cen]:
            out.append(f"<h3>Média por arquivo: {esc(ROTULO_CENARIO[cen])}</h3>")
            out.append(barras(graficos[cen], cen))
    return "".join(out)


def secao_grande(rodadas):
    nomes_rodadas = [n for n, _, d in rodadas if "grande" in d]
    if not nomes_rodadas:
        return ""
    arquivos = sorted({a for _, _, d in rodadas for a in d.get("grande", {})}, key=chave_natural)
    cab = ["Arquivo"] + [esc(NOMES.get(n, n)) for n in nomes_rodadas]
    linhas = []
    for arq in arquivos:
        celulas = [esc(arq)]
        for nome, _, d in rodadas:
            if nome not in nomes_rodadas:
                continue
            reps = d.get("grande", {}).get(arq)
            celulas.append(fmt(media_ms(reps), "grande") if reps else "-")
        linhas.append(celulas)

    out = ["<h2>Cenário 1: arquivos grandes (.zip de 1 GB)</h2>",
           "<p class='nota'>Média de 10 repetições por arquivo, em segundos.</p>",
           tabela(cab, linhas)]

    for nome, _, d in rodadas:
        if "grande" not in d:
            continue
        cab_rep = ["Arquivo"] + [f"R{i}" for i in range(1, 11)] + ["Média"]
        linhas_rep = []
        for arq in sorted(d["grande"], key=chave_natural):
            reps = d["grande"][arq]
            linhas_rep.append([esc(arq)] +
                              [fmt(reps[i] / 1000, "grande") if i in reps else "-" for i in range(1, 11)] +
                              [fmt(media_ms(reps), "grande")])
        out.append(f"<details><summary>Repetições: {esc(NOMES.get(nome, nome))}</summary>"
                   f"{tabela(cab_rep, linhas_rep)}</details>")
    return "".join(out)


def secao_pequeno(rodadas):
    nomes = [n for n, _, d in rodadas if "pequeno" in d]
    if not nomes:
        return ""
    out = ["<h2>Cenário 2: arquivos pequenos (.txt de ~1 KB)</h2>",
           "<p class='nota'>Média de 10 repetições por arquivo, em milissegundos.</p>"]

    for nome, _, d in rodadas:
        if "pequeno" not in d:
            continue
        medias = {a: media_ms(r) for a, r in d["pequeno"].items()}
        ordenados = sorted(medias.items(), key=lambda x: x[1], reverse=True)
        top = min(10, len(ordenados))
        linhas = []
        for i in range(top):
            lento, rapido = ordenados[i], ordenados[-1 - i]
            linhas.append([str(i + 1), esc(lento[0]), fmt(lento[1], "pequeno"),
                           esc(rapido[0]), fmt(rapido[1], "pequeno")])
        out.append(f"<h3>{esc(NOMES.get(nome, nome))}: 10 mais lentos e 10 mais rápidos</h3>")
        out.append(tabela(["#", "Mais lento", "Tempo", "Mais rápido", "Tempo"], linhas))

    arquivos = sorted({a for _, _, d in rodadas for a in d.get("pequeno", {})}, key=chave_natural)
    cab = ["Arquivo"] + [esc(NOMES.get(n, n)) for n in nomes]
    linhas = []
    for arq in arquivos:
        celulas = [esc(arq)]
        for nome, _, d in rodadas:
            if nome not in nomes:
                continue
            reps = d.get("pequeno", {}).get(arq)
            celulas.append(fmt(media_ms(reps), "pequeno") if reps else "-")
        linhas.append(celulas)
    out.append(f"<details><summary>Todos os {len(arquivos)} arquivos pequenos (média por rodada)</summary>"
               f"{tabela(cab, linhas)}</details>")
    return "".join(out)


def secao_comparacao_cruzada(rodadas_dict):
    """Seção de comparação cruzada PA vs PB conforme PARES definidos."""
    out = [
        "<h2>Comparação cruzada: PA vs PB</h2>",
        "<p class='nota'>Cada par compara dois sistemas de arquivos testados em partições "
        "distintas (PA e PB). A porcentagem indica quanto mais rápido é o vencedor em relação "
        "ao perdedor. Tempo = média por arquivo.</p>",
    ]

    # Tabela resumo dos duelos
    linhas = []
    for pa_key, pb_key, pa_nome, pb_nome in PARES:
        if pa_key not in rodadas_dict or pb_key not in rodadas_dict:
            continue
        _, pa_dados = rodadas_dict[pa_key]
        _, pb_dados = rodadas_dict[pb_key]

        for cen in ORDEM_CENARIO:
            pa_ms = media_cenario_ms(pa_dados, cen)
            pb_ms = media_cenario_ms(pb_dados, cen)
            if pa_ms is None or pb_ms is None:
                continue

            diff, pa_vence = pct_diff(pa_ms, pb_ms)
            vencedor = pa_nome if pa_vence else pb_nome
            cls_v = "vence"

            linhas.append([
                f"PA: {esc(pa_nome)}<br>PB: {esc(pb_nome)}",
                esc(ROTULO_CENARIO[cen].split(":")[0]),
                fmt(pa_ms, cen),
                fmt(pb_ms, cen),
                (f'<span class="destaque-{"pa" if pa_vence else "pb"}">{pt(diff, 1)}%</span>', ""),
                (f'<span class="vencedor">{esc(vencedor)}</span>', cls_v),
            ])

    out.append(tabela(
        ["Duelo", "Cenário", "PA (tempo)", "PB (tempo)", "Vantagem", "Vencedor"],
        linhas, "duelos"
    ))

    # Detalhamento por par
    for pa_key, pb_key, pa_nome, pb_nome in PARES:
        if pa_key not in rodadas_dict or pb_key not in rodadas_dict:
            continue
        _, pa_dados = rodadas_dict[pa_key]
        _, pb_dados = rodadas_dict[pb_key]

        out.append(f"<h3>{esc(pa_nome)} vs {esc(pb_nome)}</h3>")
        out.append('<div class="duelo-grid">')

        for cen in ORDEM_CENARIO:
            pa_ms = media_cenario_ms(pa_dados, cen)
            pb_ms = media_cenario_ms(pb_dados, cen)
            if pa_ms is None or pb_ms is None:
                continue

            diff, pa_vence = pct_diff(pa_ms, pb_ms)
            venc = pa_nome if pa_vence else pb_nome

            # Barra comparativa
            maximo = max(pa_ms, pb_ms)
            pa_pct = 100 * pa_ms / maximo if maximo else 0
            pb_pct = 100 * pb_ms / maximo if maximo else 0

            out.append(f'<div class="duelo-card">')
            out.append(f'<h4>{esc(ROTULO_CENARIO[cen])}</h4>')
            out.append(
                f'<div class="barra"><span class="{"destaque-pa" if pa_vence else ""}">'
                f'PA: {esc(pa_nome)}</span>'
                f'<div class="trilha"><div class="preench pa-bar" style="width:{pa_pct:.1f}%"></div></div>'
                f'<span class="val">{fmt(pa_ms, cen)}</span></div>'
            )
            out.append(
                f'<div class="barra"><span class="{"destaque-pb" if not pa_vence else ""}">'
                f'PB: {esc(pb_nome)}</span>'
                f'<div class="trilha"><div class="preench pb-bar" style="width:{pb_pct:.1f}%"></div></div>'
                f'<span class="val">{fmt(pb_ms, cen)}</span></div>'
            )
            out.append(
                f'<p class="resultado">{esc(venc)} vence por '
                f'<strong>{pt(diff, 1)}%</strong></p>'
            )
            out.append('</div>')

        out.append('</div>')

    return "".join(out)


def secao_ranking_final(rodadas_dict):
    """Ranking geral de todos os sistemas de arquivos + melhor em cada cenário."""
    out = ["<h2>Ranking final</h2>"]

    rankings = {}
    for cen in ORDEM_CENARIO:
        itens = []
        for nome, (_, dados) in rodadas_dict.items():
            ms = media_cenario_ms(dados, cen)
            if ms is not None:
                itens.append((NOMES.get(nome, nome), ms, nome))
        itens.sort(key=lambda x: x[1])
        rankings[cen] = itens

    # Tabela ranking por cenário
    for cen in ORDEM_CENARIO:
        itens = rankings[cen]
        if not itens:
            continue
        melhor = itens[0][1]
        out.append(f"<h3>🏆 {esc(ROTULO_CENARIO[cen])}</h3>")
        linhas = []
        for pos, (nome, ms, _) in enumerate(itens, 1):
            if pos == 1:
                medalha = "🥇"
            elif pos == 2:
                medalha = "🥈"
            elif pos == 3:
                medalha = "🥉"
            else:
                medalha = f"{pos}º"

            if ms == melhor:
                diff_str = "referência"
            else:
                diff_pct = ((ms - melhor) / melhor) * 100
                diff_str = f"+{pt(diff_pct, 1)}% mais lento"

            linhas.append([
                medalha, esc(nome), fmt(ms, cen), diff_str
            ])

        out.append(tabela(["Pos.", "Sistema de arquivos", "Média/arquivo", "vs 1º lugar"], linhas))
        out.append(barras([(n, v) for n, v, _ in itens], cen, cor="#3b7ddd"))

    # Melhor combinado
    out.append("<h3>Resumo dos vencedores</h3>")
    resumo_linhas = []
    for cen in ORDEM_CENARIO:
        itens = rankings[cen]
        if itens:
            resumo_linhas.append([
                esc(ROTULO_CENARIO[cen].split(":")[0]),
                f'<strong>{esc(itens[0][0])}</strong>',
                fmt(itens[0][1], cen),
            ])

    # Melhor em ambos: soma de posições, desempate por índice normalizado
    if all(rankings.get(c) for c in ORDEM_CENARIO):
        pos_map = {}
        tempos_map = {}
        melhores = {}
        for cen in ORDEM_CENARIO:
            melhores[cen] = rankings[cen][0][1] if rankings[cen] else 1
            for pos, (_, ms, key) in enumerate(rankings[cen], 1):
                pos_map.setdefault(key, {})[cen] = pos
                tempos_map.setdefault(key, {})[cen] = ms

        # Score primário = soma das posições
        # Desempate = média das razões (tempo / melhor_do_cenário)
        scores = []
        for key, posicoes in pos_map.items():
            soma = sum(posicoes.values())
            razoes = [tempos_map[key][c] / melhores[c] for c in ORDEM_CENARIO if c in tempos_map[key]]
            indice = statistics.mean(razoes) if razoes else 999
            scores.append((soma, indice, key))
        scores.sort()
        melhor_key = scores[0][2]
        melhor_nome = NOMES.get(melhor_key, melhor_key)
        melhor_indice = scores[0][1]

        pos_g = pos_map[melhor_key].get("grande", "?")
        pos_p = pos_map[melhor_key].get("pequeno", "?")
        soma_pos = (pos_g if isinstance(pos_g, int) else 99) + (pp if isinstance((pp := pos_p), int) else 99)

        # Verificar empate
        empatados = [s for s in scores if s[0] == scores[0][0]]
        if len(empatados) > 1:
            nomes_emp = ", ".join(NOMES.get(s[2], s[2]) for s in empatados)
            detalhe = (f'Empate em posições ({soma_pos}) entre {nomes_emp}. '
                       f'Desempate por índice normalizado: {pt(melhor_indice, 3)}')
        else:
            detalhe = f'{pos_g}º grande + {pos_p}º pequeno = soma {soma_pos}'

        resumo_linhas.append([
            "<strong>Melhor combinado</strong>",
            f'<strong>{esc(melhor_nome)}</strong>',
            detalhe,
        ])

    out.append(tabela(["Critério", "Vencedor", "Detalhe"], resumo_linhas))

    # Tabela completa de posições (usa melhores e tempos_map do bloco acima)
    if all(rankings.get(c) for c in ORDEM_CENARIO):
        out.append("<h3>Tabela de posições</h3>")
        pos_map_full = {}
        for cen in ORDEM_CENARIO:
            for pos, (nome, _, key) in enumerate(rankings[cen], 1):
                if key not in pos_map_full:
                    pos_map_full[key] = {"nome": nome}
                pos_map_full[key][cen] = pos

        linhas_pos = []
        def sort_key(item):
            key, info = item
            soma = sum(info.get(c, 99) for c in ORDEM_CENARIO)
            razoes = []
            for cen in ORDEM_CENARIO:
                best = melhores.get(cen, 1)
                t = tempos_map.get(key, {}).get(cen)
                if t is not None:
                    razoes.append(t / best)
            indice = statistics.mean(razoes) if razoes else 999
            return (soma, indice)
        itens_sorted = sorted(pos_map_full.items(), key=sort_key)
        for key, info in itens_sorted:
            pg = info.get("grande", "-")
            pp = info.get("pequeno", "-")
            soma = (pg if isinstance(pg, int) else 99) + (pp if isinstance(pp, int) else 99)
            # Índice normalizado
            razoes = []
            for cen in ORDEM_CENARIO:
                best = melhores.get(cen, 1)
                t = tempos_map.get(key, {}).get(cen)
                if t is not None:
                    razoes.append(t / best)
            indice = statistics.mean(razoes) if razoes else 0
            linhas_pos.append([
                esc(info["nome"]),
                f"{pg}º" if isinstance(pg, int) else "-",
                f"{pp}º" if isinstance(pp, int) else "-",
                str(soma),
                pt(indice, 3),
            ])
        out.append("<p class='nota'>Índice normalizado = média das razões (tempo / melhor do cenário). "
                   "Quanto menor, melhor. Usado como desempate.</p>")
        out.append(tabela(["Sistema de arquivos", "Pos. grande", "Pos. pequeno", "Soma", "Índice norm."], linhas_pos))

    return "".join(out)


def secao_grande(rodadas):
    nomes_rodadas = [n for n, _, d in rodadas if "grande" in d]
    if not nomes_rodadas:
        return ""
    arquivos = sorted({a for _, _, d in rodadas for a in d.get("grande", {})}, key=chave_natural)
    cab = ["Arquivo"] + [esc(NOMES.get(n, n)) for n in nomes_rodadas]
    linhas = []
    for arq in arquivos:
        celulas = [esc(arq)]
        for nome, _, d in rodadas:
            if nome not in nomes_rodadas:
                continue
            reps = d.get("grande", {}).get(arq)
            celulas.append(fmt(media_ms(reps), "grande") if reps else "-")
        linhas.append(celulas)

    out = ["<h2>Cenário 1: arquivos grandes (.zip de 1 GB)</h2>",
           "<p class='nota'>Média de 10 repetições por arquivo, em segundos.</p>",
           tabela(cab, linhas)]

    for nome, _, d in rodadas:
        if "grande" not in d:
            continue
        cab_rep = ["Arquivo"] + [f"R{i}" for i in range(1, 11)] + ["Média"]
        linhas_rep = []
        for arq in sorted(d["grande"], key=chave_natural):
            reps = d["grande"][arq]
            linhas_rep.append([esc(arq)] +
                              [fmt(reps[i] / 1000, "grande") if i in reps else "-" for i in range(1, 11)] +
                              [fmt(media_ms(reps), "grande")])
        out.append(f"<details><summary>Repetições: {esc(NOMES.get(nome, nome))}</summary>"
                   f"{tabela(cab_rep, linhas_rep)}</details>")
    return "".join(out)


def secao_pequeno(rodadas):
    nomes = [n for n, _, d in rodadas if "pequeno" in d]
    if not nomes:
        return ""
    out = ["<h2>Cenário 2: arquivos pequenos (.txt de ~1 KB)</h2>",
           "<p class='nota'>Média de 10 repetições por arquivo, em milissegundos.</p>"]

    for nome, _, d in rodadas:
        if "pequeno" not in d:
            continue
        medias = {a: media_ms(r) for a, r in d["pequeno"].items()}
        ordenados = sorted(medias.items(), key=lambda x: x[1], reverse=True)
        top = min(10, len(ordenados))
        linhas = []
        for i in range(top):
            lento, rapido = ordenados[i], ordenados[-1 - i]
            linhas.append([str(i + 1), esc(lento[0]), fmt(lento[1], "pequeno"),
                           esc(rapido[0]), fmt(rapido[1], "pequeno")])
        out.append(f"<h3>{esc(NOMES.get(nome, nome))}: 10 mais lentos e 10 mais rápidos</h3>")
        out.append(tabela(["#", "Mais lento", "Tempo", "Mais rápido", "Tempo"], linhas))

    arquivos = sorted({a for _, _, d in rodadas for a in d.get("pequeno", {})}, key=chave_natural)
    cab = ["Arquivo"] + [esc(NOMES.get(n, n)) for n in nomes]
    linhas = []
    for arq in arquivos:
        celulas = [esc(arq)]
        for nome, _, d in rodadas:
            if nome not in nomes:
                continue
            reps = d.get("pequeno", {}).get(arq)
            celulas.append(fmt(media_ms(reps), "pequeno") if reps else "-")
        linhas.append(celulas)
    out.append(f"<details><summary>Todos os {len(arquivos)} arquivos pequenos (média por rodada)</summary>"
               f"{tabela(cab, linhas)}</details>")
    return "".join(out)


CSS = """
body{font-family:system-ui,sans-serif;max-width:1200px;margin:auto;padding:24px;line-height:1.45;color:#1d1d1f;background:#fff}
h1{font-size:1.6rem;margin-bottom:.2rem} h2{margin-top:2.4rem;border-bottom:2px solid #3b7ddd;padding-bottom:.4rem;color:#1a3a5c}
h3{margin-top:1.6rem;font-size:1.05rem} h4{margin:.6rem 0 .3rem;font-size:.95rem;color:#555}
table{border-collapse:collapse;width:100%;font-size:.88rem;margin:.6rem 0}
th,td{padding:.4rem .6rem;border-bottom:1px solid #e5e5e5;text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}
th{background:#f0f4f8;color:#1a3a5c;font-weight:600}
.nota{color:#555;font-size:.92rem}
.wrap{overflow-x:auto}
.barra{display:grid;grid-template-columns:200px 1fr 130px;align-items:center;gap:.6rem;margin:.35rem 0;font-size:.9rem}
.trilha{background:#eee;border-radius:4px;height:18px;overflow:hidden}
.preench{background:#3b7ddd;height:100%;border-radius:4px}
.pa-bar{background:#2563eb}
.pb-bar{background:#dc2626}
.val{text-align:right;font-variant-numeric:tabular-nums}
details{margin:.8rem 0} summary{cursor:pointer;font-weight:600;margin:.6rem 0;color:#1a3a5c}
.destaque-pa{color:#2563eb;font-weight:700}
.destaque-pb{color:#dc2626;font-weight:700}
.vencedor{font-weight:700;color:#16a34a}
.vence{text-align:center}
.duelos td:first-child{white-space:normal;min-width:200px}
.duelo-grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin:.8rem 0}
.duelo-card{background:#f8f9fb;border:1px solid #e5e5e5;border-radius:8px;padding:1rem}
.duelo-card .barra{grid-template-columns:180px 1fr 110px}
.resultado{font-size:.92rem;margin:.6rem 0 0;color:#333}
table.duelos td{vertical-align:middle}
@media (max-width:800px){.duelo-grid{grid-template-columns:1fr} .barra{grid-template-columns:1fr;gap:.2rem}}
@media (prefers-color-scheme: dark){
body{background:#1c1c1e;color:#eee} th{background:#2c2c2e;color:#a8c4e0} td,th,h2{border-color:#3a3a3c}
h2{color:#6ea8fe} summary{color:#6ea8fe} h4{color:#aaa}
.trilha{background:#3a3a3c} .nota{color:#aaa} .resultado{color:#ccc}
.duelo-card{background:#2c2c2e;border-color:#3a3a3c}
.vencedor{color:#4ade80} .destaque-pa{color:#60a5fa} .destaque-pb{color:#f87171}
}
"""


def main():
    pasta = sys.argv[1] if len(sys.argv) > 1 else PADRAO
    ignorar = set(sys.argv[2:])
    if not os.path.isdir(pasta):
        print(f"ERRO: pasta nao encontrada: {pasta}")
        sys.exit(1)

    rodadas = []
    rodadas_dict = {}
    for nome in sorted(os.listdir(pasta)):
        if nome in ignorar:
            continue
        caminho = os.path.join(pasta, nome, "tempos_brutos.csv")
        if os.path.isfile(caminho):
            participante, dados = ler_rodada(caminho)
            rodadas.append((nome, participante, dados))
            rodadas_dict[nome] = (participante, dados)

    if not rodadas:
        print(f"ERRO: nenhuma rodada com tempos_brutos.csv em {pasta}")
        sys.exit(1)

    agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    corpo = (
        "<h1>Benchmark de gravação em partições</h1>"
        f"<p class='nota'>Gerado em {agora} a partir de {len(rodadas)} rodada(s). "
        "Cada arquivo é copiado para a partição com <code>cp</code> + <code>sync</code>, "
        "10 repetições por arquivo. Tempo médio por arquivo.</p>"
        + secao_resumo(rodadas)
        + secao_grande(rodadas)
        + secao_pequeno(rodadas)
        + secao_comparacao_cruzada(rodadas_dict)
        + secao_ranking_final(rodadas_dict)
    )
    documento = (
        "<!DOCTYPE html><html lang='pt-BR'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Relatório de benchmark</title>"
        f"<style>{CSS}</style></head><body>{corpo}</body></html>"
    )
    saida = os.path.join(pasta, "relatorio.html")
    with open(saida, "w", encoding="utf-8") as fh:
        fh.write(documento)
    print(f"Relatório gerado: {saida}")


if __name__ == "__main__":
    main()
